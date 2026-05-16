#pragma once

#include <cstddef>
#include <cstdint>

namespace syzygy::dna {

// SYZYGY DNA spec version that THIS FIRMWARE implements (served by
// register_map at sub-addresses 0x0002 / 0x0003). Distinct from the version
// bytes inside the DNA blob, which describe what spec the DNA *encoder* used.
inline constexpr std::uint8_t kDnaMajorVersion = 1;
inline constexpr std::uint8_t kDnaMinorVersion = 1;

// Maximum DNA payload reserved in flash. The actual blob (header + strings) is
// patched into this slot post-link by tools/dna_patch.py, driven by a YAML
// spec. We never build the blob in C++ — the firmware just serves these bytes.
//
// 256 bytes leaves room for 40 B header + 216 B of identity strings, which is
// more than any realistic pod will use.
inline constexpr std::size_t kPodBlobSize = 256;

extern const std::uint8_t kPodBlob[kPodBlobSize];

}  // namespace syzygy::dna
