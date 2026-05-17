"""Pytest harness for Renode-driven firmware tests.

Each test renders a per-test .resc, spawns ``renode --disable-xwt --console
<script>``, captures stdout, and provides helpers to parse the values the
script printed. Renode is restarted between tests so machine state is
always fresh.

Fixtures:
    repo_root           absolute path to the syzygy-dna checkout
    firmware_elf        absolute path to the patched ELF (built by meson)
    expected_pod_blob   bytes() of kPodBlob extracted from the ELF
    mret_addresses      list[int] of mret instruction PCs in the firmware
                        (used to build the HSP shim's pop hooks)
    renode_run          callable: renode_run(body, pre_boot="") -> {label: int}
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

import pytest
from elftools.elf.elffile import ELFFile


REPO_ROOT = Path(__file__).resolve().parents[2]

# tools/dna_patch.py is the canonical "find the DNA slot in the ELF"
# implementation. We reuse it here so tests and the patcher agree on
# how the symbol is located.
sys.path.insert(0, str(REPO_ROOT / "tools"))
from dna_patch import find_symbol_slot  # noqa: E402


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def firmware_elf(repo_root: Path) -> Path:
    elf = repo_root / "build-fw" / "src" / "syzygy-dna.elf"
    if not elf.is_file():
        pytest.skip(
            f"Firmware ELF not built ({elf}). "
            "Run `meson setup build-fw --cross-file cross/ch32v003.ini && "
            "meson compile -C build-fw` first."
        )
    return elf


@pytest.fixture(scope="session")
def expected_pod_blob(firmware_elf: Path) -> bytes:
    """Pull the patched DNA blob out of the ELF.

    The blob is allocated in the firmware text section by
    [src/dna/dna_content.cpp] and rewritten post-link by
    [tools/dna_patch.py]. Whatever bytes the firmware serves over I2C must
    equal these bytes by construction.
    """
    raw = firmware_elf.read_bytes()
    offset, size, _ = find_symbol_slot(ELFFile(BytesIO(raw)), "kPodBlob")
    return raw[offset : offset + size]


@pytest.fixture(scope="session")
def mret_addresses(firmware_elf: Path) -> list[int]:
    """Disassemble the firmware and return every `mret` instruction address.

    The HSP shim installs a pop hook at each one to restore the caller-saved
    GPRs that the `__attribute__((interrupt))` handlers expect HSP to
    preserve. Deriving these from disassembly means changes to ISR code
    can't silently desync the hook list.
    """
    objdump = os.environ.get("OBJDUMP", "riscv-none-elf-objdump")
    result = subprocess.run(
        [objdump, "-d", str(firmware_elf)],
        capture_output=True, text=True, check=True,
    )
    addrs = [
        int(m.group(1), 16)
        for m in re.finditer(r"^\s*([0-9a-fA-F]+):\s+\S+\s+mret\b",
                             result.stdout, re.MULTILINE)
    ]
    if not addrs:
        raise RuntimeError(
            "no mret instructions found in firmware; HSP shim cannot "
            "install pop hooks"
        )
    return addrs


_PRINT_RE = re.compile(r"^>>\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*$", re.MULTILINE)


@pytest.fixture
def renode_run(repo_root: Path, firmware_elf: Path, mret_addresses: list[int]):
    """Render a .resc, run Renode against it, return parsed ``>> name = value`` lines.

    The caller passes the body of the .resc that runs *after* the firmware
    has reached its WFI idle loop. Tests use lines of the form
    ``echo ">> name = ..."`` followed by `sysbus ReadDoubleWord ...` to emit
    machine-readable values this harness scrapes.

    ``pre_boot`` is an optional chunk that runs after the platform + ELF
    load but before the boot-emulation step. Use it to seed peripheral
    state the firmware reads during init (most notably the ADC raw count
    via ``sysbus WriteDoubleWord 0x40012600 <raw>``).

    Renode timeout defaults to 60s but can be overridden with
    RENODE_TIMEOUT_S (useful on cold CI runners).
    """

    timeout_s = int(os.environ.get("RENODE_TIMEOUT_S", "60"))
    pop_hooks = "\n".join(f"cpu AddHook {addr:#x} $pop" for addr in mret_addresses)

    def run(body: str, pre_boot: str = "") -> dict[str, int]:
        setup = f"""\
:name: pytest-driven

using sysbus
mach create "ch32v003"
machine LoadPlatformDescription @{repo_root}/tests/renode/platforms/ch32v003.repl
sysbus LoadELF @{firmware_elf}

# QingKe gates MEI dispatch on PFIC enables alone, so ch32fun never writes
# mie. Renode's stock RV32 CPU needs mie.MEIE set for cpu@11 to dispatch,
# so we force it on here.
cpu MIE 0x800
cpu PerformanceInMips 50
logLevel 3
logLevel 0 sysbus

# --- HSP shim (claim from PFIC, redirect via vector table .word) -----------
cpu AddHook 0x2C \"\"\"
if 'hsp_stack' not in globals():
    hsp_stack = []
machine = self.GetMachine()
sys = machine.SystemBus
pfic = machine['sysbus.pfic']
claim = pfic.ReadDoubleWord(0xFD0)
if claim != 0xFFFFFFFF:
    handler_addr = sys.ReadDoubleWord(claim * 4)
    snap = {{}}
    for r in (1, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 28, 29, 30, 31):
        snap[r] = self.GetRegisterUnsafe(r).RawValue
    hsp_stack.append(snap)
    self.PC = handler_addr
\"\"\"

$pop = \"\"\"
if 'hsp_stack' in globals() and hsp_stack:
    snap = hsp_stack.pop()
    for r, v in snap.items():
        self.SetRegisterUnsafe(r, v)
\"\"\"
{pop_hooks}
"""

        boot = '\nemulation RunFor "1.0"\n'
        full = setup + pre_boot + boot + body + "\nquit\n"
        with tempfile.NamedTemporaryFile(
            "w", suffix=".resc", delete=False
        ) as tmp:
            tmp.write(full)
            tmp_path = Path(tmp.name)

        try:
            proc = subprocess.run(
                ["renode", "--disable-xwt", "--console", str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        # The Renode CLI dies on shutdown with a path-cleanup unhandled
        # exception on macOS; ignore exit status, parse stdout regardless.
        parsed: dict[str, int] = {}
        for match in _PRINT_RE.finditer(proc.stdout):
            name, raw = match.group(1), match.group(2)
            parsed[name] = int(raw, 0)
        if not parsed:
            raise AssertionError(
                f"renode produced no '>> name = value' lines.\n"
                f"--- stdout ---\n{proc.stdout}\n"
                f"--- stderr ---\n{proc.stderr}"
            )
        return parsed

    return run
