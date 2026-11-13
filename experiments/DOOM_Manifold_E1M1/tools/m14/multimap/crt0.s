        .section .text.vec
        .global _vectors
_vectors:
        dc.l 0xE1000000, _start
        dc.l stub2
        dc.l stub3
        dc.l stub4
        dc.l stub5
        dc.l stub6
        dc.l stub7
        dc.l stub8
        dc.l stub9
        dc.l stub10
        dc.l stub11
        dc.l stub12
        dc.l stub13
        dc.l stub14
        dc.l stub15
        dc.l stub16
        dc.l stub17
        dc.l stub18
        dc.l stub19
        dc.l stub20
        dc.l stub21
        dc.l stub22
        dc.l stub23
        dc.l stub24
        dc.l stub25
        dc.l stub26
        dc.l stub27
        dc.l stub28
        dc.l stub29
        dc.l stub30
        dc.l stub31
        dc.l stub32
        dc.l stub33
        dc.l stub34
        dc.l stub35
        dc.l stub36
        dc.l stub37
        dc.l stub38
        dc.l stub39
        dc.l stub40
        dc.l stub41
        dc.l stub42
        dc.l stub43
        dc.l stub44
        dc.l stub45
        dc.l stub46
        dc.l stub47
        dc.l stub48
        dc.l stub49
        dc.l stub50
        dc.l stub51
        dc.l stub52
        dc.l stub53
        dc.l stub54
        dc.l stub55
        dc.l stub56
        dc.l stub57
        dc.l stub58
        dc.l stub59
        dc.l stub60
        dc.l stub61
        dc.l stub62
        dc.l stub63

        .org 0x100
        .ascii "SEGA SSF        "
        .ascii "(C)MANIFOLD 2026 "
        .ascii "MANIFOLD DOOM E1 LEVEL SELECT            "
        .ascii "MANIFOLD DOOM E1 LEVEL SELECT            "
        .ascii "GM 00000000-00"
        dc.w 0
        .ascii "J               "
        dc.l 0, 0x00FFFFFF, 0xE0FF0000, 0xE0FFFFFF
        .ascii "            "
        .ascii "            "
        .ascii "                                        "
        .ascii "JUE             "

        .org 0x200
_start:
        move.w #0x2700,%sr
        move.b 0xA10001,%d0
        andi.b #0x0F,%d0
        beq.s 1f
        move.l #0x53454741,0xA14000
1:      move.l #0xE1000000,%sp
        jsr main
2:      bra.s 2b

stub2: move.l 2097160,-(%sp)
        rts
stub3: move.l 2097164,-(%sp)
        rts
stub4: move.l 2097168,-(%sp)
        rts
stub5: move.l 2097172,-(%sp)
        rts
stub6: move.l 2097176,-(%sp)
        rts
stub7: move.l 2097180,-(%sp)
        rts
stub8: move.l 2097184,-(%sp)
        rts
stub9: move.l 2097188,-(%sp)
        rts
stub10: move.l 2097192,-(%sp)
        rts
stub11: move.l 2097196,-(%sp)
        rts
stub12: move.l 2097200,-(%sp)
        rts
stub13: move.l 2097204,-(%sp)
        rts
stub14: move.l 2097208,-(%sp)
        rts
stub15: move.l 2097212,-(%sp)
        rts
stub16: move.l 2097216,-(%sp)
        rts
stub17: move.l 2097220,-(%sp)
        rts
stub18: move.l 2097224,-(%sp)
        rts
stub19: move.l 2097228,-(%sp)
        rts
stub20: move.l 2097232,-(%sp)
        rts
stub21: move.l 2097236,-(%sp)
        rts
stub22: move.l 2097240,-(%sp)
        rts
stub23: move.l 2097244,-(%sp)
        rts
stub24: move.l 2097248,-(%sp)
        rts
stub25: move.l 2097252,-(%sp)
        rts
stub26: move.l 2097256,-(%sp)
        rts
stub27: move.l 2097260,-(%sp)
        rts
stub28: move.l 2097264,-(%sp)
        rts
stub29: move.l 2097268,-(%sp)
        rts
stub30: move.l 2097272,-(%sp)
        rts
stub31: move.l 2097276,-(%sp)
        rts
stub32: move.l 2097280,-(%sp)
        rts
stub33: move.l 2097284,-(%sp)
        rts
stub34: move.l 2097288,-(%sp)
        rts
stub35: move.l 2097292,-(%sp)
        rts
stub36: move.l 2097296,-(%sp)
        rts
stub37: move.l 2097300,-(%sp)
        rts
stub38: move.l 2097304,-(%sp)
        rts
stub39: move.l 2097308,-(%sp)
        rts
stub40: move.l 2097312,-(%sp)
        rts
stub41: move.l 2097316,-(%sp)
        rts
stub42: move.l 2097320,-(%sp)
        rts
stub43: move.l 2097324,-(%sp)
        rts
stub44: move.l 2097328,-(%sp)
        rts
stub45: move.l 2097332,-(%sp)
        rts
stub46: move.l 2097336,-(%sp)
        rts
stub47: move.l 2097340,-(%sp)
        rts
stub48: move.l 2097344,-(%sp)
        rts
stub49: move.l 2097348,-(%sp)
        rts
stub50: move.l 2097352,-(%sp)
        rts
stub51: move.l 2097356,-(%sp)
        rts
stub52: move.l 2097360,-(%sp)
        rts
stub53: move.l 2097364,-(%sp)
        rts
stub54: move.l 2097368,-(%sp)
        rts
stub55: move.l 2097372,-(%sp)
        rts
stub56: move.l 2097376,-(%sp)
        rts
stub57: move.l 2097380,-(%sp)
        rts
stub58: move.l 2097384,-(%sp)
        rts
stub59: move.l 2097388,-(%sp)
        rts
stub60: move.l 2097392,-(%sp)
        rts
stub61: move.l 2097396,-(%sp)
        rts
stub62: move.l 2097400,-(%sp)
        rts
stub63: move.l 2097404,-(%sp)
        rts
