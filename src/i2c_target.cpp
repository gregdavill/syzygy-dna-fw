#include "i2c_target.hpp"

#include "register_map.hpp"

extern "C" {
#include "ch32fun.h"
}

namespace syzygy {
namespace {

// Phase of the current I2C transaction. Set on every ADDR-match event:
// write direction starts at WaitSubAddrHi, read direction goes straight
// to DataStream (the subaddr was latched by a preceding write transaction).
enum class Phase : std::uint8_t {
    Idle,
    WaitSubAddrHi,   // ADDR matched W, no bytes yet
    WaitSubAddrLo,   // got the high byte
    DataStream,      // got both subaddr bytes, streaming data
};

struct TargetState {
    Phase phase = Phase::Idle;
    std::uint16_t subaddr = 0;
};

TargetState g_state{};

// Read one byte from the register map at the current subaddr and post-increment.
inline std::uint8_t fetch_and_advance() {
    const std::uint8_t byte = RegisterMap::read(g_state.subaddr);
    g_state.subaddr = static_cast<std::uint16_t>(g_state.subaddr + 1);
    return byte;
}

// Write one byte through the register map at the current subaddr and post-increment.
inline void store_and_advance(std::uint8_t byte) {
    RegisterMap::write(g_state.subaddr, byte);
    g_state.subaddr = static_cast<std::uint16_t>(g_state.subaddr + 1);
}

}  // namespace

void i2c_target_start(std::uint8_t address_7bit, std::uint32_t bus_speed_hz) {
    // Toggle peripheral reset to clear residual state, then enable the clock.
    RCC->APB1PRSTR |=  RCC_APB1Periph_I2C1;
    RCC->APB1PRSTR &= ~RCC_APB1Periph_I2C1;

    I2C1->CTLR1 |= I2C_CTLR1_SWRST;
    I2C1->CTLR1 &= ~I2C_CTLR1_SWRST;

    // FREQ field = APB1 clock in MHz. SYSCLK is 48 MHz, APB1 prescaler defaults
    // to /1 on CH32V003 (no AHB/APB divider in HCLK), so I²C input clock is the
    // full 48 MHz. The peripheral uses this to time the digital filter and
    // rise-time slope; the actual SCL frequency is set by CKCFGR below.
    constexpr std::uint32_t pclk_hz = FUNCONF_SYSTEM_CORE_CLOCK;
    constexpr std::uint32_t freq_mhz = pclk_hz / 1'000'000u;
    I2C1->CTLR2 = (I2C1->CTLR2 & ~I2C_CTLR2_FREQ) | (freq_mhz & I2C_CTLR2_FREQ);

    if (bus_speed_hz <= 100'000u) {
        // Standard mode: CCR = PCLK / (2 * bus). Minimum value is 4.
        std::uint32_t ccr = pclk_hz / (2u * bus_speed_hz);
        if (ccr < 4u) ccr = 4u;
        I2C1->CKCFGR = ccr & I2C_CKCFGR_CCR;        // F/S = 0
    } else {
        // Fast mode 33% duty: CCR = PCLK / (3 * bus). Minimum value is 1.
        std::uint32_t ccr = pclk_hz / (3u * bus_speed_hz);
        if (ccr < 1u) ccr = 1u;
        I2C1->CKCFGR = (ccr & I2C_CKCFGR_CCR) | I2C_CKCFGR_FS;
    }

    // 7-bit own address. Bit 0 of OADDR1 is the ADDMODE select on some parts;
    // leaving the high bits zero gives us 7-bit mode.
    I2C1->OADDR1 = static_cast<std::uint16_t>(address_7bit) << 1;
    I2C1->OADDR2 = 0;

    // Event + error + buffer (RxNE/TxE) interrupts.
    I2C1->CTLR2 |= I2C_CTLR2_ITEVTEN | I2C_CTLR2_ITERREN | I2C_CTLR2_ITBUFEN;

    NVIC_EnableIRQ(I2C1_EV_IRQn);
    NVIC_EnableIRQ(I2C1_ER_IRQn);

    // Enable the peripheral and ACK every received byte.
    I2C1->CTLR1 |= I2C_CTLR1_PE;
    I2C1->CTLR1 |= I2C_CTLR1_ACK;

    g_state = {};
}

}  // namespace syzygy

// ---------------------------------------------------------------------------
// ISRs.
// ---------------------------------------------------------------------------

extern "C" __attribute__((interrupt)) void I2C1_EV_IRQHandler() {
    using namespace syzygy;

    const std::uint16_t star1 = I2C1->STAR1;

    // EV1: address matched. Reading STAR1 then STAR2 clears ADDR.
    if (star1 & I2C_STAR1_ADDR) {
        const std::uint16_t star2 = I2C1->STAR2;
        const bool transmitting = (star2 & I2C_STAR2_TRA) != 0;
        if (transmitting) {
            // Read transaction: subaddr was latched by the preceding write
            // phase; pre-load the first byte into DR.
            I2C1->DATAR = fetch_and_advance();
            g_state.phase = Phase::DataStream;
        } else {
            g_state.phase = Phase::WaitSubAddrHi;
        }
        return;
    }

    // EV3: TxE — controller clocking out another byte.
    if (star1 & I2C_STAR1_TXE) {
        I2C1->DATAR = fetch_and_advance();
    }

    // EV2: RxNE — controller sent us a byte.
    if (star1 & I2C_STAR1_RXNE) {
        const std::uint8_t byte = static_cast<std::uint8_t>(I2C1->DATAR & 0xFFu);
        switch (g_state.phase) {
            case Phase::WaitSubAddrHi:
                g_state.subaddr = static_cast<std::uint16_t>(byte) << 8;
                g_state.phase   = Phase::WaitSubAddrLo;
                break;
            case Phase::WaitSubAddrLo:
                g_state.subaddr |= byte;
                g_state.phase    = Phase::DataStream;
                break;
            case Phase::DataStream:
                store_and_advance(byte);
                break;
            case Phase::Idle:
                break;  // stray byte before ADDR — drop
        }
    }

    // EV4: STOPF during target-receive. Clear: read STAR1, then write CTLR1.
    if (star1 & I2C_STAR1_STOPF) {
        I2C1->CTLR1 |= I2C_CTLR1_PE;
        g_state.phase = Phase::Idle;
    }
}

extern "C" __attribute__((interrupt)) void I2C1_ER_IRQHandler() {
    using namespace syzygy;

    const std::uint16_t star1 = I2C1->STAR1;

    // AF: NACK from controller — normal end of a read transaction.
    if (star1 & I2C_STAR1_AF) {
        I2C1->STAR1 = static_cast<std::uint16_t>(star1 & ~I2C_STAR1_AF);
        g_state.phase = Phase::Idle;
    }

    // BERR / ARLO bus errors: clear and reset our state.
    constexpr std::uint16_t kFatal = I2C_STAR1_BERR | I2C_STAR1_ARLO;
    if (star1 & kFatal) {
        I2C1->STAR1 = static_cast<std::uint16_t>(star1 & ~kFatal);
        g_state.phase = Phase::Idle;
    }
}
