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
#   - renode                     (RISC-V ISA simulator + peripheral framework,
#                                 1.16.1 portable-dotnet build pulled from the
#                                 upstream release — not packaged in nixpkgs
#                                 for darwin)
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

  # ---------------------------------------------------------------------------
  # Renode 1.16.1 — pulled from the upstream GitHub release.
  #
  # nixpkgs has `pkgs.renode` but it's marked `platforms = [ "x86_64-linux" ]`
  # and pulls the Mono-based Linux tarball. We want the newer portable-dotnet
  # builds, and we want darwin-aarch64 support. So: fetch the per-platform
  # release asset and stage it ourselves, mirroring the xpack pattern above.
  #
  # x86_64-darwin is intentionally unsupported: upstream only ships an old
  # Mono build for Intel macs (renode_1.16.1.dmg), which hard-codes
  # /Library/Frameworks/Mono.framework. If you need it, install Mono manually
  # and point at the upstream DMG.
  # ---------------------------------------------------------------------------
  renodeVersion = "1.16.1";

  renodeAssets = {
    "aarch64-darwin" = {
      file   = "renode-${renodeVersion}-dotnet.osx-arm64-portable.dmg";
      sha256 = "99b8ae5897b8926ef179868d39a504fe5296555dc9c9b973718ddf3ab09175d9";
      kind   = "dmg";
    };
    "aarch64-linux" = {
      file   = "renode-${renodeVersion}.linux-arm64-portable-dotnet.tar.gz";
      sha256 = "fff3a098c96ed0a4ffbdff3f028c9c5fde432db09587c7bd7c99406180f90007";
      kind   = "tarball";
    };
    "x86_64-linux" = {
      file   = "renode-${renodeVersion}.linux-portable-dotnet.tar.gz";
      sha256 = "00e113cdbd0f5354cf2f64bbe3f5a070d8958409542fca66e45ac97d982938c0";
      kind   = "tarball";
    };
  };

  renodeAsset = renodeAssets.${pkgs.stdenv.hostPlatform.system} or (throw ''
    Renode is not provisioned for ${pkgs.stdenv.hostPlatform.system}.
    Upstream only ships a Mono-based DMG for x86_64-darwin; install Mono
    Framework 5.20+ and grab renode_${renodeVersion}.dmg from
    https://github.com/renode/renode/releases manually if you need it.
  '');

  renode = pkgs.stdenv.mkDerivation {
    pname = "renode";
    version = renodeVersion;

    src = pkgs.fetchurl {
      url    = "https://github.com/renode/renode/releases/download/v${renodeVersion}/${renodeAsset.file}";
      sha256 = renodeAsset.sha256;
    };

    # DMGs aren't auto-unpacked; tarballs are. Disable the default unpack
    # phase so we can handle both uniformly.
    dontUnpack = true;
    dontConfigure = true;
    dontBuild = true;
    dontStrip = true;
    dontPatchELF = true;

    nativeBuildInputs = pkgs.lib.optionals (renodeAsset.kind == "tarball") [
      pkgs.autoPatchelfHook
    ];

    # The portable-dotnet Linux build needs these in rpath. autoPatchelfHook
    # will set the interpreter and resolve DT_NEEDED entries from buildInputs.
    buildInputs = pkgs.lib.optionals (renodeAsset.kind == "tarball") [
      pkgs.stdenv.cc.cc.lib   # libstdc++.so.6, libgcc_s.so.1
      pkgs.zlib
      pkgs.openssl
      pkgs.icu                # System.Globalization.Native
      pkgs.libuuid
    ];

    installPhase =
      if renodeAsset.kind == "dmg" then ''
        runHook preInstall

        # Mount the DMG read-only, copy the .app's MacOS payload out, detach.
        # @loader_path-relative dylib refs stay valid as long as renode and
        # its lib*.dylibs live in the same directory.
        mnt=$(mktemp -d)
        /usr/bin/hdiutil attach -nobrowse -readonly -noautoopen \
          -mountpoint "$mnt" "$src"

        mkdir -p $out/libexec/renode $out/bin
        cp -R "$mnt/Renode.app/Contents/MacOS/." $out/libexec/renode/

        /usr/bin/hdiutil detach "$mnt" -quiet || true

        chmod +x $out/libexec/renode/renode $out/libexec/renode/renode-test
        ln -s $out/libexec/renode/renode      $out/bin/renode
        ln -s $out/libexec/renode/renode-test $out/bin/renode-test

        runHook postInstall
      '' else ''
        runHook preInstall

        tar -xzf "$src"
        mkdir -p $out/libexec $out/bin
        mv renode_*-dotnet_portable $out/libexec/renode

        ln -s $out/libexec/renode/renode      $out/bin/renode
        ln -s $out/libexec/renode/renode-test $out/bin/renode-test

        runHook postInstall
      '';

    meta = {
      description = "Renode framework for embedded systems simulation (portable-dotnet build)";
      homepage = "https://renode.io";
      platforms = pkgs.lib.attrNames renodeAssets;
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

    # Embedded systems simulator (RISC-V ISA + custom peripheral models)
    renode

    # Convenience
    pkgs.git
    pkgs.gnumake          # ch32fun's minichlink uses Make
    pkgs.libusb1          # minichlink talks to WCH-LinkE over USB

    # tools/dna_patch.py: rewrite the DNA blob inside a firmware ELF from YAML
    (pkgs.python3.withPackages (ps: with ps; [ pyelftools pyyaml ]))
  ];

  shellHook = ''
    echo "─── syzygy-dna dev shell ───"
    echo "  $(riscv-none-elf-gcc --version | head -1)"
    echo "  $(meson --version | xargs -I{} echo meson {})"
    echo "  renode $(renode --version 2>/dev/null | head -1 | awk '{print $NF}')"
    echo
    echo "Build firmware:   meson setup build-fw --cross-file cross/ch32v003.ini && meson compile -C build-fw"
    echo "Build/run tests:  meson setup build-tests && meson test -C build-tests"
  '';
}
