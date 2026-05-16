#pragma once

#include <cstdint>

namespace syzygy {

// Dispatcher across the full 16-bit sub-address space defined by the SYZYGY
// DNA spec.
//
//   0x0000-0x0005: firmware register fields (read-only versions, EEPROM size)
//   0x0006-0x02FF: reserved (reads 0xFF, writes ignored)
//   0x0300-0x7FFF: firmware-specific (unused -> 0xFF, writes ignored)
//   0x8000-0x8FFF: DNA EEPROM blob (read-only; addresses past the blob length
//                  return 0xFF, mirroring an unprogrammed EEPROM byte)
//   0x9000-0xFFFF: reserved
struct RegisterMap {
    // Read one byte at the given sub-address. Never NACKs at the I2C layer;
    // unmapped regions return 0xFF so a host can detect "no data here".
    static std::uint8_t read(std::uint16_t addr);

    // Writes are accepted (ACKed) but ignored for all read-only regions, which
    // is everything in this build. Returns true if the byte was actually
    // stored, false if dropped — useful for telemetry if you ever add a
    // mutable region.
    static bool write(std::uint16_t addr, std::uint8_t value);
};

}  // namespace syzygy
