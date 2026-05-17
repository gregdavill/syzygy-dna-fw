"""Sweep ADC raw counts and verify the firmware programs the matching I2C address.

The geographical-address scheme in [src/ga_adc.cpp](../../src/ga_adc.cpp) maps
the voltage on PA2 to one of 16 I2C addresses (0x30..0x3F) using a fixed
nominal mV table per the SYZYGY DNA spec table 1. The firmware reads the
ADC, averages 16 samples, converts to mV, and picks the address whose
nominal mV is within ±GA_ADC_WINDOW_MV (default 75 mV) of the reading.

These tests seed the ADC's raw count via the test-only INJ_RAW offset
(0x40012600), boot the firmware, and assert that I2C1->OADDR1 ends up
configured for the expected 7-bit address (which the I2C target uses to
hardware-ACK the bus address).
"""

import pytest

# I2C1 OADDR1 is at 0x40005408 (CH32V003 RM). OADDR1[7:1] = address_7bit.
OADDR1 = 0x40005408
ADC1_INJ_RAW = 0x40012600   # = ADC1 base 0x40012400 + 0x200

# Mirrors kNominalMv from src/ga_adc.cpp. Index i -> I2C address 0x30 + i.
NOMINAL_MV = [
    3147, 2944, 2740, 2548, 2341, 2135, 1926, 1734,
    1535, 1341, 1137,  933,  738,  541,  342,  153,
]


def _mv_to_raw(mv: int) -> int:
    """Inverse of raw_to_mv() in ga_adc.cpp: mv = raw * 3300 / 1023."""
    return (mv * 1023) // 3300


@pytest.mark.parametrize("index", range(len(NOMINAL_MV)))
def test_ga_address_for_each_nominal(renode_run, index):
    """Seeding the ADC with the nominal raw count for index i lands on address 0x30+i."""
    expected_addr = 0x30 + index
    raw = _mv_to_raw(NOMINAL_MV[index])

    pre_boot = f'sysbus WriteDoubleWord {ADC1_INJ_RAW:#x} {raw}'
    body = '\n'.join([
        'echo ">> oaddr1 = "',
        f'sysbus ReadDoubleWord {OADDR1:#x}',
    ])

    result = renode_run(body, pre_boot=pre_boot)
    assert result["oaddr1"] == expected_addr << 1, (
        f"index={index} mv={NOMINAL_MV[index]} raw={raw}: "
        f"expected OADDR1=0x{(expected_addr << 1):02x} "
        f"(addr 0x{expected_addr:02x}), got 0x{result['oaddr1']:08x}"
    )


@pytest.mark.parametrize(
    "raw,expected_addr",
    [
        # Just inside the window on the high side of nominal index 5 (2135 mV).
        # 2135 + 70 = 2205 mV; 2205 * 1023 / 3300 = 683.
        (683, 0x35),
        # Just inside the window on the low side. 2135 - 70 = 2065 mV -> 640.
        (640, 0x35),
    ],
)
def test_ga_address_window_inside(renode_run, raw, expected_addr):
    """Voltages within ±GA_ADC_WINDOW_MV of a nominal still resolve to that address."""
    pre_boot = f'sysbus WriteDoubleWord {ADC1_INJ_RAW:#x} {raw}'
    body = '\n'.join([
        'echo ">> oaddr1 = "',
        f'sysbus ReadDoubleWord {OADDR1:#x}',
    ])
    result = renode_run(body, pre_boot=pre_boot)
    assert result["oaddr1"] == expected_addr << 1, (
        f"raw={raw}: expected OADDR1=0x{(expected_addr << 1):02x}, "
        f"got 0x{result['oaddr1']:08x}"
    )


@pytest.mark.parametrize(
    "raw,mv,why",
    [
        # Midpoint between nominal index 5 (2135 mV, addr 0x35) and
        # index 6 (1926 mV, addr 0x36). 2030 mV -> raw 629; 106 mV from
        # index 5 and 104 mV from index 6, both outside the ±75 mV window.
        (629, 2030, "between 0x35 and 0x36"),
        # Above the highest nominal (3147 mV) by more than the window.
        # 3300 mV -> raw 1023; 153 mV above 3147, outside ±75.
        (1023, 3300, "above 0x30 + window"),
        # Below the lowest nominal (153 mV) by more than the window.
        # raw 0 -> 0 mV; 153 mV below nominal index 15.
        (0, 0, "below 0x3F - window"),
    ],
)
def test_ga_address_dead_band(renode_run, raw, mv, why):
    """Outside-window readings leave the firmware spinning — OADDR1 stays 0."""
    pre_boot = f'sysbus WriteDoubleWord {ADC1_INJ_RAW:#x} {raw}'
    body = '\n'.join([
        'echo ">> oaddr1 = "',
        f'sysbus ReadDoubleWord {OADDR1:#x}',
    ])
    result = renode_run(body, pre_boot=pre_boot)
    assert result["oaddr1"] == 0, (
        f"raw={raw} (~{mv} mV, {why}): expected OADDR1=0, "
        f"got 0x{result['oaddr1']:08x} — firmware unexpectedly progressed past "
        f"resolve_geographical_address()"
    )
