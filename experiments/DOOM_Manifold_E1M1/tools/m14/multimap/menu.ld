OUTPUT_ARCH(m68k)
SECTIONS { .text 0 : { *(.text.vec) *(.text) *(.text.*) *(.rodata) *(.rodata.*) } /DISCARD/ : { *(.comment) *(.eh_frame) } }
