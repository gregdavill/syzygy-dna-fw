# Vendor: ch32fun

This directory wraps [ch32fun](https://github.com/cnlohr/ch32v003fun) — a
minimal MIT-licensed register/startup layer for the CH32V003.

The Meson `vendor/ch32v003/meson.build` then compiles `ch32fun.c` into a
static library and exposes its include paths as `ch32fun_dep`. (Upstream
renamed the file from `ch32v003fun.c` to `ch32fun.c` when it grew CH32X
support; the repo URL still uses the old name.)

## Flashing

ch32fun also provides `minichlink`, which talks to the WCH-LinkE programmer
over USB. See `tools/flash.sh` at the repo root.
