#!/usr/bin/env python3
"""
dna_patch: rewrite a syzygy-dna firmware ELF's compiled-in DNA blob from a YAML
spec, producing a new ELF.

The firmware embeds a default identity (manufacturer / product / serial / etc.)
as a constexpr std::array<uint8_t,N> placed in flash. For per-unit programming
you don't want to recompile just to bump a serial number — this tool reads the
YAML, builds a new 40-byte header + strings (computing the CRC-16/CCITT-FALSE),
and writes those bytes over the kPodBlob symbol's slot in the ELF.

  ./tools/dna_patch.py build-fw/src/syzygy-dna.elf identity.yaml -o patched.elf
  ./tools/dna_patch.py --self-test           # offline: verifies POD-CAMERA -> 0x72F9
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path
from typing import Iterable

import yaml
from elftools.elf.elffile import ELFFile


# Layout constants from SYZYGY DNA Specification v1.1 §3.2.5.
HEADER_LEN = 40
MAX_STRING_LEN = 255       # uint8 length field
MAX_VIO_RANGES = 4

# Default symbol substring; firmware uses `inline constexpr auto syzygy::dna::kPodBlob`.
DEFAULT_SYMBOL_NEEDLE = "kPodBlob"


# ----------------------------------------------------------------------------
# CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF, MSB-first, no reflection, no
# final XOR). Identical to the constexpr C++ implementation in src/dna/crc16.hpp.
# ----------------------------------------------------------------------------

def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        x = (crc >> 8) ^ b
        x ^= x >> 4
        crc = ((crc << 8) ^ (x << 12) ^ (x << 5) ^ x) & 0xFFFF
    return crc


# ----------------------------------------------------------------------------
# Serializer: YAML spec -> raw DNA bytes.
# ----------------------------------------------------------------------------

def _require_ascii(name: str, value: str) -> bytes:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string, got {type(value).__name__}")
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{name} must be ASCII: {exc}") from exc
    if len(encoded) > MAX_STRING_LEN:
        raise ValueError(f"{name} length {len(encoded)} exceeds {MAX_STRING_LEN}")
    return encoded


def _mv_to_units(name: str, mv: int) -> int:
    if not isinstance(mv, int):
        raise ValueError(f"{name} must be an integer mV, got {type(mv).__name__}")
    if mv < 0 or mv > 0xFFFF * 10:
        raise ValueError(f"{name} {mv} mV out of range")
    if mv % 10 != 0:
        raise ValueError(f"{name} {mv} mV is not a multiple of 10 mV (spec stores 10 mV units)")
    return mv // 10


def build_dna_blob(spec: dict) -> bytes:
    """Build the 40-byte header + strings exactly like src/dna/dna_blob.hpp."""
    manufacturer = _require_ascii("manufacturer", spec.get("manufacturer", ""))
    product      = _require_ascii("product",      spec.get("product",      ""))
    part_number  = _require_ascii("part_number",  spec.get("part_number",  ""))
    revision     = _require_ascii("revision",     spec.get("revision",     ""))
    serial       = _require_ascii("serial",       spec.get("serial",       ""))

    loads = spec.get("loads") or {}
    max_5v  = int(loads.get("max_5v_mA",  0))
    max_3v3 = int(loads.get("max_3v3_mA", 0))
    max_vio = int(loads.get("max_vio_mA", 0))
    for name, v in [("loads.max_5v_mA", max_5v),
                    ("loads.max_3v3_mA", max_3v3),
                    ("loads.max_vio_mA", max_vio)]:
        if v < 0 or v > 0xFFFF:
            raise ValueError(f"{name} {v} out of uint16 range")

    attrs = spec.get("attributes") or {}
    attr_bits = (
        (1 << 0 if attrs.get("is_lvds")       else 0) |
        (1 << 1 if attrs.get("is_doublewide") else 0) |
        (1 << 2 if attrs.get("is_txr4")       else 0)
    )

    ranges = list(spec.get("vio_ranges") or [])
    if len(ranges) > MAX_VIO_RANGES:
        raise ValueError(f"vio_ranges has {len(ranges)} entries, max {MAX_VIO_RANGES}")
    vio_units: list[tuple[int, int]] = []
    for i, r in enumerate(ranges):
        vio_units.append((
            _mv_to_units(f"vio_ranges[{i}].min_mV", r.get("min_mV", 0)),
            _mv_to_units(f"vio_ranges[{i}].max_mV", r.get("max_mV", 0)),
        ))
    while len(vio_units) < MAX_VIO_RANGES:
        vio_units.append((0, 0))

    dna_v = spec.get("dna_version") or {}
    req_v = spec.get("required_dna_version") or {}
    dna_major = int(dna_v.get("major", 1))
    dna_minor = int(dna_v.get("minor", 1))
    req_major = int(req_v.get("major", 0))
    req_minor = int(req_v.get("minor", 0))

    strings = manufacturer + product + part_number + revision + serial
    full_length = HEADER_LEN + len(strings)
    if full_length > 0xFFFF:
        raise ValueError(f"DNA full length {full_length} exceeds uint16 range")

    header = bytearray(HEADER_LEN)
    struct.pack_into("<H", header,  0, full_length)
    struct.pack_into("<H", header,  2, HEADER_LEN)
    header[4] = dna_major
    header[5] = dna_minor
    header[6] = req_major
    header[7] = req_minor
    struct.pack_into("<H", header,  8, max_5v)
    struct.pack_into("<H", header, 10, max_3v3)
    struct.pack_into("<H", header, 12, max_vio)
    struct.pack_into("<H", header, 14, attr_bits)
    for i, (mn, mx) in enumerate(vio_units):
        struct.pack_into("<H", header, 16 + i * 4 + 0, mn)
        struct.pack_into("<H", header, 16 + i * 4 + 2, mx)
    header[32] = len(manufacturer)
    header[33] = len(product)
    header[34] = len(part_number)
    header[35] = len(revision)
    header[36] = len(serial)
    header[37] = 0  # reserved

    # CRC over the first 38 bytes; stored MSB-first so that recomputing CRC
    # over all 40 bytes yields 0 (residue property).
    crc = crc16_ccitt(bytes(header[:38]))
    header[38] = (crc >> 8) & 0xFF
    header[39] = crc & 0xFF

    return bytes(header) + strings


# ----------------------------------------------------------------------------
# ELF lookup.
# ----------------------------------------------------------------------------

def find_symbol_slot(elf: ELFFile, needle: str) -> tuple[int, int, str]:
    """Return (file_offset, size_bytes, mangled_name) for the unique symbol whose
    name contains `needle`."""
    symtab = elf.get_section_by_name(".symtab")
    if symtab is None:
        raise RuntimeError("ELF has no .symtab — build with debug symbols (default in our cross-file)")

    matches = [s for s in symtab.iter_symbols() if needle in s.name and s["st_size"] > 0]
    if not matches:
        raise RuntimeError(f"no symbol matching {needle!r} found in {elf.stream.name}")
    if len(matches) > 1:
        names = ", ".join(s.name for s in matches[:6])
        raise RuntimeError(f"multiple symbols match {needle!r}: {names}")

    sym = matches[0]
    addr = sym["st_value"]
    size = sym["st_size"]

    for section in elf.iter_sections():
        sh_addr = section["sh_addr"]
        sh_size = section["sh_size"]
        if sh_size == 0:
            continue
        if sh_addr <= addr < sh_addr + sh_size:
            file_offset = section["sh_offset"] + (addr - sh_addr)
            return file_offset, size, sym.name

    raise RuntimeError(f"address 0x{addr:x} of {sym.name} not in any section")


# ----------------------------------------------------------------------------
# Self-test: reproduce spec POD-CAMERA example.
# ----------------------------------------------------------------------------

POD_CAMERA_SPEC = {
    "manufacturer": "Opal Kelly Incorporated",
    "product":      "POD-CAMERA",
    "part_number":  "POD-CAMERA-AR0330",
    "revision":     "A",
    "serial":       "1743000ABC",
    "loads":        {"max_5v_mA": 0, "max_3v3_mA": 510, "max_vio_mA": 50},
    "attributes":   {"is_lvds": True, "is_doublewide": False, "is_txr4": False},
    "vio_ranges":   [{"min_mV": 1800, "max_mV": 3300}],
    "dna_version":  {"major": 1, "minor": 0},   # spec example predates v1.1
}


def run_self_test() -> int:
    blob = build_dna_blob(POD_CAMERA_SPEC)
    errors = []
    if len(blob) != 101:
        errors.append(f"POD-CAMERA blob is {len(blob)} bytes, expected 101")
    if blob[38] != 0x72 or blob[39] != 0xF9:
        errors.append(f"POD-CAMERA CRC = {blob[38]:02X}{blob[39]:02X}, expected 72F9")
    if crc16_ccitt(blob[:40]) != 0:
        errors.append(f"residue over 40-byte header = 0x{crc16_ccitt(blob[:40]):04X}, expected 0")
    if errors:
        for e in errors:
            print(f"self-test: {e}", file=sys.stderr)
        return 1
    print("self-test: POD-CAMERA reproduced (CRC=0x72F9, residue=0) ✓")
    return 0


# ----------------------------------------------------------------------------
# CLI.
# ----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Patch the DNA blob inside a syzygy-dna firmware ELF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("elf_in",  type=Path, nargs="?", help="firmware ELF to read")
    parser.add_argument("yaml_in", type=Path, nargs="?", help="DNA spec YAML")
    parser.add_argument("-o", "--output", type=Path, help="patched ELF (required unless --self-test)")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL_NEEDLE,
                        help=f"symbol-name substring of the DNA slot (default: {DEFAULT_SYMBOL_NEEDLE})")
    parser.add_argument("--self-test", action="store_true",
                        help="verify POD-CAMERA reproduction against the spec's CRC 0x72F9 and exit")
    args = parser.parse_args(argv)

    if args.self_test:
        return run_self_test()

    if not args.elf_in or not args.yaml_in or not args.output:
        parser.error("elf_in, yaml_in, and -o/--output are required")

    spec = yaml.safe_load(args.yaml_in.read_text())
    if not isinstance(spec, dict):
        sys.exit(f"error: {args.yaml_in} did not parse to a mapping")

    blob = build_dna_blob(spec)

    elf_bytes = bytearray(args.elf_in.read_bytes())
    with args.elf_in.open("rb") as f:
        offset, slot_size, sym_name = find_symbol_slot(ELFFile(f), args.symbol)

    if len(blob) > slot_size:
        sys.exit(
            f"error: new DNA blob is {len(blob)} bytes but the firmware reserved "
            f"only {slot_size} bytes for {sym_name}.\n"
            f"       Rebuild firmware with longer placeholder strings in "
            f"src/dna/dna_content.hpp."
        )

    elf_bytes[offset : offset + len(blob)] = blob
    if len(blob) < slot_size:
        elf_bytes[offset + len(blob) : offset + slot_size] = b"\x00" * (slot_size - len(blob))

    args.output.write_bytes(bytes(elf_bytes))

    crc = (blob[38] << 8) | blob[39]
    print(f"patched {args.elf_in.name} -> {args.output}")
    print(f"  symbol:    {sym_name} @ file offset 0x{offset:x}")
    print(f"  slot size: {slot_size} bytes  ({'fits' if len(blob) <= slot_size else 'OVERFLOW'})")
    print(f"  new blob:  {len(blob)} bytes  (header CRC-16 = 0x{crc:04X})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
