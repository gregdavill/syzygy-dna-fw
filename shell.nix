# Development shell for the CH32V003 SYZYGY DNA firmware.
#
# Usage:
#   nix-shell                                                 # interactive
#   nix-shell --run "meson setup build-fw --cross-file cross/ch32v003-nix.ini && meson compile -C build-fw"
#
# What this provides:
#   - meson + ninja              (build system)
#   - clang/lld                  (for native unit tests)
#   - xpack-riscv-none-elf-gcc   (RISC-V cross-toolchain, version 14.2.0-3 –
#                                 this is the version that added rv32ec/ilp32e
#                                 multilib, required for CH32V003)
{ pkgs ? import <nixpkgs> {} }:

let
  xpackVersion = "14.2.0-3";

  # Platform tuple -> { url, sha256 } pulled from the v14.2.0-3 release page.
  # Hashes are sha256 in hex (matches `*.tar.gz.sha` files on the release).
  xpackAssets = {
    "aarch64-darwin" = {
      arch    = "darwin-arm64";
      sha256  = "e76e86b8c500f8e92b3b4ff7b0444cfbf3b218515f322929e0744ec3b9ed80a8";
    };
    "x86_64-darwin" = {
      arch    = "darwin-x64";
      sha256  = "8a6e699f12876152d6386e777675d94529ccc21a57224a69d973f676949a1687";
    };
    "aarch64-linux" = {
      arch    = "linux-arm64";
      sha256  = "0c0551986e30174af55f245e1c3a86c45233fc793bf36586567f266ada6fdd98";
    };
    "x86_64-linux" = {
      arch    = "linux-x64";
      sha256  = "f574415b63f12b09bdd3475223ab492a465d23810646c90c13a4c3b676c83503";
    };
  };

  asset = xpackAssets.${pkgs.stdenv.hostPlatform.system}
    or (throw "Unsupported platform: ${pkgs.stdenv.hostPlatform.system}");

  xpack-riscv = pkgs.stdenv.mkDerivation {
    pname = "xpack-riscv-none-elf-gcc";
    version = xpackVersion;

    src = pkgs.fetchurl {
      url = "https://github.com/xpack-dev-tools/riscv-none-elf-gcc-xpack/releases/download/v${xpackVersion}/xpack-riscv-none-elf-gcc-${xpackVersion}-${asset.arch}.tar.gz";
      sha256 = asset.sha256;
    };

    # Skip the usual unpack/build phases; this is a prebuilt binary tarball.
    dontConfigure = true;
    dontBuild = true;
    dontStrip = true;       # don't strip — they're already signed/built right
    dontPatchELF = true;    # macOS: no-op. Linux: patched in fixupPhase below.

    installPhase = ''
      mkdir -p $out
      cp -r * $out/
    '';

    # On Linux, patch the dynamic linker so the binaries can find ld.so.
    # On macOS, this is a no-op.
    postFixup = pkgs.lib.optionalString pkgs.stdenv.isLinux ''
      ${pkgs.patchelf}/bin/patchelf \
        --set-interpreter $(cat ${pkgs.stdenv.cc}/nix-support/dynamic-linker) \
        $out/bin/* 2>/dev/null || true
      for f in $out/bin/* $out/libexec/gcc/*/*/c*1 $out/libexec/gcc/*/*/lto*; do
        if [ -f "$f" ] && file "$f" | grep -q ELF; then
          ${pkgs.patchelf}/bin/patchelf \
            --set-rpath ${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib pkgs.zlib ]} \
            "$f" 2>/dev/null || true
        fi
      done
    '';

    meta = {
      description = "xPack GNU RISC-V Embedded GCC toolchain (with rv32ec multilib)";
      homepage = "https://xpack-dev-tools.github.io/riscv-none-elf-gcc-xpack/";
      platforms = pkgs.lib.attrNames xpackAssets;
    };
  };

in
pkgs.mkShell {
  name = "syzygy-dna-dev";

  packages = [
    # Build system
    pkgs.meson
    pkgs.ninja
    pkgs.pkg-config

    # Native compiler for host-side unit tests
    pkgs.clang
    pkgs.lld

    # Cross toolchain
    xpack-riscv

    # Convenience
    pkgs.git
    pkgs.gnumake          # ch32fun's minichlink uses Make
    pkgs.libusb1          # minichlink talks to WCH-LinkE over USB
  ];

  shellHook = ''
    echo "─── syzygy-dna dev shell ───"
    echo "  $(riscv-none-elf-gcc --version | head -1)"
    echo "  $(meson --version | xargs -I{} echo meson {})"
    echo
    echo "Build firmware:   meson setup build-fw --cross-file cross/ch32v003.ini && meson compile -C build-fw"
    echo "Build/run tests:  meson setup build-tests && meson test -C build-tests"
  '';
}
