"""End-to-end test: read the DNA blob over emulated I2C, assert byte-for-byte.

The firmware reaches its WFI idle loop, the harness injects an I2C
controller-side transaction (write [0x80, 0x00] sub-address, repeated-start
read), and we pull bytes via the I2C peripheral's INJ_TX magic offset.
Each pull triggers a TXE-driven IRQ, the ISR stages the next byte from
RegisterMap::read(0x8000 + offset).

Pass criterion: every byte pulled from emulated I2C must equal the
corresponding kPodBlob byte extracted from the linked ELF.
"""

import pytest


# I2C1 register / injection offsets (must match tests/renode/platforms/peripherals/i2c1.repl).
INJ_START = 0x40005500
INJ_RX    = 0x40005504
INJ_TX    = 0x40005508
INJ_STOP  = 0x4000550C
INJ_NACK  = 0x40005510

# Sub-address space dispatcher constants (must match src/register_map.cpp).
DNA_BASE        = 0x8000
EXPECTED_EEPROM = 4096   # = src/dna/dna_content.hpp kPodBlobSize


def _settle():
    """One short slice of emulated time, enough for the firmware ISR to run."""
    return 'emulation RunFor "0.005"'


def _write_subaddr(subaddr: int) -> list[str]:
    """Address-match-W + sub-address hi/lo (the firmware latches them into g_state)."""
    return [
        f'sysbus WriteDoubleWord {INJ_START:#x} 0',
        _settle(),
        f'sysbus WriteDoubleWord {INJ_RX:#x} {(subaddr >> 8) & 0xFF:#x}',
        _settle(),
        f'sysbus WriteDoubleWord {INJ_RX:#x} {subaddr & 0xFF:#x}',
        _settle(),
    ]


def _begin_read() -> list[str]:
    return [f'sysbus WriteDoubleWord {INJ_START:#x} 1', _settle()]


def _read_byte(label: str) -> list[str]:
    return [
        f'echo ">> {label} = "',
        f'sysbus ReadDoubleWord {INJ_TX:#x}',
        _settle(),
    ]


def _close() -> list[str]:
    return [f'sysbus WriteDoubleWord {INJ_NACK:#x} 0', _settle()]


@pytest.mark.parametrize("nbytes", [4, 16, 40])
def test_read_dna_blob_from_zero(renode_run, expected_pod_blob, nbytes):
    """Read the first ``nbytes`` of kPodBlob and compare to the ELF copy."""

    lines = _write_subaddr(DNA_BASE) + _begin_read()
    for i in range(nbytes):
        lines += _read_byte(f"b{i:02d}")
    lines += _close()

    result = renode_run("\n".join(lines))

    got = bytes(result[f"b{i:02d}"] & 0xFF for i in range(nbytes))
    want = expected_pod_blob[:nbytes]
    assert got == want, (
        f"DNA blob mismatch for first {nbytes} bytes:\n"
        f"  got:  {got.hex(' ')}\n"
        f"  want: {want.hex(' ')}"
    )


def test_dna_version_registers(renode_run):
    """Read 0x0002..0x0005 (DNA major/minor + EEPROM size)."""

    lines = _write_subaddr(0x0002) + _begin_read()
    lines += _read_byte("dna_major")
    lines += _read_byte("dna_minor")
    lines += _read_byte("eep_hi")
    lines += _read_byte("eep_lo")
    lines += _close()

    r = renode_run("\n".join(lines))
    # DNA spec version is 1.1 (see src/dna/dna_content.hpp).
    assert r["dna_major"] & 0xFF == 1
    assert r["dna_minor"] & 0xFF == 1
    # EEPROM size = sizeof(kPodBlob), big-endian.
    eep = ((r["eep_hi"] & 0xFF) << 8) | (r["eep_lo"] & 0xFF)
    assert eep == EXPECTED_EEPROM, (
        f"EEPROM size register = {eep} (0x{eep:04x}), "
        f"expected {EXPECTED_EEPROM} (kPodBlobSize)"
    )
