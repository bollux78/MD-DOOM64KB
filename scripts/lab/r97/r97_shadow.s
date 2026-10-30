/* R97 (Claudio): Shadow joint pass, p=0 path of R92_ShadowPass in asm.
 * a0 = first A word of the first transferred row, a1 = r91_joint[mode] (65536 longs),
 * d6.w = rows (>=1), d5.w = words per row (>=1). B word = A word + 76 bytes (38 words).
 * Per block: key = (A&255)<<8 | (B&255); pair = table[key]; A = pair>>16; B = pair&0xffff.
 * Clobbers d0, d1, d5-d7, a0, a2 and condition codes. ~114 cycles/block (C: ~164). */
.text
.align 2
.globl R97_ShadowJoint
.type R97_ShadowJoint,@function
R97_ShadowJoint:
 subq.w #1,%d6
1:
 movea.l %a0,%a2
 move.w %d5,%d7
 subq.w #1,%d7
2:
 moveq #0,%d0
 move.w (%a0),%d0
 lsl.w #8,%d0
 move.b 77(%a0),%d0
 add.l %d0,%d0
 add.l %d0,%d0
 move.l (%a1,%d0.l),%d1
 move.w %d1,76(%a0)
 swap %d1
 move.w %d1,(%a0)+
 dbra %d7,2b
 lea 152(%a2),%a0
 dbra %d6,1b
 rts
.size R97_ShadowJoint,.-R97_ShadowJoint
