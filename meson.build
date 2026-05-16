project(
  'syzygy-dna',
  ['c', 'cpp'],
  version : '0.1.0',
  license : 'MIT',
  meson_version : '>=1.1',
  default_options : [
    'cpp_std=c++20',
    'warning_level=3',
    # LTO is disabled: triggers a GCC ICE in riscv_output_move when LTO'ing
    # ch32fun's printf with rv32ec_zicsr/ilp32e (xPack GCC 14.2). The target
    # is small enough that LTO isn't load-bearing anyway.
    'b_lto=false',
    'b_staticpic=false',
  ],
)

# This project builds in two modes:
#   - cross  (meson setup build-fw --cross-file cross/ch32v003.ini): firmware for CH32V003F4U6
#   - native (meson setup build-tests):                              host unit tests
# We dispatch on meson.is_cross_build() so the same tree handles both.

if meson.is_cross_build()
  add_project_arguments(
    '-fno-exceptions',
    '-fno-rtti',
    '-fno-threadsafe-statics',
    '-fno-use-cxa-atexit',
    '-ffunction-sections',
    '-fdata-sections',
    '-fno-common',
    language : 'cpp',
  )
  add_project_arguments(
    '-ffunction-sections',
    '-fdata-sections',
    '-fno-common',
    language : 'c',
  )
  add_project_link_arguments(
    '-Wl,--gc-sections',
    '-Wl,--print-memory-usage',
    '-nostartfiles',
    # Skip libc/libgloss: xPack ships them only for rv32imac/ilp32, and we
    # don't use any of their symbols anyway. -nolibc keeps libgcc going
    # through the driver (so multilib lookup still picks rv32ec/ilp32e).
    '-nolibc',
    '-T' + meson.project_source_root() / 'ldscripts' / 'ch32v003.ld',
    language : ['c', 'cpp'],
  )

  subdir('vendor/ch32v003')
  subdir('src')
else
  subdir('tests')
endif
