"""Pytest harness for Renode-driven firmware tests.

Each test renders a per-test .resc, spawns ``renode --disable-xwt --console
<script>``, captures stdout, and provides helpers to parse the values the
script printed. Renode is restarted between tests so machine state is
always fresh.

Fixtures:
    repo_root           absolute path to the syzygy-dna checkout
    firmware_elf        absolute path to the patched ELF (built by meson)
    expected_pod_blob   bytes() of kPodBlob extracted from the ELF
    renode_run          callable: run_renode(resc_body) -> {label: int}
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import pytest
from elftools.elf.elffile import ELFFile


REPO_ROOT = Path(__file__).resolve().parents[2]
KPODBLOB_SYMBOL = "_ZN6syzygy3dna8kPodBlobE"
KPODBLOB_SIZE_GUESS = 256  # we only need the first 40 bytes for the spec header


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

    The blob is allocated in the firmware text section by [src/dna/dna_content.cpp]
    and rewritten post-link by [tools/dna_patch.py]. So whatever bytes the
    firmware will return over I2C must equal these bytes by construction.
    """
    with firmware_elf.open("rb") as f:
        elf = ELFFile(f)
        symtab = elf.get_section_by_name(".symtab")
        sym = symtab.get_symbol_by_name(KPODBLOB_SYMBOL)
        if not sym:
            raise RuntimeError(f"{KPODBLOB_SYMBOL} not found in symtab")
        addr = sym[0].entry["st_value"]
        size = sym[0].entry["st_size"] or KPODBLOB_SIZE_GUESS
        for sec in elf.iter_sections():
            base = sec.header["sh_addr"]
            length = sec.header["sh_size"]
            if base <= addr < base + length:
                offset = addr - base
                return bytes(sec.data()[offset : offset + size])
        raise RuntimeError(f"{KPODBLOB_SYMBOL} @ {addr:#x} not inside any section")


_PRINT_RE = re.compile(r"^>>\s*(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*$", re.MULTILINE)


@pytest.fixture
def renode_run(repo_root: Path, firmware_elf: Path):
    """Render a .resc, run Renode against it, return parsed ``>> name = value`` lines.

    The caller passes the body of the .resc — everything after the standard
    boot prelude. Tests use `print` lines of the form ``echo ">> name = ..."``
    followed by `sysbus ReadDoubleWord ...` to emit machine-readable values
    this harness scrapes.
    """

    def run(body: str) -> dict[str, int]:
        prelude = f"""\
:name: pytest-driven

using sysbus
mach create "ch32v003"
machine LoadPlatformDescription @{repo_root}/tests/renode/platforms/ch32v003.repl
sysbus LoadELF @{firmware_elf}
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
cpu AddHook 0x414 $pop
cpu AddHook 0x516 $pop
cpu AddHook 0x58A $pop

# --- Boot to WFI ----------------------------------------------------------
emulation RunFor "1.0"
"""

        full = prelude + body + "\nquit\n"
        with tempfile.NamedTemporaryFile(
            "w", suffix=".resc", delete=False, dir=repo_root
        ) as tmp:
            tmp.write(full)
            tmp_path = Path(tmp.name)

        try:
            proc = subprocess.run(
                ["renode", "--disable-xwt", "--console", str(tmp_path)],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60,
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
