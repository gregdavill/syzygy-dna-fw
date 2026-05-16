i2c_speed_hz   = get_option('i2c_speed_hz')
ga_window_mv   = get_option('ga_adc_window_mv')

firmware_defs = [
  '-DSYZYGY_I2C_SPEED_HZ=' + i2c_speed_hz.to_string(),
  '-DGA_ADC_WINDOW_MV='    + ga_window_mv.to_string(),
]

firmware_srcs = files(
  'main.cpp',
  'system_init.cpp',
  'ga_adc.cpp',
  'register_map.cpp',
  'i2c_target.cpp',
)

firmware_inc = include_directories('.', 'dna')

firmware_elf = executable(
  'syzygy-dna.elf',
  firmware_srcs,
  include_directories : firmware_inc,
  dependencies        : ch32fun_dep,
  cpp_args            : firmware_defs,
  c_args              : firmware_defs,
  link_depends        : files('../ldscripts/ch32v003.ld'),
)

objcopy = find_program('riscv-none-elf-objcopy', required : false)
if objcopy.found()
  custom_target(
    'syzygy-dna.bin',
    input  : firmware_elf,
    output : 'syzygy-dna.bin',
    command : [objcopy, '-O', 'binary', '@INPUT@', '@OUTPUT@'],
    build_by_default : true,
  )
  custom_target(
    'syzygy-dna.hex',
    input  : firmware_elf,
    output : 'syzygy-dna.hex',
    command : [objcopy, '-O', 'ihex', '@INPUT@', '@OUTPUT@'],
    build_by_default : true,
  )
endif
