#include "ga_adc.hpp"
#include "i2c_target.hpp"
#include "system_init.hpp"

extern "C" {
#include "ch32fun.h"
}

#ifndef SYZYGY_I2C_SPEED_HZ
#define SYZYGY_I2C_SPEED_HZ 100000
#endif

// Retry interval while waiting for a usable R_GA reading from the carrier.
// Short enough that startup feels instant when the carrier is already up,
// long enough that we're not slamming the ADC during a slow power ramp.
static constexpr unsigned kGaRetryDelayMs = 10;

int main() {
    syzygy::system_init();

    // Resolve our I2C address from R_GA. The spec recommends sampling shortly
    // after startup; we do it before bringing up I2C so we have an address to
    // configure with. If the carrier reading lands in a dead-band we loop
    // forever waiting for a future power-cycle — there is nothing useful we
    // can announce without a valid address.
    std::uint8_t address = 0;
    while (true) {
        auto ga = syzygy::resolve_geographical_address();
        if (ga.has_value()) {
            address = *ga;
            break;
        }
        Delay_Ms(kGaRetryDelayMs);
    }

    syzygy::i2c_target_start(address, SYZYGY_I2C_SPEED_HZ);

    // The target runs entirely from interrupts. Park in WFI to save power.
    while (true) {
        __WFI();
    }
}
