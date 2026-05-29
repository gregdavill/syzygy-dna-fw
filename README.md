# syzygy-dna

SYZYGY DNA peripheral firmware for small low cost WCH RISC-V RV32EC microcontrollers.

| Target | Cross-file | Flash | SRAM |
|--------|------------|-------|------|
| **CH32V003F4U6** | `cross/ch32v003.ini` | 16 KB | 2 KB |
| **CH32V005D6U6** | `cross/ch32v005.ini` | 32 KB | 6 KB |

Implements the I2C-responder side of the [SYZYGY DNA Specification
v1.1](https://syzygyfpga.io/wp-content/uploads/2020/05/Syzygy-DNA-Specification-V1p1.pdf):

- R_GA voltage on PA2 → 7-bit I2C address (`0x30 … 0x3F`)
- I2C target on PC1 (SDA) / PC2 (SCL), 16-bit sub-address framing
- Firmware register file (FW & DNA versions, EEPROM size)
- 40-byte DNA header + ASCII strings, CRC-16/CCITT-FALSE protected,
  patched into the ELF post-link from a YAML spec

## Layout

```
.
├── meson.build / meson.options    top-level build, options
├── cross/*.ini             riscv-none-elf meson cross-file
├── ldscripts/*.ld          linker script (per target)
├── vendor/ch32v003/               ch32fun submodule wrapper (all WCH chips)
├── src/
│   ├── main.cpp
│   ├── system_init.{hpp,cpp}      clocks, PA2/PC1/PC2 GPIO mux
│   ├── ga_adc.{hpp,cpp}           R_GA -> 7-bit address
│   ├── i2c_target.{hpp,cpp}       I2C target state machine
│   ├── register_map.{hpp,cpp}     16-bit subaddr dispatcher
│   └── dna/
│       └── dna_content.cpp        Blank placeholder array (patched post-link)
└── tools/
    ├── dna_patch.py               YAML -> DNA blob -> patch into ELF
    ├── dna_example.yaml           default identity injected post-link by meson
    └── flash.sh                   minichlink wrapper
```

## Build firmware

```sh
nix-shell
meson setup build-fw --cross-file cross/ch32v003.ini   # or cross/ch32v005.ini
meson compile -C build-fw
# Produces build-fw/src/syzygy-dna.{elf,bin,hex}
```

The DNA blob is **not** baked in by the C++ compiler — `kPodBlob` is reserved
as a fixed 4096-byte zero-filled array (the full SYZYGY EEPROM region), and
meson runs `tools/dna_patch.py` post-link to overwrite it with the contents
of a YAML spec. The default YAML is
[tools/dna_example.yaml](tools/dna_example.yaml); override with:

```sh
meson setup build-fw --cross-file cross/ch32v003.ini -Ddna_yaml=path/to/your.yaml
```

You can also re-spin per-unit identities after the build without recompiling:

```sh
tools/dna_patch.py build-fw/src/syzygy-dna.elf my-unit.yaml -o syzygy-dna-SN0001.elf
```

`-Wl,--print-memory-usage` reports flash/SRAM utilization at link time.

## Run tests

Two suites, both wired into CI:

```sh
meson test -C build-fw           # offline DNA self-test (~0.1s)
pytest tests/renode/ -v          # Renode integration suite (~2 min, 25 tests)
```

The meson test runs `tools/dna_patch.py --self-test`, which reproduces the
spec's POD-CAMERA example and asserts the published CRC of `0x72F9` — this is
the only place the DNA layout has a programmatic implementation, so the
self-test pins it to the spec.

The pytest suite boots the compiled firmware inside Renode against a CH32V003
platform model (RCC / ADC1 / I2C1 / PFIC peripherals in
[tests/renode/platforms/](tests/renode/platforms/)) and exercises two
end-to-end paths:

- `test_adc_address.py` sweeps every R_GA voltage and asserts the firmware
  programs the matching 7-bit I2C address.
- `test_dna_blob.py` drives a controller-side I2C read of `kPodBlob` through
  the firmware's ISR and compares byte-for-byte against the ELF.

## Flash

```sh
./tools/flash.sh                # uses build-fw/src/syzygy-dna.bin
./tools/flash.sh path/to/x.bin  # explicit path
```

## Pin map

| MCU pin | Function | SYZYGY role |
|---------|----------|-------------|
| PA2 | ADC1 channel 0, analog in | R_GA voltage sense |
| PC1 | I2C1_SDA, AF open-drain | I2C data |
| PC2 | I2C1_SCL, AF open-drain | I2C clock |

External components on the peripheral side:

- 10 kΩ pull-up from PA2 to 3.3 V (`R_GA` divider top)
- I2C pull-ups: provided by the carrier per SYZYGY spec

## Memory map (sub-address space)

| Range | Access | Contents |
|-------|--------|----------|
| `0x0000` | R | FW major version |
| `0x0001` | R | FW minor version |
| `0x0002` | R | SYZYGY DNA major version (1) |
| `0x0003` | R | SYZYGY DNA minor version (1) |
| `0x0004 – 0x0005` | R | EEPROM size, big-endian |
| `0x0006 – 0x02FF` | – | Reserved (reads `0xFF`) |
| `0x0300 – 0x7FFF` | – | Firmware-specific, unused (reads `0xFF`) |
| `0x8000 – 0x8FFF` | R | DNA EEPROM blob (`kPodBlob`, 4 KB); identity bytes first, zero-padded past `full_length` |
| `0x9000 – 0xFFFF` | – | Reserved |

Writes are ACKed by the I2C engine but currently dropped (this is a
read-only peripheral; the spec allows it).
