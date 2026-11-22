OUTPUT_ARCH(m68k)
ENTRY(_start)
MEMORY {
 ROM (rx) : ORIGIN = 0, LENGTH = 4M
 RAM (rw) : ORIGIN = 0xff0000, LENGTH = 64K
}
SECTIONS {
 .text : { *(.text.boot) *(.text*) *(.rodata*) } > ROM
 .data : { *(.data*) } > RAM AT>ROM
 .bss (NOLOAD) : { __bss_start = .; *(.bss*) *(COMMON) __bss_end = .; } > RAM
 /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
