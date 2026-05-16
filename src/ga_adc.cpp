#include "ga_adc.hpp"

extern "C" {
#include "ch32fun.h"
}

#include <array>

namespace syzygy {
namespace {

// Configured at meson level; injected as -DGA_ADC_WINDOW_MV=...
#ifndef GA_ADC_WINDOW_MV
#define GA_ADC_WINDOW_MV 75
#endif

// Nominal R_GA voltages from spec Table 1, in millivolts.
// Index 0 -> address 0x30, index 15 -> address 0x3F.
constexpr std::array<std::uint16_t, 16> kNominalMv = {
    3147, 2944, 2740, 2548, 2341, 2135, 1926, 1734,
    1535, 1341, 1137,  933,  738,  541,  342,  153,
};

// CH32V003 ADC: 10-bit, Vref = VDDA (3.3 V). LSB ~= 3.223 mV.
// Convert raw counts -> mV via integer math: mv = raw * 3300 / 1023.
constexpr std::uint16_t raw_to_mv(std::uint16_t raw) {
    return static_cast<std::uint16_t>((static_cast<std::uint32_t>(raw) * 3300u) / 1023u);
}

// Single ADC1 conversion on channel 0 (PA2). Returns the raw 10-bit count.
std::uint16_t adc_sample_pa2() {
    // Configure ADC1: independent mode, single conversion, channel 0.
    ADC1->CTLR2 = ADC_ADON | ADC_EXTSEL;  // software trigger, ADC enabled
    ADC1->RSQR3 = 0;                      // first (and only) conversion: channel 0
    ADC1->RSQR1 = 0;                      // 1 conversion in regular group
    // Sampling time: longest (241 cycles for channel 0) to settle 10 kΩ source.
    ADC1->SAMPTR2 = 0b111;                // SMP0 = 111

    // Calibrate (recommended after enable).
    ADC1->CTLR2 |= ADC_RSTCAL;
    while (ADC1->CTLR2 & ADC_RSTCAL) { /* wait */ }
    ADC1->CTLR2 |= ADC_CAL;
    while (ADC1->CTLR2 & ADC_CAL) { /* wait */ }

    // Start conversion (SWSTART).
    ADC1->CTLR2 |= ADC_SWSTART;
    while (!(ADC1->STATR & ADC_EOC)) { /* wait */ }

    return static_cast<std::uint16_t>(ADC1->RDATAR & 0x3FFu);
}

}  // namespace

std::optional<std::uint8_t> resolve_geographical_address() {
    // Average a handful of samples to reduce noise.
    std::uint32_t accum = 0;
    constexpr int kSamples = 16;
    for (int i = 0; i < kSamples; ++i) {
        accum += adc_sample_pa2();
    }
    const std::uint16_t raw = static_cast<std::uint16_t>(accum / kSamples);
    const std::uint16_t mv = raw_to_mv(raw);

    for (std::size_t i = 0; i < kNominalMv.size(); ++i) {
        const int delta = static_cast<int>(mv) - static_cast<int>(kNominalMv[i]);
        if (delta >= -GA_ADC_WINDOW_MV && delta <= GA_ADC_WINDOW_MV) {
            return static_cast<std::uint8_t>(0x30 + i);
        }
    }
    return std::nullopt;
}

}  // namespace syzygy
