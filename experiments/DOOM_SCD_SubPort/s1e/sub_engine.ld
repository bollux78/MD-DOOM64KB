/* Z8 sub-68000: vectors must precede cold/unlikely GCC text sections. */
ENTRY(subcpu_vectors)
SECTIONS
{
  . = 0;
  .text : {
    KEEP(*(.text.vectors))
    *(.text .text.* .gnu.linkonce.t.*)
  }
  .rodata : ALIGN(4) { *(.rodata .rodata.* .gnu.linkonce.r.*) }
  .data : ALIGN(4) { *(.data .data.* .sdata .sdata.*) }
  .bss (NOLOAD) : ALIGN(16) {
    __bss_start = .;
    *(.bss .bss.* .sbss .sbss.*)
    *(COMMON)
    . = ALIGN(16);
    _end = .;
  }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
  ASSERT(subcpu_vectors == 0, "68000 reset vectors are not at zero")
  ASSERT(_end < 0x7C000, "engine overlaps diagnostic trace/stack reserve")
}
