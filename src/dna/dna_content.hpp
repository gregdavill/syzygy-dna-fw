#pragma once

#include <cstddef>
#include <cstdint>

namespace syzygy::dna {

// SYZYGY DNA spec version that THIS FIRMWARE implements (served by
// register_map at sub-addresses 0x0002 / 0x0003). Distinct from the version
// bytes inside the DNA blob, which describe what spec the DNA *encoder* used.
inline constexpr std::uint8_t kDnaMajorVersion = 1;
inline constexpr std::uint8_t kDnaMinorVersion = 1;

// Reservation for the DNA payload in flash. tools/dna_patch.py overwrites
// this slot post-link from a YAML spec.
//
// Sized to 4096 B to match the full SYZYGY DNA EEPROM region the spec maps at
// sub-addresses 0x8000–0x8FFF. The actual identity is bounded tighter — the
// header is 40 B and each of the five string-length fields is a uint8, so an
// all-max-ASCII identity is 40 + 5*255 = 1315 B — but reserving the full
// 4096 B is what the EEPROM-size register at 0x0004/0x0005 should report,
// and it costs negligible flash on this part.
inline constexpr std::size_t kPodBlobSize = 4096;

extern const std::uint8_t kPodBlob[kPodBlobSize];

}  // namespace syzygy::dna
