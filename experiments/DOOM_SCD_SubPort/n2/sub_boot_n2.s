/* N2 sub boot: 256 vectors; any exception reports through the sub I_Error channel: message
 * address in $FF802A/2C ("SUB EXCEPTION"), vector number in $FF8028, faulting PC high word in
 * $FF8026, 0xDEAD in $FF8020. */
    .section .text.vectors,"ax"
    .globl subcpu_vectors
subcpu_vectors:
    .long 0x00080000, entry
    .long vex2
    .long vex3
    .long vex4
    .long vex5
    .long vex6
    .long vex7
    .long vex8
    .long vex9
    .long vex10
    .long vex11
    .long vex12
    .long vex13
    .long vex14
    .long vex15
    .long vex16
    .long vex17
    .long vex18
    .long vex19
    .long vex20
    .long vex21
    .long vex22
    .long vex23
    .long vex24
    .long vex25
    .long vex26
    .long vex27
    .long vex28
    .long vex29
    .long vex30
    .long vex31
    .long vex32
    .long vex33
    .long vex34
    .long vex35
    .long vex36
    .long vex37
    .long vex38
    .long vex39
    .long vex40
    .long vex41
    .long vex42
    .long vex43
    .long vex44
    .long vex45
    .long vex46
    .long vex47
    .long vex48
    .long vex49
    .long vex50
    .long vex51
    .long vex52
    .long vex53
    .long vex54
    .long vex55
    .long vex56
    .long vex57
    .long vex58
    .long vex59
    .long vex60
    .long vex61
    .long vex62
    .long vex63
    .long vex64
    .long vex65
    .long vex66
    .long vex67
    .long vex68
    .long vex69
    .long vex70
    .long vex71
    .long vex72
    .long vex73
    .long vex74
    .long vex75
    .long vex76
    .long vex77
    .long vex78
    .long vex79
    .long vex80
    .long vex81
    .long vex82
    .long vex83
    .long vex84
    .long vex85
    .long vex86
    .long vex87
    .long vex88
    .long vex89
    .long vex90
    .long vex91
    .long vex92
    .long vex93
    .long vex94
    .long vex95
    .long vex96
    .long vex97
    .long vex98
    .long vex99
    .long vex100
    .long vex101
    .long vex102
    .long vex103
    .long vex104
    .long vex105
    .long vex106
    .long vex107
    .long vex108
    .long vex109
    .long vex110
    .long vex111
    .long vex112
    .long vex113
    .long vex114
    .long vex115
    .long vex116
    .long vex117
    .long vex118
    .long vex119
    .long vex120
    .long vex121
    .long vex122
    .long vex123
    .long vex124
    .long vex125
    .long vex126
    .long vex127
    .long vex128
    .long vex129
    .long vex130
    .long vex131
    .long vex132
    .long vex133
    .long vex134
    .long vex135
    .long vex136
    .long vex137
    .long vex138
    .long vex139
    .long vex140
    .long vex141
    .long vex142
    .long vex143
    .long vex144
    .long vex145
    .long vex146
    .long vex147
    .long vex148
    .long vex149
    .long vex150
    .long vex151
    .long vex152
    .long vex153
    .long vex154
    .long vex155
    .long vex156
    .long vex157
    .long vex158
    .long vex159
    .long vex160
    .long vex161
    .long vex162
    .long vex163
    .long vex164
    .long vex165
    .long vex166
    .long vex167
    .long vex168
    .long vex169
    .long vex170
    .long vex171
    .long vex172
    .long vex173
    .long vex174
    .long vex175
    .long vex176
    .long vex177
    .long vex178
    .long vex179
    .long vex180
    .long vex181
    .long vex182
    .long vex183
    .long vex184
    .long vex185
    .long vex186
    .long vex187
    .long vex188
    .long vex189
    .long vex190
    .long vex191
    .long vex192
    .long vex193
    .long vex194
    .long vex195
    .long vex196
    .long vex197
    .long vex198
    .long vex199
    .long vex200
    .long vex201
    .long vex202
    .long vex203
    .long vex204
    .long vex205
    .long vex206
    .long vex207
    .long vex208
    .long vex209
    .long vex210
    .long vex211
    .long vex212
    .long vex213
    .long vex214
    .long vex215
    .long vex216
    .long vex217
    .long vex218
    .long vex219
    .long vex220
    .long vex221
    .long vex222
    .long vex223
    .long vex224
    .long vex225
    .long vex226
    .long vex227
    .long vex228
    .long vex229
    .long vex230
    .long vex231
    .long vex232
    .long vex233
    .long vex234
    .long vex235
    .long vex236
    .long vex237
    .long vex238
    .long vex239
    .long vex240
    .long vex241
    .long vex242
    .long vex243
    .long vex244
    .long vex245
    .long vex246
    .long vex247
    .long vex248
    .long vex249
    .long vex250
    .long vex251
    .long vex252
    .long vex253
    .long vex254
    .long vex255
