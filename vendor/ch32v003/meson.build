# ch32fun integration.
#
# Expected layout (upstream renamed ch32v003fun -> ch32fun):
#   vendor/ch32v003/ch32fun/                <- clone of github.com/cnlohr/ch32v003fun
#                          /ch32fun/ch32fun.c
#                          /ch32fun/ch32fun.h
#                          /ch32fun/ch32v003hw.h
#                          /ch32fun/...
#
# Add as submodule with:
#   git submodule add https://github.com/cnlohr/ch32v003fun vendor/ch32v003/ch32fun

ch32fun_dir = meson.current_source_dir() / 'ch32fun' / 'ch32fun'

if not import('fs').exists(ch32fun_dir / 'ch32fun.c')
  error('ch32fun not found. Run: git submodule add https://github.com/cnlohr/ch32v003fun vendor/ch32v003/ch32fun')
endif

# Configuration lives in funconfig.h (next to this file) — ch32fun.h includes
# it via the include path. Keep -D's out of the build command so the config is
# discoverable in one place.
ch32fun_lib = static_library(
  'ch32fun',
  ch32fun_dir / 'ch32fun.c',
  include_directories : include_directories('.', 'ch32fun/ch32fun'),
  c_args : [
    '-Wno-unused-parameter',
    '-Wno-unused-variable',
    '-Wno-pedantic',
    '-Wno-unused-function',
  ],
  pic : false,
)

ch32fun_dep = declare_dependency(
  link_with : ch32fun_lib,
  include_directories : include_directories('.', 'ch32fun/ch32fun'),
)
