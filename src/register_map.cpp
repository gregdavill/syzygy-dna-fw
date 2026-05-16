#include "register_map.hpp"

#include "dna/dna_content.hpp"

namespace syzygy {

namespace {

constexpr std::uint16_t kFwMajor = 0;
constexpr std::uint16_t kFwMinor = 1;

constexpr std::uint16_t kDnaBase = 0x8000;
constexpr std::uint16_t kDnaRegionEnd = 0x9000;  // exclusive

constexpr std::uint16_t kEepromSize = static_cast<std::uint16_t>(dna::kPodBlobSize);

}  // namespace

std::uint8_t RegisterMap::read(std::uint16_t addr) {
    switch (addr) {
        case 0x0000: return static_cast<std::uint8_t>(kFwMajor);
        case 0x0001: return static_cast<std::uint8_t>(kFwMinor);
        case 0x0002: return dna::kDnaMajorVersion;
        case 0x0003: return dna::kDnaMinorVersion;
        case 0x0004: return static_cast<std::uint8_t>((kEepromSize >> 8) & 0xFF);  // EEPROM size hi
        case 0x0005: return static_cast<std::uint8_t>(kEepromSize & 0xFF);          // EEPROM size lo
        default: break;
    }

    if (addr >= kDnaBase && addr < kDnaRegionEnd) {
        const std::uint16_t offset = static_cast<std::uint16_t>(addr - kDnaBase);
        if (offset < dna::kPodBlobSize) {
            return dna::kPodBlob[offset];
        }
        return 0xFF;
    }

    return 0xFF;
}

bool RegisterMap::write(std::uint16_t /*addr*/, std::uint8_t /*value*/) {
    // All regions are read-only in this build.
    return false;
}

}  // namespace syzygy
