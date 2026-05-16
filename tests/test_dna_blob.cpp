// Golden test: reproduce the POD-CAMERA example from SYZYGY DNA Specification
// v1.1, Table 5 (§3.3), and assert the published CRC of 0x72F9.

#include "dna_blob.hpp"

#include <cstdint>
#include <cstdio>

using namespace syzygy::dna;

namespace {

constexpr DnaSpec pod_camera = {
    .identity = {
        .manufacturer = "Opal Kelly Incorporated",  // 23
        .product      = "POD-CAMERA",               // 10
        .part_number  = "POD-CAMERA-AR0330",        // 17
        .revision     = "A",                        //  1
        .serial       = "1743000ABC",               // 10
    },
    .loads = {
        .max_5v_mA  = 0,
        .max_3v3_mA = 510,
        .max_vio_mA = 50,
    },
    .attributes = {
        .is_lvds       = true,    // attribute bits = 0x0001
        .is_doublewide = false,
        .is_txr4       = false,
    },
    .vio_ranges = {{
        {.min_10mV = 180, .max_10mV = 330},
        {}, {}, {},
    }},
    .dna_major          = 1,
    .dna_minor          = 0,   // spec example predates v1.1
    .required_dna_major = 0,
    .required_dna_minor = 0,
};

constexpr std::size_t kSize = dna_blob_size(pod_camera);
constexpr auto kBlob = build_dna_blob<kSize>(pod_camera);

// Compile-time assertion: the spec says total length is 101 bytes.
static_assert(kSize == 101, "POD-CAMERA blob must be 101 bytes (40 header + 61 strings)");

// Compile-time assertion: header CRC must match the spec's published value.
static_assert(kBlob[38] == 0x72, "POD-CAMERA CRC high byte must be 0x72");
static_assert(kBlob[39] == 0xF9, "POD-CAMERA CRC low byte must be 0xF9");

// Spot-check header fields per Table 5.
static_assert(kBlob[ 0] == 101, "full length lo");
static_assert(kBlob[ 1] ==   0, "full length hi");
static_assert(kBlob[ 2] ==  40, "header length lo");
static_assert(kBlob[ 4] ==   1, "dna major");
static_assert(kBlob[ 5] ==   0, "dna minor");
static_assert(kBlob[14] == 0x01 && kBlob[15] == 0x00, "attribute flags = 0x0001 (LE)");
static_assert(kBlob[32] == 23, "manufacturer name length");
static_assert(kBlob[36] == 10, "serial number length");

}  // namespace

int main() {
    // Runtime sanity check that the constexpr value really did materialize.
    if (kBlob[38] != 0x72 || kBlob[39] != 0xF9) {
        std::fprintf(stderr, "POD-CAMERA CRC mismatch: got %02X%02X\n", kBlob[38], kBlob[39]);
        return 1;
    }

    // Whole-header residue must be 0 (spec §3.2.3).
    std::uint16_t crc = 0xFFFF;
    for (std::size_t i = 0; i < 40; ++i) {
        std::uint16_t x = static_cast<std::uint16_t>(crc >> 8) ^ kBlob[i];
        x ^= static_cast<std::uint16_t>(x >> 4);
        crc = static_cast<std::uint16_t>((crc << 8) ^ (x << 12) ^ (x << 5) ^ x);
    }
    if (crc != 0) {
        std::fprintf(stderr, "Header CRC residue = 0x%04X (expected 0)\n", crc);
        return 1;
    }

    return 0;
}
