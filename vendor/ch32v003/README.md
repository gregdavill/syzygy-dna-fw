# Vendor: ch32fun

This directory wraps [ch32fun](https://github.com/cnlohr/ch32v003fun) — a
minimal MIT-licensed register/startup layer for the CH32V003.

## One-time setup

```sh
git submodule add https://github.com/cnlohr/ch32v003fun vendor/ch32v003/ch32fun
# or, if you don't want a submodule:
git clone --depth=1 https://github.com/cnlohr/ch32v003fun vendor/ch32v003/ch32fun
```

The Meson `vendor/ch32v003/meson.build` then compiles `ch32v003fun.c` into a
static library and exposes its include paths as `ch32fun_dep`.

## Why ch32fun rather than the WCH StdPeriph SDK?

- Minimal — fits comfortably in 16 KB of flash with code to spare.
- MIT-licensed; no vendor toolchain dependency.
- Register-level access: this firmware drives I²C and ADC directly anyway, so
  a high-level peripheral library would just be dead weight.

## Flashing

ch32fun also provides `minichlink`, which talks to the WCH-LinkE programmer
over USB. See `tools/flash.sh` at the repo root.