entry:
    move.w #0x2700,%sr
    lea __bss_start,%a0
    lea _end,%a1
1:  cmp.l %a1,%a0
    bcc.s 2f
    clr.b (%a0)+
    bra.s 1b
2:  jsr sub_main
3:  bra.s 3b
vex2: move.w #2,%d0
    bra.w vexc
vex3: move.w #3,%d0
    bra.w vexc
vex4: move.w #4,%d0
    bra.w vexc
vex5: move.w #5,%d0
    bra.w vexc
vex6: move.w #6,%d0
    bra.w vexc
vex7: move.w #7,%d0
    bra.w vexc
vex8: move.w #8,%d0
    bra.w vexc
vex9: move.w #9,%d0
    bra.w vexc
vex10: move.w #10,%d0
    bra.w vexc
vex11: move.w #11,%d0
    bra.w vexc
vex12: move.w #12,%d0
    bra.w vexc
vex13: move.w #13,%d0
    bra.w vexc
vex14: move.w #14,%d0
    bra.w vexc
vex15: move.w #15,%d0
    bra.w vexc
vex16: move.w #16,%d0
    bra.w vexc
vex17: move.w #17,%d0
    bra.w vexc
vex18: move.w #18,%d0
    bra.w vexc
vex19: move.w #19,%d0
    bra.w vexc
vex20: move.w #20,%d0
    bra.w vexc
vex21: move.w #21,%d0
    bra.w vexc
vex22: move.w #22,%d0
    bra.w vexc
vex23: move.w #23,%d0
    bra.w vexc
vex24: move.w #24,%d0
    bra.w vexc
vex25: move.w #25,%d0
    bra.w vexc
vex26: move.w #26,%d0
    bra.w vexc
vex27: move.w #27,%d0
    bra.w vexc
vex28: move.w #28,%d0
    bra.w vexc
vex29: move.w #29,%d0
    bra.w vexc
vex30: move.w #30,%d0
    bra.w vexc
vex31: move.w #31,%d0
    bra.w vexc
vex32: move.w #32,%d0
    bra.w vexc
vex33: move.w #33,%d0
    bra.w vexc
vex34: move.w #34,%d0
    bra.w vexc
vex35: move.w #35,%d0
    bra.w vexc
vex36: move.w #36,%d0
    bra.w vexc
vex37: move.w #37,%d0
    bra.w vexc
vex38: move.w #38,%d0
    bra.w vexc
vex39: move.w #39,%d0
    bra.w vexc
vex40: move.w #40,%d0
    bra.w vexc
vex41: move.w #41,%d0
    bra.w vexc
vex42: move.w #42,%d0
    bra.w vexc
vex43: move.w #43,%d0
    bra.w vexc
vex44: move.w #44,%d0
    bra.w vexc
vex45: move.w #45,%d0
    bra.w vexc
vex46: move.w #46,%d0
    bra.w vexc
vex47: move.w #47,%d0
    bra.w vexc
vex48: move.w #48,%d0
    bra.w vexc
vex49: move.w #49,%d0
    bra.w vexc
vex50: move.w #50,%d0
    bra.w vexc
vex51: move.w #51,%d0
    bra.w vexc
