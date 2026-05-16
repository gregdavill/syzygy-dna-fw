#pragma once

#include <cstdint>
#include <optional>

namespace syzygy {

// Read the R_GA voltage on PA2 (ADC1 channel 0) and resolve it to a 7-bit I2C
// address per SYZYGY DNA spec v1.1 Table 1. Returns std::nullopt if the
// reading falls outside every acceptance window (dead-band hit, no carrier).
//
// Must be called after system_init().
std::optional<std::uint8_t> resolve_geographical_address();

}  // namespace syzygy
