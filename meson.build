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

# This project is cross-only: there is no native code to build any more. The
# only on-host artefact is the Python DNA patcher (tools/dna_patch.py), and
# its --self-test runs as a meson test below.
assert(meson.is_cross_build(), 'configure with --cross-file cross/ch32v003.ini')

# Flags that apply identically to C and C++ — emit one symbol per
# function/data item so --gc-sections can drop unused ones at link time.
common_optim = ['-ffunction-sections', '-fdata-sections', '-fno-common']

add_project_arguments(common_optim, language : 'c')
add_project_arguments(
  common_optim + [
    '-fno-exceptions',
    '-fno-rtti',
    '-fno-threadsafe-statics',
    '-fno-use-cxa-atexit',
  ],
  language : 'cpp',
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

# Python interpreter for the DNA patcher. require pyelftools + pyyaml at
# configure time so we fail fast if they're missing.
python = import('python').find_installation(
  'python3',
  modules : ['elftools.elf.elffile', 'yaml'],
)

subdir('vendor/ch32v003')
subdir('src')

test(
  'dna_patch_self_test',
  python,
  args : [files('tools/dna_patch.py'), '--self-test'],
)