vex52: move.w #52,%d0
    bra.w vexc
vex53: move.w #53,%d0
    bra.w vexc
vex54: move.w #54,%d0
    bra.w vexc
vex55: move.w #55,%d0
    bra.w vexc
vex56: move.w #56,%d0
    bra.w vexc
vex57: move.w #57,%d0
    bra.w vexc
vex58: move.w #58,%d0
    bra.w vexc
vex59: move.w #59,%d0
    bra.w vexc
vex60: move.w #60,%d0
    bra.w vexc
vex61: move.w #61,%d0
    bra.w vexc
vex62: move.w #62,%d0
    bra.w vexc
vex63: move.w #63,%d0
    bra.w vexc
vex64: move.w #64,%d0
    bra.w vexc
vex65: move.w #65,%d0
    bra.w vexc
vex66: move.w #66,%d0
    bra.w vexc
vex67: move.w #67,%d0
    bra.w vexc
vex68: move.w #68,%d0
    bra.w vexc
vex69: move.w #69,%d0
    bra.w vexc
vex70: move.w #70,%d0
    bra.w vexc
vex71: move.w #71,%d0
    bra.w vexc
vex72: move.w #72,%d0
    bra.w vexc
vex73: move.w #73,%d0
    bra.w vexc
vex74: move.w #74,%d0
    bra.w vexc
vex75: move.w #75,%d0
    bra.w vexc
vex76: move.w #76,%d0
    bra.w vexc
vex77: move.w #77,%d0
    bra.w vexc
vex78: move.w #78,%d0
    bra.w vexc
vex79: move.w #79,%d0
    bra.w vexc
vex80: move.w #80,%d0
    bra.w vexc
vex81: move.w #81,%d0
    bra.w vexc
vex82: move.w #82,%d0
    bra.w vexc
vex83: move.w #83,%d0
    bra.w vexc
vex84: move.w #84,%d0
    bra.w vexc
vex85: move.w #85,%d0
    bra.w vexc
vex86: move.w #86,%d0
    bra.w vexc
vex87: move.w #87,%d0
    bra.w vexc
vex88: move.w #88,%d0
    bra.w vexc
vex89: move.w #89,%d0
    bra.w vexc
vex90: move.w #90,%d0
    bra.w vexc
vex91: move.w #91,%d0
    bra.w vexc
vex92: move.w #92,%d0
    bra.w vexc
vex93: move.w #93,%d0
    bra.w vexc
vex94: move.w #94,%d0
    bra.w vexc
vex95: move.w #95,%d0
    bra.w vexc
vex96: move.w #96,%d0
    bra.w vexc
vex97: move.w #97,%d0
    bra.w vexc
vex98: move.w #98,%d0
    bra.w vexc
vex99: move.w #99,%d0
    bra.w vexc
vex100: move.w #100,%d0
    bra.w vexc
vex101: move.w #101,%d0
    bra.w vexc
vex102: move.w #102,%d0
    bra.w vexc
vex103: move.w #103,%d0
    bra.w vexc
vex104: move.w #104,%d0
    bra.w vexc
vex105: move.w #105,%d0
    bra.w vexc
vex106: move.w #106,%d0
    bra.w vexc
vex107: move.w #107,%d0
    bra.w vexc
vex108: move.w #108,%d0
    bra.w vexc
vex109: move.w #109,%d0
    bra.w vexc
vex110: move.w #110,%d0
    bra.w vexc
vex111: move.w #111,%d0
    bra.w vexc
vex112: move.w #112,%d0
    bra.w vexc
vex113: move.w #113,%d0
    bra.w vexc
vex114: move.w #114,%d0
    bra.w vexc
vex115: move.w #115,%d0
    bra.w vexc
vex116: move.w #116,%d0
    bra.w vexc
vex117: move.w #117,%d0
    bra.w vexc
vex118: move.w #118,%d0
    bra.w vexc
vex119: move.w #119,%d0
    bra.w vexc
vex120: move.w #120,%d0
    bra.w vexc
vex121: move.w #121,%d0
    bra.w vexc
