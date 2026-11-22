/* Independent hardware-pipeline proof. Frozen captured scene, NOT a 3D engine.
 * Tiles are rebuilt from 80 four-pixel strips × 72 rows, then written to VDP.
 * No source bytes from Ferret executable code are used in this ROM. */
.section .text
.global _start
_start:
.long 0x00fffffc, start
.rept 62
.long halt
.endr
.byte 83,69,71,65,32,77,69,71,65,32,68,82,73,86,69,32
.byte 40,67,41,66,79,76,76,85,88,55,56,32,50,48,50,54
.byte 70,69,82,82,69,84,32,80,73,80,69,76,73,78,69,32
.byte 82,69,83,69,65,82,67,72,32,45,32,83,84,65,84,73
.byte 67,32,80,82,79,79,70,32,32,32,32,32,32,32,32,32
.byte 70,69,82,82,69,84,32,80,73,80,69,76,73,78,69,32
.byte 82,69,83,69,65,82,67,72,32,45,32,83,84,65,84,73
.byte 67,32,80,82,79,79,70,32,32,32,32,32,32,32,32,32
.byte 71,77,32,48,48,48,48,48,48,48,48,45,48,48,0,0
.byte 74,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32
.byte 0,0,0,0,0,0,0,0,0,255,0,0,0,255,255,255
.byte 32,32,32,32,32,32,32,32,32,32,32,32,32,32,32,32
.byte 32,32,32,32,32,32,32,32,83,84,65,84,73,67,32,80
.byte 73,80,69,76,73,78,69,32,80,82,79,79,70,32,45,32
.byte 78,79,84,32,65,32,71,65,77,69,32,32,32,32,32,32
.byte 74,85,69,32,32,32,32,32,32,32,32,32,32,32,32,32
.org 0x200
start:
 move.w #0x2700,sr
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
 /* Both framebuffer tile banks receive independently reconstructed pixels. */
 move.l #0x42000000,(a4)
 bsr repack_vdp
 move.l #0x5c000001,(a4)
 bsr repack_vdp
 move.w #0x8144,(a4)
halt:
 bra.s halt
repack_vdp:
 lea source_pixels,a2
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
 rts
.balign 2
registers: .incbin "registers.bin"
.balign 2
frozen_vram: .incbin "vram.bin"
frozen_cram: .incbin "cram.bin"
frozen_vsram: .incbin "vsram.bin"
source_pixels: .incbin "source.bin"
rom_end:
