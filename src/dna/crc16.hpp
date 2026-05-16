#pragma once

#include <cstddef>
#include <cstdint>

namespace syzygy::dna {

// CRC-16/CCITT-FALSE per SYZYGY DNA Specification v1.1 §3.2.3.
//   Polynomial: 0x1021  (x^16 + x^12 + x^5 + 1)
//   Init:       0xFFFF
//   Shift:      MSB-first
//   No reflection, no final XOR.
// constexpr so the header CRC can be computed at compile time.
constexpr std::uint16_t crc16_ccitt(const std::uint8_t* data, std::size_t length) {
    std::uint16_t crc = 0xFFFF;
    while (length--) {
        std::uint16_t x = static_cast<std::uint16_t>(crc >> 8) ^ *data++;
        x ^= static_cast<std::uint16_t>(x >> 4);
        crc = static_cast<std::uint16_t>((crc << 8) ^ (x << 12) ^ (x << 5) ^ x);
    }
    return crc;
}

}  // namespace syzygy::dna
