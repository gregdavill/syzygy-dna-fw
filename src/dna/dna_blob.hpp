#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

#include "crc16.hpp"

// SYZYGY DNA blob layout (spec v1.1, §3.2.5).
//
//   uint16 dna_full_data_length            offset 0
//   uint16 dna_header_length               offset 2
//   uint8  dna_major_version               offset 4
//   uint8  dna_minor_version               offset 5
//   uint8  required_dna_major_version      offset 6
//   uint8  required_dna_minor_version      offset 7
//   uint16 max_5v_load_mA                  offset 8
//   uint16 max_3v3_load_mA                 offset 10
//   uint16 max_vio_load_mA                 offset 12
//   uint16 attribute_flags                 offset 14
//   uint16 vio_range_n_min_10mV  (n=1..4)  offset 16, 20, 24, 28
//   uint16 vio_range_n_max_10mV            offset 18, 22, 26, 30
//   uint8  manufacturer_name_length        offset 32
//   uint8  product_name_length             offset 33
//   uint8  product_part_number_length      offset 34
//   uint8  product_revision_length         offset 35
//   uint8  serial_number_length            offset 36
//   uint8  reserved (0)                    offset 37
//   uint8  crc_hi                          offset 38  <-- CRC bytes are big-endian
//   uint8  crc_lo                          offset 39
//   <strings, no NUL terminators>          offset 40
//
// Multi-byte fields are little-endian EXCEPT the CRC, which is stored MSB
// first so that running the CRC over the full 40-byte header (including the
// CRC bytes themselves) yields 0x0000 on a valid blob.

namespace syzygy::dna {

inline constexpr std::size_t kHeaderLength = 40;
inline constexpr std::uint8_t kDnaMajorVersion = 1;
inline constexpr std::uint8_t kDnaMinorVersion = 1;

struct VioRange {
    std::uint16_t min_10mV = 0;
    std::uint16_t max_10mV = 0;
};

struct Attributes {
    bool is_lvds = false;
    bool is_doublewide = false;
    bool is_txr4 = false;

    constexpr std::uint16_t bits() const {
        return static_cast<std::uint16_t>(
            (is_lvds ? 1u << 0 : 0u) |
            (is_doublewide ? 1u << 1 : 0u) |
            (is_txr4 ? 1u << 2 : 0u));
    }
};

struct Identity {
    std::string_view manufacturer;
    std::string_view product;
    std::string_view part_number;
    std::string_view revision;
    std::string_view serial;
};

struct Loads {
    std::uint16_t max_5v_mA = 0;
    std::uint16_t max_3v3_mA = 0;
    std::uint16_t max_vio_mA = 0;
};

struct DnaSpec {
    Identity identity{};
    Loads loads{};
    Attributes attributes{};
    std::array<VioRange, 4> vio_ranges{};
    std::uint8_t dna_major = kDnaMajorVersion;
    std::uint8_t dna_minor = kDnaMinorVersion;
    std::uint8_t required_dna_major = 0;
    std::uint8_t required_dna_minor = 0;
};

// Compile-time builder.
// Returns a std::array<uint8_t, N> sized to header + all string lengths.
//   Template arg N must equal kHeaderLength + sum of identity string lengths;
//   the helper `dna_blob_size(spec)` computes it.
constexpr std::size_t dna_blob_size(const DnaSpec& s) {
    return kHeaderLength
         + s.identity.manufacturer.size()
         + s.identity.product.size()
         + s.identity.part_number.size()
         + s.identity.revision.size()
         + s.identity.serial.size();
}

namespace detail {

constexpr void put_u8(std::uint8_t* p, std::uint8_t v) { p[0] = v; }

constexpr void put_u16_le(std::uint8_t* p, std::uint16_t v) {
    p[0] = static_cast<std::uint8_t>(v & 0xFF);
    p[1] = static_cast<std::uint8_t>((v >> 8) & 0xFF);
}

constexpr void put_str(std::uint8_t* p, std::string_view s) {
    for (std::size_t i = 0; i < s.size(); ++i) {
        p[i] = static_cast<std::uint8_t>(s[i]);
    }
}

}  // namespace detail

template <std::size_t N>
constexpr std::array<std::uint8_t, N> build_dna_blob(const DnaSpec& spec) {
    std::array<std::uint8_t, N> out{};
    std::uint8_t* p = out.data();

    const std::uint16_t full_len = static_cast<std::uint16_t>(N);

    detail::put_u16_le(p +  0, full_len);
    detail::put_u16_le(p +  2, static_cast<std::uint16_t>(kHeaderLength));
    detail::put_u8   (p +  4, spec.dna_major);
    detail::put_u8   (p +  5, spec.dna_minor);
    detail::put_u8   (p +  6, spec.required_dna_major);
    detail::put_u8   (p +  7, spec.required_dna_minor);
    detail::put_u16_le(p +  8, spec.loads.max_5v_mA);
    detail::put_u16_le(p + 10, spec.loads.max_3v3_mA);
    detail::put_u16_le(p + 12, spec.loads.max_vio_mA);
    detail::put_u16_le(p + 14, spec.attributes.bits());

    for (std::size_t i = 0; i < 4; ++i) {
        const auto& r = spec.vio_ranges[i];
        detail::put_u16_le(p + 16 + i * 4 + 0, r.min_10mV);
        detail::put_u16_le(p + 16 + i * 4 + 2, r.max_10mV);
    }

    detail::put_u8(p + 32, static_cast<std::uint8_t>(spec.identity.manufacturer.size()));
    detail::put_u8(p + 33, static_cast<std::uint8_t>(spec.identity.product.size()));
    detail::put_u8(p + 34, static_cast<std::uint8_t>(spec.identity.part_number.size()));
    detail::put_u8(p + 35, static_cast<std::uint8_t>(spec.identity.revision.size()));
    detail::put_u8(p + 36, static_cast<std::uint8_t>(spec.identity.serial.size()));
    detail::put_u8(p + 37, 0);
    // CRC bytes (38, 39) are filled in below.

    // Strings (no NUL terminators).
    std::size_t off = kHeaderLength;
    detail::put_str(p + off, spec.identity.manufacturer); off += spec.identity.manufacturer.size();
    detail::put_str(p + off, spec.identity.product);      off += spec.identity.product.size();
    detail::put_str(p + off, spec.identity.part_number);  off += spec.identity.part_number.size();
    detail::put_str(p + off, spec.identity.revision);     off += spec.identity.revision.size();
    detail::put_str(p + off, spec.identity.serial);

    // Compute the CRC over the first 38 bytes (header minus the CRC field
    // itself). Stored MSB-first so that running CRC over all 40 bytes yields
    // 0x0000 — that's the residue property the spec relies on for header
    // integrity checking.
    const std::uint16_t crc = crc16_ccitt(p, kHeaderLength - 2);
    p[38] = static_cast<std::uint8_t>((crc >> 8) & 0xFF);
    p[39] = static_cast<std::uint8_t>(crc & 0xFF);

    return out;
}

}  // namespace syzygy::dna
