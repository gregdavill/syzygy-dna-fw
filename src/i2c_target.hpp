#pragma once

#include <cstdint>

namespace syzygy {

// Configure I2C1 as a target on PC1 (SDA) / PC2 (SCL) responding to the given
// 7-bit address, with the SYZYGY DNA framing layered on top:
//
//   write transaction: <addr|W> <subaddr_hi> <subaddr_lo> [data...]    (up to 32)
//   read transaction:  <addr|W> <subaddr_hi> <subaddr_lo> Sr <addr|R> [data...]
//
// Reads stream straight from RegisterMap::read(); writes route to ::write().
// Internal pointer auto-increments and rolls over at 0xFFFF.
//
// Enables the I2C1_EV / I2C1_ER NVIC entries. Returns immediately; all
// servicing happens in the event/error ISRs.
//
// Naming: "target" follows NXP UM10204 rev 7+ I2C bus specification, which
// replaces the legacy controller/target = master/slave terminology.
void i2c_target_start(std::uint8_t address_7bit, std::uint32_t bus_speed_hz);

}  // namespace syzygy
