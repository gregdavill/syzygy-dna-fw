#!/usr/bin/env bash
# Flash syzygy-dna.bin to a CH32V003F4U6 using a WCH-LinkE programmer.
#
# Requires `minichlink` from ch32fun (built when you clone the submodule;
# binary lives in vendor/ch32v003/ch32fun/minichlink/).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

BIN="${1:-${ROOT}/build-fw/src/syzygy-dna.bin}"
MINICHLINK="${MINICHLINK:-${ROOT}/vendor/ch32v003/ch32fun/minichlink/minichlink}"

if [[ ! -x "$MINICHLINK" ]]; then
    echo "minichlink not found at $MINICHLINK" >&2
    echo "Build it with: make -C vendor/ch32v003/ch32fun/minichlink" >&2
    exit 1
fi

if [[ ! -f "$BIN" ]]; then
    echo "firmware binary not found: $BIN" >&2
    echo "Build it with: meson setup build-fw --cross-file cross/ch32v003.ini && meson compile -C build-fw" >&2
    exit 1
fi

# -w <file> <address>: write file to flash starting at address (0x00000000)
# -b: reboot to user code afterwards
exec "$MINICHLINK" -w "$BIN" 0x00000000 -b
