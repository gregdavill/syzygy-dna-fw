"""Shared MMIO addresses for the Renode test suite.

CH32V003 peripheral base addresses are pulled from the reference manual.
The ``*_OFF`` constants are register / injection offsets *within* a
peripheral; absolute addresses are computed at module scope so tests can
import them directly.

The peripheral models in ``tests/renode/platforms/peripherals/*.repl``
carry their own copy of the offsets because Renode's embedded IronPython
can't import host modules. When changing an injection offset, change
*both* sides — this module is the source of truth for the Python tests,
the .repl is the source of truth for what the Renode peripheral actually
responds to.
"""

# --- Peripheral base addresses (CH32V003 RM §1.1) --------------------------

I2C1_BASE = 0x40005400
ADC1_BASE = 0x40012400

# --- I2C1 (mirrors tests/renode/platforms/peripherals/i2c1.repl) ----------

# Real-silicon registers
I2C1_CTLR1  = I2C1_BASE + 0x00
I2C1_CTLR2  = I2C1_BASE + 0x04
I2C1_OADDR1 = I2C1_BASE + 0x08
I2C1_DATAR  = I2C1_BASE + 0x10
I2C1_STAR1  = I2C1_BASE + 0x14
I2C1_STAR2  = I2C1_BASE + 0x18

# Test-only injection window (no real-silicon meaning; see i2c1.repl)
I2C1_INJ_START = I2C1_BASE + 0x100
I2C1_INJ_RX    = I2C1_BASE + 0x104
I2C1_INJ_TX    = I2C1_BASE + 0x108
I2C1_INJ_STOP  = I2C1_BASE + 0x10C
I2C1_INJ_NACK  = I2C1_BASE + 0x110

# --- ADC1 (mirrors tests/renode/platforms/peripherals/adc1.repl) ----------

# Test-only override: writing here seeds the raw count returned by the
# next RDATAR read. Outside the real silicon register set.
ADC1_INJ_RAW = ADC1_BASE + 0x200
