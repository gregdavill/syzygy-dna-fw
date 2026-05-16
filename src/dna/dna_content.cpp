#include "dna_content.hpp"

namespace syzygy::dna {

// Placeholder: kPodBlobSize zero bytes in flash. tools/dna_patch.py (run by
// meson as the last build step) overwrites the leading bytes with a real DNA
// payload derived from a YAML spec — header + identity strings + CRC-16 —
// and leaves the tail zero-filled.
//
// Until patched, sub-address 0x8000+ reads return zeros, which a SYZYGY
// carrier will treat as an invalid/empty DNA (full_length = 0).
const std::uint8_t kPodBlob[kPodBlobSize] = {};

}  // namespace syzygy::dna
