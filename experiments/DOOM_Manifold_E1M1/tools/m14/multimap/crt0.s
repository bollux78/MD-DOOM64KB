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

stub2: move.l 3145736,-(%sp)
        rts
stub3: move.l 3145740,-(%sp)
        rts
stub4: move.l 3145744,-(%sp)
        rts
stub5: move.l 3145748,-(%sp)
        rts
stub6: move.l 3145752,-(%sp)
        rts
stub7: move.l 3145756,-(%sp)
        rts
stub8: move.l 3145760,-(%sp)
        rts
stub9: move.l 3145764,-(%sp)
        rts
stub10: move.l 3145768,-(%sp)
        rts
stub11: move.l 3145772,-(%sp)
        rts
stub12: move.l 3145776,-(%sp)
        rts
stub13: move.l 3145780,-(%sp)
        rts
stub14: move.l 3145784,-(%sp)
        rts
stub15: move.l 3145788,-(%sp)
        rts
stub16: move.l 3145792,-(%sp)
        rts
stub17: move.l 3145796,-(%sp)
        rts
stub18: move.l 3145800,-(%sp)
        rts
stub19: move.l 3145804,-(%sp)
        rts
stub20: move.l 3145808,-(%sp)
        rts
stub21: move.l 3145812,-(%sp)
        rts
stub22: move.l 3145816,-(%sp)
        rts
stub23: move.l 3145820,-(%sp)
        rts
stub24: move.l 3145824,-(%sp)
        rts
stub25: move.l 3145828,-(%sp)
        rts
stub26: move.l 3145832,-(%sp)
        rts
stub27: move.l 3145836,-(%sp)
        rts
stub28: move.l 3145840,-(%sp)
        rts
stub29: move.l 3145844,-(%sp)
        rts
stub30: move.l 3145848,-(%sp)
        rts
stub31: move.l 3145852,-(%sp)
        rts
stub32: move.l 3145856,-(%sp)
        rts
stub33: move.l 3145860,-(%sp)
        rts
stub34: move.l 3145864,-(%sp)
        rts
stub35: move.l 3145868,-(%sp)
        rts
stub36: move.l 3145872,-(%sp)
        rts
stub37: move.l 3145876,-(%sp)
        rts
stub38: move.l 3145880,-(%sp)
        rts
stub39: move.l 3145884,-(%sp)
        rts
stub40: move.l 3145888,-(%sp)
        rts
stub41: move.l 3145892,-(%sp)
        rts
stub42: move.l 3145896,-(%sp)
        rts
stub43: move.l 3145900,-(%sp)
        rts
stub44: move.l 3145904,-(%sp)
        rts
stub45: move.l 3145908,-(%sp)
        rts
stub46: move.l 3145912,-(%sp)
        rts
stub47: move.l 3145916,-(%sp)
        rts
stub48: move.l 3145920,-(%sp)
        rts
stub49: move.l 3145924,-(%sp)
        rts
stub50: move.l 3145928,-(%sp)
        rts
stub51: move.l 3145932,-(%sp)
        rts
stub52: move.l 3145936,-(%sp)
        rts
stub53: move.l 3145940,-(%sp)
        rts
stub54: move.l 3145944,-(%sp)
        rts
stub55: move.l 3145948,-(%sp)
        rts
stub56: move.l 3145952,-(%sp)
        rts
stub57: move.l 3145956,-(%sp)
        rts
stub58: move.l 3145960,-(%sp)
        rts
stub59: move.l 3145964,-(%sp)
        rts
stub60: move.l 3145968,-(%sp)
        rts
stub61: move.l 3145972,-(%sp)
        rts
stub62: move.l 3145976,-(%sp)
        rts
stub63: move.l 3145980,-(%sp)
        rts
