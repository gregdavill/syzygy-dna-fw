/*
 * Linker script for CH32V003F4U6
 *   16 KB Flash at 0x00000000 (mapped from 0x08000000 internally)
 *    2 KB SRAM  at 0x20000000
 *
 * Adapted from the ch32fun reference linker script. The vector table lives at
 * the start of flash; ch32fun's startup code points the RISC-V mtvec there.
 */

ENTRY(InterruptVector)

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 16K
    RAM   (xrw) : ORIGIN = 0x20000000, LENGTH = 2K
}

SECTIONS
{
    .init :
    {
        _sinit = .;
        KEEP(*(SORT_NONE(.init)))
        KEEP(*(SORT_NONE(.vector)))
        _einit = .;
    } >FLASH AT>FLASH

    .text :
    {
        . = ALIGN(4);
        *(.text)
        *(.text.*)
        . = ALIGN(4);
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
    } >FLASH AT>FLASH

    .fini :
    {
        KEEP(*(SORT_NONE(.fini)))
        . = ALIGN(4);
    } >FLASH AT>FLASH

    PROVIDE(_etext = .);

    .preinit_array :
    {
        PROVIDE_HIDDEN(__preinit_array_start = .);
        KEEP(*(.preinit_array))
        PROVIDE_HIDDEN(__preinit_array_end = .);
    } >FLASH AT>FLASH

    .init_array :
    {
        PROVIDE_HIDDEN(__init_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.init_array.*) SORT_BY_INIT_PRIORITY(.ctors.*)))
        KEEP(*(.init_array EXCLUDE_FILE(*crtbegin.o *crtbegin?.o *crtend.o *crtend?.o) .ctors))
        PROVIDE_HIDDEN(__init_array_end = .);
    } >FLASH AT>FLASH

    .fini_array :
    {
        PROVIDE_HIDDEN(__fini_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.fini_array.*) SORT_BY_INIT_PRIORITY(.dtors.*)))
        KEEP(*(.fini_array EXCLUDE_FILE(*crtbegin.o *crtbegin?.o *crtend.o *crtend?.o) .dtors))
        PROVIDE_HIDDEN(__fini_array_end = .);
    } >FLASH AT>FLASH

    .data :
    {
        . = ALIGN(4);
        _sdata = .;
        PROVIDE(_data_vma = .);
        PROVIDE(__global_pointer$ = . + 0x800);
        *(.gnu.linkonce.r.*)
        *(.data .data.*)
        *(.gnu.linkonce.d.*)
        *(.sdata .sdata.*)
        *(.sdata2.*)
        *(.gnu.linkonce.s.*)
        . = ALIGN(8);
        *(.srodata.cst16)
        *(.srodata.cst8)
        *(.srodata.cst4)
        *(.srodata.cst2)
        *(.srodata .srodata.*)
        . = ALIGN(4);
        _edata = .;
    } >RAM AT>FLASH

    _sidata = LOADADDR(.data);
    PROVIDE(_data_lma = LOADADDR(.data));

    .bss :
    {
        . = ALIGN(4);
        _sbss = .;
        *(.sbss*)
        *(.gnu.linkonce.sb.*)
        *(.bss*)
        *(.gnu.linkonce.b.*)
        *(COMMON*)
        . = ALIGN(4);
        _ebss = .;
    } >RAM

    PROVIDE(_end = _ebss);
    PROVIDE(end  = .);

    /* Stack grows down from the end of RAM */
    .stack ORIGIN(RAM) + LENGTH(RAM) - 0 (NOLOAD) :
    {
        PROVIDE(_eusrstack = .);
    } >RAM
}
