#include "system_init.hpp"

extern "C" {
#include "ch32fun.h"
}

namespace syzygy {

void system_init() {
    SystemInit();

    // Peripheral clocks. CH32V003: RCC_APB2PCENR for GPIO/AFIO/ADC, RCC_APB1PCENR for I2C1.
    RCC->APB2PCENR |= RCC_APB2Periph_GPIOA
                    | RCC_APB2Periph_GPIOC
                    | RCC_APB2Periph_AFIO
                    | RCC_APB2Periph_ADC1;
    RCC->APB1PCENR |= RCC_APB1Periph_I2C1;

    // ------- PA2 as analog input ----------------------------------------
    // CFGLR for PA2: CNF=00 (analog), MODE=00 (input). Bits [11:8] = 0b0000.
    GPIOA->CFGLR = (GPIOA->CFGLR & ~(0xFu << (2 * 4))) | (0x0u << (2 * 4));

    // ------- PC1 / PC2 as AF open-drain, 10 MHz -------------------------
    // CNF=11 (AF open-drain), MODE=01 (10 MHz output) -> 0b1101 = 0xD per pin.
    constexpr unsigned kAfOdSlow = 0b1101u;
    GPIOC->CFGLR = (GPIOC->CFGLR & ~(0xFu << (1 * 4) | 0xFu << (2 * 4)))
                 | (kAfOdSlow << (1 * 4))
                 | (kAfOdSlow << (2 * 4));
}

}  // namespace syzygy
