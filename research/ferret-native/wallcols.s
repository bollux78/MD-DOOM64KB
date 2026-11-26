| fr_wall_cols: draw pass of wall_impl() for the paired-art path (packed==2), in 68000 assembly.
| int fr_wall_cols(const WallCtx *k, int m)
| Draws records m..ncol-1. Returns the index of the first record it could not handle (the C body then
| redraws that whole column: every write is idempotent and the clip arrays are only written at the end
| of a column), or ncol when all were drawn. Exactly the logic of the C draw pass in core.c.
|
| WallCtx offsets (must match core.c):
K_RECS   = 0      | record array (16 bytes each: r0 r1 r2 r3 inv.w j.b pad q.l)
K_NCOL   = 4
K_TOP    = 8      | &top[x0]  (uint16)
K_BOT    = 12     | &bottom[x0]
K_DEPTH  = 16     | &depth[x0]
K_PIX    = 20     | frame pixels
K_X0     = 24
K_FLAGS  = 28     | bit0 c, 1 u, 2 l, 3 fl, 4 sky, 5 solid(v<=3), 6 special(v==11||17), 7 textured, 8 linear
K_LOWO   = 32     | byte offset of 'low' in a record (2 or 4)
K_FSO    = 34     | byte offset of 'fs'  in a record (2, 4 or 6)
K_CE     = 36     | ceiling byte, even rows
K_CO     = 37     | ceiling byte, odd rows (nibbles swapped)
K_FE     = 38     | floor byte, even rows
K_FO     = 39     | floor byte, odd rows
K_ZSH    = 40     | sar(z,1)
K_SCAL   = 44     | scalers
K_IND    = 48     | indices or 0
K_UDAT   = 52     | upper texture data, 0 if the C path must handle it
K_UORG   = 56
K_LDAT   = 60
K_LORG   = 64
K_SKYC   = 68     | table of 160 sky column pointers (by x)
K_SKYR   = 72     | sky row offsets (uint16, by y)
K_SWAP   = 76     | 256-byte nibble swap table
K_GEN    = 80     | generated scaler entry-point table, or null
| locals (link a6,#-40)
L_T   = -2
L_B   = -4
L_X   = -8
L_CB  = -12       | column base: pixels + (x>>1)*144 + (x&1)
L_LOW = -14
L_FS  = -16
L_SC  = -20       | scaler row pointer for this column
L_OFF = -24       | texture offset (column part + sar(z,1))
L_J2  = -28       | 2*j
L_GEN = -32       | generated scaler entry-point row, or null

    .macro clamp_word branch
    cmp.w %d1,%d0
    \branch\().s 1f
    move.w %d1,%d0
1:
    .endm

    .text
    .globl fr_wall_cols
    .even
fr_wall_cols:
    link %a6,#-40
    movem.l %d2-%d7/%a2-%a5,-(%sp)
    move.l 8(%a6),%a5
    move.l 12(%a6),%d7
    move.l K_FLAGS(%a5),%d6           | d6 = flags for the whole wall
.Lloop:
    cmp.l K_NCOL(%a5),%d7
    bge .Ldone
    move.l %d7,%d0
    lsl.l #4,%d0
    move.l K_RECS(%a5),%a4
    add.l %d0,%a4
    | j, x, t, b, column base
    moveq #0,%d0
    move.b 10(%a4),%d0
    move.l %d0,%d1
    add.l K_X0(%a5),%d1
    move.l %d1,L_X(%a6)
    add.l %d0,%d0
    move.l %d0,L_J2(%a6)
    move.l K_TOP(%a5),%a0
    move.w (%a0,%d0.l),L_T(%a6)
    move.l K_BOT(%a5),%a0
    move.w (%a0,%d0.l),L_B(%a6)
    move.l %d1,%d2
    lsr.l #1,%d2
    move.l %d2,%d3
    lsl.l #7,%d2
    lsl.l #4,%d3
    add.l %d3,%d2
    and.l #1,%d1
    add.l %d1,%d2
    add.l K_PIX(%a5),%d2
    move.l %d2,L_CB(%a6)
    move.w K_LOWO(%a5),%d0
    move.w (%a4,%d0.w),L_LOW(%a6)
    move.w K_FSO(%a5),%d0
    move.w (%a4,%d0.w),L_FS(%a6)

    | ---- texture setup first (only checks; may fall back before anything is drawn) ----
    btst #7,%d6
    beq .Lnotex
    btst #1,%d6
    bne.s 1f
    btst #2,%d6
    beq .Lnotex
1:  moveq #0,%d4
    move.w 8(%a4),%d4                 | inv
    move.l 12(%a4),%d0                | q
    btst #8,%d6
    bne.s 2f                          | linear: offset from q
    tst.w %d4
    beq .Lfallback                    | !linear && !inv: C reports -4
    move.l %d0,%d1
    clr.w %d1
    swap %d1                          | q>>16
    cmp.l %d4,%d1
    bcc .Lfallback                    | quotient would not fit DIVU.W: C path
    divu.w %d4,%d0
2:  and.l #0x1f80,%d0
    add.l K_ZSH(%a5),%d0
    move.l %d0,L_OFF(%a6)
    move.l %d4,%d1
    lsr.w #5,%d1                      | inv>>5
    move.l K_IND(%a5),%d2
    beq.s 3f
    move.l %d2,%a0
    moveq #0,%d2
    move.b (%a0,%d1.w),%d2
    move.l %d2,%d1
3:  move.l %d1,%d2                    | *144 bytes (72 int16)
    lsl.l #7,%d1
    lsl.l #4,%d2
    add.l %d2,%d1
    add.l K_SCAL(%a5),%d1
    move.l %d1,L_SC(%a6)
    move.l K_GEN(%a5),%d2
    beq.s 4f
    sub.l K_SCAL(%a5),%d1
    add.l %d1,%d1                    | *288 bytes (72 entry pointers)
    add.l %d1,%d2
4:  move.l %d2,L_GEN(%a6)
.Lnotex:
    | ---- ceiling: rows [t, min(b,r0)) ----
    btst #0,%d6
    beq.s .Lnoceil
    move.w L_B(%a6),%d0
    move.w (%a4),%d1
    clamp_word ble
    move.w L_T(%a6),%d2
    cmp.w %d2,%d0
    ble.s .Lnoceil
    sub.w %d2,%d0                     | n
    move.l L_CB(%a6),%a0
    add.w %d2,%a0
    add.w %d2,%a0
    moveq #1,%d1
    and.w %d2,%d1                     | parity of y0
    btst #4,%d6
    beq.s 6f
    move.l K_SKYC(%a5),%a1
    move.l L_X(%a6),%d3
    add.l %d3,%d3
    add.l %d3,%d3
    move.l (%a1,%d3.l),%a1            | sky column
    move.l K_SKYR(%a5),%a2
    add.w %d2,%a2
    add.w %d2,%a2
    move.l K_SWAP(%a5),%a3
    bsr .Lfsky
    bra.s .Lnoceil
6:  move.b K_CE(%a5),%d2
    move.b K_CO(%a5),%d3
    bsr .Lfsolid
.Lnoceil:
    | ---- textured spans ----
    btst #7,%d6
    beq .Lnotex2
    btst #1,%d6
    beq.s 7f
    move.w L_T(%a6),%d0
    move.w (%a4),%d1
    clamp_word bge
    move.w %d0,%d2
    move.w L_B(%a6),%d0
    move.w 2(%a4),%d1
    clamp_word ble
    move.w %d0,%d3
    move.l K_UDAT(%a5),%a1
    move.l K_UORG(%a5),%d4
    bsr .Ltex
    bne .Lfallback
7:  btst #2,%d6
    beq.s .Lnotex2
    move.w L_T(%a6),%d0
    move.w L_LOW(%a6),%d1
    clamp_word bge
    move.w %d0,%d2
    move.w L_B(%a6),%d0
    move.w 6(%a4),%d1
    clamp_word ble
    move.w %d0,%d3
    move.l K_LDAT(%a5),%a1
    move.l K_LORG(%a5),%d4
    bsr .Ltex
    bne .Lfallback
.Lnotex2:
    | ---- floor: rows [max(t,fs), b) ----
    btst #3,%d6
    beq.s .Lnofloor
    move.w L_T(%a6),%d0
    move.w L_FS(%a6),%d1
    clamp_word bge
    move.w %d0,%d2                    | y0
    move.w L_B(%a6),%d0
    sub.w %d2,%d0                     | n
    ble.s .Lnofloor
    move.l L_CB(%a6),%a0
    add.w %d2,%a0
    add.w %d2,%a0
    moveq #1,%d1
    and.w %d2,%d1
    move.b K_FE(%a5),%d2
    move.b K_FO(%a5),%d3
    btst #6,%d6                       | special: color 0 when t>=r2 && b>=r3
    beq.s 8f
    move.w L_T(%a6),%d4
    cmp.w 4(%a4),%d4
    blt.s 8f
    move.w L_B(%a6),%d4
    cmp.w 6(%a4),%d4
    blt.s 8f
    moveq #0,%d2
    moveq #0,%d3
8:  bsr .Lfsolid
.Lnofloor:
    | ---- clip update ----
    move.l L_J2(%a6),%d5
    move.l K_TOP(%a5),%a0
    move.l K_BOT(%a5),%a1
    btst #5,%d6
    beq.s 9f
    clr.w (%a0,%d5.l)
    clr.w (%a1,%d5.l)
    move.l K_DEPTH(%a5),%a2
    move.w 8(%a4),(%a2,%d5.l)
    bra .Lnext
9:  move.w L_T(%a6),%d2               | t
    move.w L_B(%a6),%d3               | b
    | et = u ? r1 : (c ? r0 : t)
    move.w %d2,%d0
    btst #0,%d6
    beq.s 10f
    move.w (%a4),%d0
10: btst #1,%d6
    beq.s 11f
    move.w 2(%a4),%d0
11: | eb = l ? low : (fl ? fs : b)
    move.w %d3,%d1
    btst #3,%d6
    beq.s 12f
    move.w L_FS(%a6),%d1
12: btst #2,%d6
    beq.s 13f
    move.w L_LOW(%a6),%d1
13: | nt = min(b, max(t,et))
    move.w %d0,%d4
    cmp.w %d2,%d4
    bge.s 14f
    move.w %d2,%d4
14: cmp.w %d3,%d4
    ble.s 15f
    move.w %d3,%d4
15: | nb = max(t, min(b,eb))  (d7 holds m: save it)
    move.l %d7,-(%sp)
    move.w %d1,%d7
    cmp.w %d3,%d7
    ble.s 17f
    move.w %d3,%d7
17: cmp.w %d2,%d7
    bge.s 18f
    move.w %d2,%d7
18: | closed if (c && b<et) || (fl && t>=eb)
    btst #0,%d6
    beq.s 19f
    cmp.w %d0,%d3
    blt.s 21f
19: btst #3,%d6
    beq.s 20f
    cmp.w %d1,%d2
    bge.s 21f
20: move.w %d4,(%a0,%d5.l)
    move.w %d7,(%a1,%d5.l)
    move.l (%sp)+,%d7
    bra.s .Lnext
21: clr.w (%a0,%d5.l)
    clr.w (%a1,%d5.l)
    move.l K_DEPTH(%a5),%a2
    move.w 8(%a4),(%a2,%d5.l)
    move.l (%sp)+,%d7
.Lnext:
    addq.l #1,%d7
    bra .Lloop
.Lfallback:
.Ldone:
    move.l %d7,%d0
    movem.l (%sp)+,%d2-%d7/%a2-%a5
    unlk %a6
    rts

| .Ltex: validate and draw [d2,d3) from texture a1 (origin d4).
| Returns Z=1 on success or an empty span. On failure, C retries this column;
| previous ceiling/upper writes are idempotent and clip has not been updated.
.Ltex:
    cmp.w %d3,%d2
    bge .Ltex_ok
    move.w %d3,%d5
    sub.w %d2,%d5                    | n
    cmpa.l #0,%a1
    beq .Ltex_bad
    add.l L_OFF(%a6),%d4             | base
    move.l L_SC(%a6),%a3
    add.w %d2,%a3
    add.w %d2,%a3                    | sc + y0 (y0 is nonnegative after clipping)
    move.w (%a3),%d0
    ext.l %d0
    add.l %d4,%d0                    | first sample address
    cmp.l #24576,%d0
    bcc .Ltex_bad
    move.w %d5,%d1
    add.w %d1,%d1
    subq.w #2,%d1
    move.w (%a3,%d1.w),%d1
    ext.l %d1
    add.l %d4,%d1                    | last sample address
    cmp.l #24576,%d1
    bcc .Ltex_bad
    move.l L_CB(%a6),%a0
    move.l K_SWAP(%a5),%a2
    eor.l %d0,%d1
    and.w #0xe000,%d1               | both samples are below 24576
    bne.s .Ltex_wrapped
    and.w #0xe000,%d0               | same 8 KB block: rebase once
    sub.l %d0,%d4
    move.l L_GEN(%a6),%d1
    beq.s .Ltex_unwrapped
    move.l %d1,%a3
    move.w %d2,%d1
    lsl.w #2,%d1
    move.l (%a3,%d1.w),%a3
    add.l %d4,%a1
    move.l %d6,-(%sp)
    moveq #0,%d6
    move.w %d5,%d6
    subq.w #1,%d6
    moveq #0,%d0
    jsr (%a3)
    move.l (%sp)+,%d6
    bra.s .Ltex_ok
.Ltex_unwrapped:
    bsr.s .Ltex_dst
    jsr fr_col_pair_rn
    bra.s .Ltex_ok
.Ltex_wrapped:
    bsr.s .Ltex_dst
    jsr fr_col_pair_r
.Ltex_ok:
    moveq #0,%d0
    rts
.Ltex_bad:
    moveq #1,%d0
    rts
.Ltex_dst:
    add.w %d2,%a0
    add.w %d2,%a0
    moveq #1,%d3
    and.w %d2,%d3
    ext.l %d5
    rts

| .Lfsolid: a0 dst, d0 n (>0), d1 parity, d2 even byte, d3 odd byte
.Lfsolid:
    tst.w %d1
    beq.s 1f
    move.b %d3,(%a0)
    addq.l #2,%a0
    subq.w #1,%d0
1:  move.w %d0,%d1
    lsr.w #1,%d1
    beq.s 3f
    subq.w #1,%d1
2:  move.b %d2,(%a0)
    move.b %d3,2(%a0)
    addq.l #4,%a0
    dbra %d1,2b
3:  btst #0,%d0
    beq.s 4f
    move.b %d2,(%a0)
4:  rts

| .Lfsky: a0 dst, d0 n (>0), d1 parity, a1 sky column, a2 row offsets at y0, a3 swap table
.Lfsky:
    moveq #0,%d2
    tst.w %d1
    beq.s 1f
    move.w (%a2)+,%d3
    move.b (%a1,%d3.w),%d2
    move.b (%a3,%d2.w),(%a0)
    addq.l #2,%a0
    subq.w #1,%d0
1:  move.w %d0,%d1
    lsr.w #1,%d1
    beq.s 3f
    subq.w #1,%d1
2:  move.w (%a2)+,%d3
    move.b (%a1,%d3.w),(%a0)
    move.w (%a2)+,%d3
    move.b (%a1,%d3.w),%d2
    move.b (%a3,%d2.w),2(%a0)
    addq.l #4,%a0
    dbra %d1,2b
3:  btst #0,%d0
    beq.s 4f
    move.w (%a2)+,%d3
    move.b (%a1,%d3.w),(%a0)
4:  rts
