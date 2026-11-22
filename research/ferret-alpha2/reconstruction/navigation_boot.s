/* Independent hardware-pipeline proof. Frozen captured scene, NOT a 3D engine.
 * Tiles are rebuilt from 80 four-pixel strips × 72 rows, then written to VDP.
 * No source bytes from Ferret executable code are used in this ROM. */
.section .text.boot
.global _start
_start:
.long 0x00fffffc, start
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long vblank_isr
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt
.long halt

.byte 83,69,71,65,32,77,69,71,65,32,68,82,73,86,69,32
.byte 40,67,41,66,79,76,76,85,88,55,56,32,50,48,50,54
.byte 70,69,82,82,69,84,32,82,69,83,69,65,82,67,72,32
.byte 45,32,78,65,86,73,71,65,66,76,69,32,69,49,77,49
.byte 32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32
.byte 70,69,82,82,69,84,32,82,69,83,69,65,82,67,72,32
.byte 45,32,78,65,86,73,71,65,66,76,69,32,69,49,77,49
.byte 32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32
.byte 71,77,32,48,48,48,48,48,48,48,48,45,48,48,0,0
.byte 74,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32
.byte 0,0,0,0,0,0,0,0,0,255,0,0,0,255,255,255
.byte 32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32
.byte 32,32,32,32,32,32,32,32,68,45,80,65,68,32,77,79
.byte 86,69,32,65,78,68,32,84,85,82,78,32,45,32,78,79
.byte 32,77,79,78,83,84,69,82,83,32,32,32,32,32,32,32
.byte 74,85,69,32,32,32,32,32,32,32,32,32,32,32,32,32
.org 0x200
start:
 move.w #0x2700,sr
 lea __bss_start,a0
 lea __bss_end,a1
clear_bss:
 cmpa.l a1,a0
 bcc.s bss_ready
 clr.b (a0)+
 bra.s clear_bss
bss_ready:
 move.b 0xa10001,d0
 andi.b #15,d0
 beq.s no_tmss
 move.l #0x53454741,0xa14000
no_tmss:
 move.w #0x100,0xa11100
 move.w #0,0xa11200
 lea 0xc00004,a4
 lea 0xc00000,a5
 move.w #0x8104,(a4)
 lea registers,a0
 move.w #0x8000,d1
 moveq #18,d2
regs:
 moveq #0,d0
 move.b (a0)+,d0
 or.w d1,d0
 move.w d0,(a4)
 addi.w #0x100,d1
 dbra d2,regs
 move.w #0x8104,(a4)
 move.w #0x8f02,(a4)
 move.l #0x40000000,(a4)
 lea frozen_vram,a0
 move.w #32767,d0
load_vram:
 move.w (a0)+,(a5)
 dbra d0,load_vram
 move.l #0xc0000000,(a4)
 lea frozen_cram,a0
 moveq #63,d0
load_cram:
 move.w (a0)+,(a5)
 dbra d0,load_cram
 move.l #0x40000010,(a4)
 lea frozen_vsram,a0
 moveq #39,d0
load_vsram:
 move.w (a0)+,(a5)
 dbra d0,load_vsram
 jsr scene_main
halt: bra.s halt
.global pipeline_write
pipeline_write:
 movem.l d2-d4/a2-a3/a5,-(sp)
 movea.l 28(sp),a2
 lea 0xc00000,a5
 moveq #17,d2
next_band:
 movea.l a2,a0
 moveq #39,d3
next_tile:
 lea 144(a0),a3
 moveq #3,d4
next_row:
 move.w (a0)+,d0
 swap d0
 move.w (a3)+,d0
 move.l d0,(a5)
 move.l d0,(a5)
 dbra d4,next_row
 adda.w #280,a0
 dbra d3,next_tile
 addq.l #8,a2
 dbra d2,next_band
 movem.l (sp)+,d2-d4/a2-a3/a5
 rts
.balign 2
registers: .incbin "registers.bin"
.balign 2
frozen_vram: .incbin "vram.bin"
frozen_cram: .incbin "cram.bin"
frozen_vsram: .incbin "vsram.bin"

.global vblank_isr
vblank_isr:
 movem.l d0-d1,-(sp)
 move.w 0xc00004,d0
 addq.w #1,navigation_vblanks
 move.b #0x40,0xa10003
 nop
 nop
 nop
 nop
 moveq #0,d0
 move.b 0xa10003,d0
 not.w d0
 andi.w #0x3f,d0
 move.b #0,0xa10003
 nop
 nop
 nop
 nop
 moveq #0,d1
 move.b 0xa10003,d1
 not.w d1
 andi.w #0x30,d1
 lsl.w #2,d1
 or.w d1,d0
 move.w d0,navigation_buttons
 move.b #0x40,0xa10003
 movem.l (sp)+,d0-d1
 rte
