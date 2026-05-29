#pragma once

// Per-project ch32fun configuration for the SYZYGY DNA firmware.
// ch32fun.h includes this; the defines below select runtime features.

#define FUNCONF_USE_HSI           1   // internal 24 MHz HSI oscillator
#define FUNCONF_USE_HSE           0
#define FUNCONF_USE_PLL           1   // PLL doubles HSI -> 48 MHz core clock
#define FUNCONF_SYSTEM_CORE_CLOCK 48000000

// We don't use the debug or UART printf paths — the only host link is I2C.
#define FUNCONF_USE_DEBUGPRINTF   0
#define FUNCONF_USE_UARTPRINTF    0

// Clock-security-system: re-falls-back to HSI on HSE failure. We're already on
// HSI so it costs nothing to leave on.
#define FUNCONF_USE_CLK_SEC       1
