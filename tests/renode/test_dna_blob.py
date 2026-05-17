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


# I2C1 register magic offsets (must match tests/renode/platforms/ch32v003.repl)
INJ_START = 0x40005500
INJ_TX    = 0x40005508
INJ_STOP  = 0x4000550C
INJ_NACK  = 0x40005510


@pytest.mark.parametrize("nbytes", [4, 16, 40])
def test_read_dna_blob_from_zero(renode_run, expected_pod_blob, nbytes):
    """Read the first ``nbytes`` of kPodBlob and compare to the ELF copy."""

    # Build the per-test sequence: sub-address [0x80, 0x00] then nbytes reads.
    lines = [
        # Write transaction: address-match, sub-address hi (0x80), sub-address lo (0x00).
        'sysbus WriteDoubleWord 0x40005500 0',
        'emulation RunFor "0.005"',
        'sysbus WriteDoubleWord 0x40005504 0x80',
        'emulation RunFor "0.005"',
        'sysbus WriteDoubleWord 0x40005504 0x00',
        'emulation RunFor "0.005"',
        # Repeated start, read direction.
        'sysbus WriteDoubleWord 0x40005500 1',
        'emulation RunFor "0.005"',
    ]
    # Pull each byte.
    for i in range(nbytes):
        lines.append(f'echo ">> b{i:02d} = "')
        lines.append('sysbus ReadDoubleWord 0x40005508')
        lines.append('emulation RunFor "0.005"')
    # Close transaction.
    lines.append('sysbus WriteDoubleWord 0x40005510 0')
    lines.append('emulation RunFor "0.005"')

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

    body = "\n".join([
        # Write sub-address 0x00, 0x02.
        'sysbus WriteDoubleWord 0x40005500 0',
        'emulation RunFor "0.005"',
        'sysbus WriteDoubleWord 0x40005504 0x00',
        'emulation RunFor "0.005"',
        'sysbus WriteDoubleWord 0x40005504 0x02',
        'emulation RunFor "0.005"',
        'sysbus WriteDoubleWord 0x40005500 1',
        'emulation RunFor "0.005"',
        'echo ">> dna_major = "',
        'sysbus ReadDoubleWord 0x40005508',
        'emulation RunFor "0.005"',
        'echo ">> dna_minor = "',
        'sysbus ReadDoubleWord 0x40005508',
        'emulation RunFor "0.005"',
        'echo ">> eep_hi = "',
        'sysbus ReadDoubleWord 0x40005508',
        'emulation RunFor "0.005"',
        'echo ">> eep_lo = "',
        'sysbus ReadDoubleWord 0x40005508',
        'emulation RunFor "0.005"',
        'sysbus WriteDoubleWord 0x40005510 0',
        'emulation RunFor "0.005"',
    ])

    r = renode_run(body)
    # DNA spec version is 1.1 (see src/dna/dna_content.hpp).
    assert r["dna_major"] & 0xFF == 1
    assert r["dna_minor"] & 0xFF == 1
    # EEPROM size = sizeof(kPodBlob), big-endian. Must be > 0 either way.
    eep = ((r["eep_hi"] & 0xFF) << 8) | (r["eep_lo"] & 0xFF)
    assert eep > 0
