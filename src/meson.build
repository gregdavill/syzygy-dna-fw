i2c_speed_hz = get_option('i2c_speed_hz')
ga_window_mv = get_option('ga_adc_window_mv')

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
  'dna/dna_content.cpp',
)

firmware_inc = include_directories('.', 'dna')

# Raw firmware: 256-byte kPodBlob is still zero-filled here. Not built by
# default; we only need it as input to the patch step below.
firmware_raw = executable(
  'syzygy-dna-raw.elf',
  firmware_srcs,
  include_directories : firmware_inc,
  dependencies        : ch32fun_dep,
  cpp_args            : firmware_defs,
  c_args              : firmware_defs,
  link_depends        : files('../ldscripts' / ldscript_name),
  build_by_default    : false,
)

# Resolve the DNA YAML to bake in. Empty meson option => use the in-tree
# example, which lets `meson compile` produce a flashable ELF out of the box.
dna_yaml_opt = get_option('dna_yaml')
if dna_yaml_opt == ''
  dna_yaml = meson.project_source_root() / 'tools' / 'dna_example.yaml'
else
  dna_yaml = dna_yaml_opt
endif

dna_patch_script = files('../tools/dna_patch.py')

# Patched firmware: kPodBlob slot rewritten from the YAML. This is the ELF
# that gets flashed.
firmware_elf = custom_target(
  'syzygy-dna.elf',
  input            : firmware_raw,
  output           : 'syzygy-dna.elf',
  depend_files     : [dna_patch_script, files(dna_yaml)],
  command          : [python, dna_patch_script, '@INPUT@', dna_yaml, '-o', '@OUTPUT@'],
  build_by_default : true,
)

# .bin / .hex derive from the patched ELF so flash output reflects the YAML.
objcopy = find_program('riscv-none-elf-objcopy', required : false)
if objcopy.found()
  custom_target(
    'syzygy-dna.bin',
    input            : firmware_elf,
    output           : 'syzygy-dna.bin',
    command          : [objcopy, '-O', 'binary', '@INPUT@', '@OUTPUT@'],
    build_by_default : true,
  )
  custom_target(
    'syzygy-dna.hex',
    input            : firmware_elf,
    output           : 'syzygy-dna.hex',
    command          : [objcopy, '-O', 'ihex', '@INPUT@', '@OUTPUT@'],
    build_by_default : true,
  )
endif
