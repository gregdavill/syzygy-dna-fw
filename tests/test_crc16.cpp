// Standalone test: CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, MSB-first).
//
// Reference values from the SYZYGY DNA Specification v1.1 §3.2.3 and the
// well-known CRC-16/CCITT-FALSE test vectors.

#include "crc16.hpp"

#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>

using syzygy::dna::crc16_ccitt;

int main() {
    // Classic test vector: "123456789" -> 0x29B1
    {
        const char* s = "123456789";
        const auto crc = crc16_ccitt(reinterpret_cast<const std::uint8_t*>(s), 9);
        if (crc != 0x29B1) {
            std::fprintf(stderr, "CRC \"123456789\" got 0x%04X, expected 0x29B1\n", crc);
            return 1;
        }
    }

    // Empty input -> init value 0xFFFF
    {
        const auto crc = crc16_ccitt(nullptr, 0);
        if (crc != 0xFFFF) {
            std::fprintf(stderr, "CRC of empty got 0x%04X, expected 0xFFFF\n", crc);
            return 1;
        }
    }

    // Self-check property: feeding the data followed by its big-endian CRC
    // should yield 0 (residue). The spec relies on this so the carrier can
    // verify the header by running CRC over all 40 bytes.
    {
        const std::uint8_t data[] = {'1', '2', '3', '4', '5', '6', '7', '8', '9'};
        const auto crc = crc16_ccitt(data, sizeof data);
        std::uint8_t with_crc[sizeof data + 2];
        std::memcpy(with_crc, data, sizeof data);
        with_crc[sizeof data + 0] = static_cast<std::uint8_t>(crc >> 8);
        with_crc[sizeof data + 1] = static_cast<std::uint8_t>(crc & 0xFF);
        const auto residue = crc16_ccitt(with_crc, sizeof with_crc);
        if (residue != 0) {
            std::fprintf(stderr, "CRC residue got 0x%04X, expected 0x0000\n", residue);
            return 1;
        }
    }

    return 0;
}