vex122: move.w #122,%d0
    bra.w vexc
vex123: move.w #123,%d0
    bra.w vexc
vex124: move.w #124,%d0
    bra.w vexc
vex125: move.w #125,%d0
    bra.w vexc
vex126: move.w #126,%d0
    bra.w vexc
vex127: move.w #127,%d0
    bra.w vexc
vex128: move.w #128,%d0
    bra.w vexc
vex129: move.w #129,%d0
    bra.w vexc
vex130: move.w #130,%d0
    bra.w vexc
vex131: move.w #131,%d0
    bra.w vexc
vex132: move.w #132,%d0
    bra.w vexc
vex133: move.w #133,%d0
    bra.w vexc
vex134: move.w #134,%d0
    bra.w vexc
vex135: move.w #135,%d0
    bra.w vexc
vex136: move.w #136,%d0
    bra.w vexc
vex137: move.w #137,%d0
    bra.w vexc
vex138: move.w #138,%d0
    bra.w vexc
vex139: move.w #139,%d0
    bra.w vexc
vex140: move.w #140,%d0
    bra.w vexc
vex141: move.w #141,%d0
    bra.w vexc
vex142: move.w #142,%d0
    bra.w vexc
vex143: move.w #143,%d0
    bra.w vexc
vex144: move.w #144,%d0
    bra.w vexc
vex145: move.w #145,%d0
    bra.w vexc
vex146: move.w #146,%d0
    bra.w vexc
vex147: move.w #147,%d0
    bra.w vexc
vex148: move.w #148,%d0
    bra.w vexc
vex149: move.w #149,%d0
    bra.w vexc
vex150: move.w #150,%d0
    bra.w vexc
vex151: move.w #151,%d0
    bra.w vexc
vex152: move.w #152,%d0
    bra.w vexc
vex153: move.w #153,%d0
    bra.w vexc
vex154: move.w #154,%d0
    bra.w vexc
vex155: move.w #155,%d0
    bra.w vexc
vex156: move.w #156,%d0
    bra.w vexc
vex157: move.w #157,%d0
    bra.w vexc
vex158: move.w #158,%d0
    bra.w vexc
vex159: move.w #159,%d0
    bra.w vexc
vex160: move.w #160,%d0
    bra.w vexc
vex161: move.w #161,%d0
    bra.w vexc
vex162: move.w #162,%d0
    bra.w vexc
vex163: move.w #163,%d0
    bra.w vexc
vex164: move.w #164,%d0
    bra.w vexc
vex165: move.w #165,%d0
    bra.w vexc
vex166: move.w #166,%d0
    bra.w vexc
vex167: move.w #167,%d0
    bra.w vexc
vex168: move.w #168,%d0
    bra.w vexc
vex169: move.w #169,%d0
    bra.w vexc
vex170: move.w #170,%d0
    bra.w vexc
vex171: move.w #171,%d0
    bra.w vexc
vex172: move.w #172,%d0
    bra.w vexc
vex173: move.w #173,%d0
    bra.w vexc
vex174: move.w #174,%d0
    bra.w vexc
vex175: move.w #175,%d0
    bra.w vexc
vex176: move.w #176,%d0
    bra.w vexc
vex177: move.w #177,%d0
    bra.w vexc
vex178: move.w #178,%d0
    bra.w vexc
vex179: move.w #179,%d0
    bra.w vexc
vex180: move.w #180,%d0
    bra.w vexc
vex181: move.w #181,%d0
    bra.w vexc
vex182: move.w #182,%d0
    bra.w vexc
vex183: move.w #183,%d0
    bra.w vexc
vex184: move.w #184,%d0
    bra.w vexc
vex185: move.w #185,%d0
    bra.w vexc
vex186: move.w #186,%d0
    bra.w vexc
vex187: move.w #187,%d0
    bra.w vexc
vex188: move.w #188,%d0
    bra.w vexc
vex189: move.w #189,%d0
    bra.w vexc
vex190: move.w #190,%d0
    bra.w vexc
vex191: move.w #191,%d0
    bra.w vexc
