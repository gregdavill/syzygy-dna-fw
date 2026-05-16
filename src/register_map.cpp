#include "register_map.hpp"

#include <cstdint>

#include "dna/dna_content.hpp"

namespace syzygy {

namespace {

constexpr std::uint8_t kFwMajor = 0;
constexpr std::uint8_t kFwMinor = 1;

constexpr std::uint16_t kDnaBase      = 0x8000;
constexpr std::uint16_t kDnaRegionEnd = 0x9000;  // exclusive

constexpr std::uint16_t kEepromSize = static_cast<std::uint16_t>(dna::kPodBlobSize);

// The DNA region is mapped 1:1 onto kPodBlob; keep these in sync so the
// dispatcher below can rely on every in-range offset being valid.
static_assert(kDnaRegionEnd - kDnaBase == dna::kPodBlobSize,
              "DNA sub-address window must match kPodBlobSize");

}  // namespace

std::uint8_t RegisterMap::read(std::uint16_t addr) {
    switch (addr) {
        case 0x0000: return kFwMajor;
        case 0x0001: return kFwMinor;
        case 0x0002: return dna::kDnaMajorVersion;
        case 0x0003: return dna::kDnaMinorVersion;
        case 0x0004: return static_cast<std::uint8_t>(kEepromSize >> 8);
        case 0x0005: return static_cast<std::uint8_t>(kEepromSize & 0xFF);
        default: break;
    }

    if (addr >= kDnaBase && addr < kDnaRegionEnd) {
        return dna::kPodBlob[addr - kDnaBase];
    }

    return 0xFF;
}

bool RegisterMap::write(std::uint16_t /*addr*/, std::uint8_t /*value*/) {
    // All regions are read-only in this build.
    return false;
}

}  // namespace syzygy
