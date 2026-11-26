OUTPUT_ARCH(m68k)
ENTRY(_start)
SECTIONS {
  .vectors 0 : { KEEP(*(.vectors)) }
  .header 0x100 : { KEEP(*(.header)) }
  .text 0x200 : { *(.text.start) *(.text .text.*) *(.rodata .rodata.*) . = ALIGN(2); }
  .data 0xff0000 : AT(LOADADDR(.text)+SIZEOF(.text)) { *(.data .data.*) }
  .bss 0xff0000 (NOLOAD) : { . = ALIGN(4); __bss_start = .; *(.bss .bss.* COMMON) . = ALIGN(4); __bss_end = .; }
  /DISCARD/ : { *(.comment .note* .eh_frame* .debug*) }
  ASSERT(SIZEOF(.vectors)==256, "bad vector table")
  ASSERT(SIZEOF(.header)==256, "bad header")
  ASSERT(SIZEOF(.data)==0, "initialized writable data requires startup copy")
  ASSERT(__bss_start == 0xff0000, "BSS must begin in WRAM")
  ASSERT(__bss_end <= 0xffe800, "WRAM overlaps diagnostic mailbox/stack")
  ASSERT(LOADADDR(.text)+SIZEOF(.text) < 0x200000, "ROM overlaps SRAM16")
}