vex192: move.w #192,%d0
    bra.w vexc
vex193: move.w #193,%d0
    bra.w vexc
vex194: move.w #194,%d0
    bra.w vexc
vex195: move.w #195,%d0
    bra.w vexc
vex196: move.w #196,%d0
    bra.w vexc
vex197: move.w #197,%d0
    bra.w vexc
vex198: move.w #198,%d0
    bra.w vexc
vex199: move.w #199,%d0
    bra.w vexc
vex200: move.w #200,%d0
    bra.w vexc
vex201: move.w #201,%d0
    bra.w vexc
vex202: move.w #202,%d0
    bra.w vexc
vex203: move.w #203,%d0
    bra.w vexc
vex204: move.w #204,%d0
    bra.w vexc
vex205: move.w #205,%d0
    bra.w vexc
vex206: move.w #206,%d0
    bra.w vexc
vex207: move.w #207,%d0
    bra.w vexc
vex208: move.w #208,%d0
    bra.w vexc
vex209: move.w #209,%d0
    bra.w vexc
vex210: move.w #210,%d0
    bra.w vexc
vex211: move.w #211,%d0
    bra.w vexc
vex212: move.w #212,%d0
    bra.w vexc
vex213: move.w #213,%d0
    bra.w vexc
vex214: move.w #214,%d0
    bra.w vexc
vex215: move.w #215,%d0
    bra.w vexc
vex216: move.w #216,%d0
    bra.w vexc
vex217: move.w #217,%d0
    bra.w vexc
vex218: move.w #218,%d0
    bra.w vexc
vex219: move.w #219,%d0
    bra.w vexc
vex220: move.w #220,%d0
    bra.w vexc
vex221: move.w #221,%d0
    bra.w vexc
vex222: move.w #222,%d0
    bra.w vexc
vex223: move.w #223,%d0
    bra.w vexc
vex224: move.w #224,%d0
    bra.w vexc
vex225: move.w #225,%d0
    bra.w vexc
vex226: move.w #226,%d0
    bra.w vexc
vex227: move.w #227,%d0
    bra.w vexc
vex228: move.w #228,%d0
    bra.w vexc
vex229: move.w #229,%d0
    bra.w vexc
vex230: move.w #230,%d0
    bra.w vexc
vex231: move.w #231,%d0
    bra.w vexc
vex232: move.w #232,%d0
    bra.w vexc
vex233: move.w #233,%d0
    bra.w vexc
vex234: move.w #234,%d0
    bra.w vexc
vex235: move.w #235,%d0
    bra.w vexc
vex236: move.w #236,%d0
    bra.w vexc
vex237: move.w #237,%d0
    bra.w vexc
vex238: move.w #238,%d0
    bra.w vexc
vex239: move.w #239,%d0
    bra.w vexc
vex240: move.w #240,%d0
    bra.w vexc
vex241: move.w #241,%d0
    bra.w vexc
vex242: move.w #242,%d0
    bra.w vexc
vex243: move.w #243,%d0
    bra.w vexc
vex244: move.w #244,%d0
    bra.w vexc
vex245: move.w #245,%d0
    bra.w vexc
vex246: move.w #246,%d0
    bra.w vexc
vex247: move.w #247,%d0
    bra.w vexc
vex248: move.w #248,%d0
    bra.w vexc
vex249: move.w #249,%d0
    bra.w vexc
vex250: move.w #250,%d0
    bra.w vexc
vex251: move.w #251,%d0
    bra.w vexc
vex252: move.w #252,%d0
    bra.w vexc
vex253: move.w #253,%d0
    bra.w vexc
vex254: move.w #254,%d0
    bra.w vexc
vex255: move.w #255,%d0
    bra.w vexc
vexc:
    move.w #0x2700,%sr
    move.w 2(%sp),0xff8026
    move.w %d0,0xff8028
    move.l #vmsg,%d0
    move.w %d0,0xff802c
    swap %d0
    move.w %d0,0xff802a
    move.w #0xdead,0xff8020
4:  bra.s 4b
vmsg: .asciz "SUB EXCEPTION"
    .even
