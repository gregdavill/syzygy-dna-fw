#pragma once

// Pod identity for THIS firmware build.
// Edit the values below to match your peripheral.
//
// All strings are stored without NUL terminators. Lengths are bytes; each
// individual field is limited to 255 chars (uint8 length field).

#include "dna_blob.hpp"

namespace syzygy::dna {

inline constexpr DnaSpec kPodSpec = {
    .identity = {
        .manufacturer = "Example Co",
        .product      = "POD-EXAMPLE",
        .part_number  = "POD-EXAMPLE-0001",
        .revision     = "A",
        .serial       = "0000000001",
    },
    .loads = {
        .max_5v_mA  = 0,
        .max_3v3_mA = 100,
        .max_vio_mA = 50,
    },
    .attributes = {
        .is_lvds       = false,
        .is_doublewide = false,
        .is_txr4       = false,
    },
    .vio_ranges = {{
        // SmartVIO range 1: 1.8 V – 3.3 V (in 10 mV units).
        {.min_10mV = 180, .max_10mV = 330},
        {},
        {},
        {},
    }},
    .dna_major          = kDnaMajorVersion,
    .dna_minor          = kDnaMinorVersion,
    .required_dna_major = 0,
    .required_dna_minor = 0,
};

inline constexpr std::size_t kPodBlobSize = dna_blob_size(kPodSpec);

inline constexpr auto kPodBlob = build_dna_blob<kPodBlobSize>(kPodSpec);

}  // namespace syzygy::dna
