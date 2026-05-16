# Native (host) tests. Pure constexpr code from src/dna/*.hpp, no MCU code.

test_inc = include_directories('../src/dna')

test('crc16',     executable('test_crc16',    'test_crc16.cpp',    include_directories : test_inc))
test('dna_blob',  executable('test_dna_blob', 'test_dna_blob.cpp', include_directories : test_inc))
