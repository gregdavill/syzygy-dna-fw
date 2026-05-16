#pragma once

namespace syzygy {

// Bring up clocks (HSI + PLL = 48 MHz via ch32fun's SystemInit), enable
// peripheral clocks for GPIOC / AFIO / I2C1 / GPIOA / ADC1, and configure pin
// modes:
//   PA2 -> analog input (R_GA ADC sense)
//   PC1 -> AF open-drain (I2C1_SDA)
//   PC2 -> AF open-drain (I2C1_SCL)
void system_init();

}  // namespace syzygy
