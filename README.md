# syzygy-dna

SYZYGY DNA peripheral firmware for the **CH32V003F4U6** (RISC-V RV32EC,
16 KB flash, 2 KB SRAM).

Implements the I2C-responder side of the [SYZYGY DNA Specification
v1.1](https://syzygyfpga.io/wp-content/uploads/2020/05/Syzygy-DNA-Specification-V1p1.pdf):

- R_GA voltage on PA2 → 7-bit I²C address (`0x30 … 0x3F`)
- I2C target on PC1 (SDA) / PC2 (SCL), 16-bit sub-address framing
- Firmware register file (FW & DNA versions, EEPROM size)
- 40-byte DNA header + ASCII strings, CRC-16/CCITT-FALSE protected,
  built at compile time

## Layout

```
.
├── meson.build / meson.options    top-level build, options
├── cross/ch32v003.ini             riscv-none-elf cross-file
├── ldscripts/ch32v003.ld          linker script
├── vendor/ch32v003/               ch32fun submodule wrapper
├── src/
│   ├── main.cpp
│   ├── system_init.{hpp,cpp}      clocks, PA2/PC1/PC2 GPIO mux
│   ├── ga_adc.{hpp,cpp}           R_GA -> 7-bit address
│   ├── i2c_target.{hpp,cpp}       I2C target state machine
│   ├── register_map.{hpp,cpp}     16-bit subaddr dispatcher
│   └── dna/
│       ├── crc16.hpp              constexpr CRC-16/CCITT-FALSE
│       ├── dna_blob.hpp           constexpr DNA blob builder
│       └── dna_content.hpp        << pod identity lives here
├── tests/                         native unit tests
└── tools/flash.sh                 minichlink wrapper
```

## Build firmware

```sh
nix-shell
meson setup build-fw --cross-file cross/ch32v003.ini
meson compile -C build-fw
# Produces build-fw/src/syzygy-dna.{elf,bin,hex}
```

`-Wl,--print-memory-usage` reports flash/SRAM utilization at link time.

## Build & run host tests

```sh
nix-shell
meson setup build-tests
meson test -C build-tests
```

`test_dna_blob` reproduces the POD-CAMERA example from the spec at compile
time; the published CRC `0x72F9` is checked with `static_assert`.

## Per-unit DNA without recompiling

The firmware bakes a default DNA blob into `.rodata` (the constexpr `kPodBlob`).
To program different identities (serial numbers, etc.) into otherwise-identical
firmware, use `tools/dna_patch.py` to overwrite the blob bytes inside an ELF:

```sh
tools/dna_patch.py build-fw/src/syzygy-dna.elf my-unit.yaml -o syzygy-dna-SN0001.elf
tools/dna_patch.py --self-test          # offline check: POD-CAMERA -> 0x72F9
```

YAML format: see [tools/dna_example.yaml](tools/dna_example.yaml). The patcher
recomputes the CRC-16 and fails clearly if the new blob doesn't fit in the slot
the compiler reserved.

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
| `0x8000 – 0x8FFF` | R | DNA EEPROM blob (`kPodBlob`); beyond blob length returns `0xFF` |
| `0x9000 – 0xFFFF` | – | Reserved |

Writes are ACKed by the I2C engine but currently dropped (this is a
read-only peripheral; the spec allows it).
