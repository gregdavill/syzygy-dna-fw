#include "system_init.hpp"

#include <cstdint>

extern "C" {
#include "ch32fun.h"
}

namespace syzygy {
namespace {

// Write the 4-bit CFGLR config nibble for `pin` (0..7 within the low-half
// register) without disturbing the other pins on the port.
inline void set_cfglr_nibble(volatile std::uint32_t& cfglr, unsigned pin, unsigned cfg4) {
    const unsigned shift = pin * 4;
    cfglr = (cfglr & ~(0xFu << shift)) | ((cfg4 & 0xFu) << shift);
}

// CNF=11 (AF open-drain), MODE=01 (10 MHz output) -> 0b1101.
constexpr unsigned kAfOdSlow = 0b1101u;
// CNF=00 (analog), MODE=00 (input) -> 0b0000.
constexpr unsigned kAnalogIn = 0b0000u;

}  // namespace

void system_init() {
    SystemInit();

    // Peripheral clocks. CH32V003: RCC_APB2PCENR for GPIO/AFIO/ADC, RCC_APB1PCENR for I2C1.
    RCC->APB2PCENR |= RCC_APB2Periph_GPIOA
                    | RCC_APB2Periph_GPIOC
                    | RCC_APB2Periph_AFIO
                    | RCC_APB2Periph_ADC1;
    RCC->APB1PCENR |= RCC_APB1Periph_I2C1;

    set_cfglr_nibble(GPIOA->CFGLR, 2, kAnalogIn);   // PA2 -> ADC1_IN0
    set_cfglr_nibble(GPIOC->CFGLR, 1, kAfOdSlow);   // PC1 -> I2C1_SDA
    set_cfglr_nibble(GPIOC->CFGLR, 2, kAfOdSlow);   // PC2 -> I2C1_SCL
}

}  // namespace syzygy
