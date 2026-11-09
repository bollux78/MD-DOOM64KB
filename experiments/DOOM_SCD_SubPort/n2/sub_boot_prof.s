/* N2 sub vectors with a timer PC-sampling profiler. Every interrupt-capable vector (24..255)
 * counts its hits in scd_vec_hits[] and then samples the PC; bins of 64 bytes over 256 KiB. */
    .section .text.vectors,"ax"
    .globl subcpu_vectors
    .weak scd_prof_bins
    .weak scd_vec_hits
    .globl prof_isr
subcpu_vectors:
    .long 0x00080000, entry
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long fault
    .long vstub24
    .long vstub25
    .long vstub26
    .long vstub27
    .long vstub28
    .long vstub29
    .long vstub30
    .long vstub31
    .long vstub32
    .long vstub33
    .long vstub34
    .long vstub35
    .long vstub36
    .long vstub37
    .long vstub38
    .long vstub39
    .long vstub40
    .long vstub41
    .long vstub42
    .long vstub43
    .long vstub44
    .long vstub45
    .long vstub46
    .long vstub47
    .long vstub48
    .long vstub49
    .long vstub50
    .long vstub51
    .long vstub52
    .long vstub53
    .long vstub54
    .long vstub55
    .long vstub56
    .long vstub57
    .long vstub58
    .long vstub59
    .long vstub60
    .long vstub61
    .long vstub62
    .long vstub63
    .long vstub64
    .long vstub65
    .long vstub66
    .long vstub67
    .long vstub68
    .long vstub69
    .long vstub70
    .long vstub71
    .long vstub72
    .long vstub73
    .long vstub74
    .long vstub75
    .long vstub76
    .long vstub77
    .long vstub78
    .long vstub79
    .long vstub80
    .long vstub81
    .long vstub82
    .long vstub83
    .long vstub84
    .long vstub85
    .long vstub86
    .long vstub87
    .long vstub88
    .long vstub89
    .long vstub90
    .long vstub91
    .long vstub92
    .long vstub93
    .long vstub94
    .long vstub95
    .long vstub96
    .long vstub97
    .long vstub98
    .long vstub99
    .long vstub100
    .long vstub101
    .long vstub102
    .long vstub103
    .long vstub104
    .long vstub105
    .long vstub106
    .long vstub107
    .long vstub108
    .long vstub109
    .long vstub110
    .long vstub111
    .long vstub112
    .long vstub113
    .long vstub114
    .long vstub115
    .long vstub116
    .long vstub117
    .long vstub118
    .long vstub119
    .long vstub120
    .long vstub121
    .long vstub122
    .long vstub123
    .long vstub124
    .long vstub125
    .long vstub126
    .long vstub127
    .long vstub128
    .long vstub129
    .long vstub130
    .long vstub131
    .long vstub132
    .long vstub133
    .long vstub134
    .long vstub135
    .long vstub136
    .long vstub137
    .long vstub138
    .long vstub139
    .long vstub140
    .long vstub141
    .long vstub142
    .long vstub143
    .long vstub144
    .long vstub145
    .long vstub146
    .long vstub147
    .long vstub148
    .long vstub149
    .long vstub150
    .long vstub151
    .long vstub152
    .long vstub153
    .long vstub154
    .long vstub155
    .long vstub156
    .long vstub157
    .long vstub158
    .long vstub159
    .long vstub160
    .long vstub161
    .long vstub162
    .long vstub163
    .long vstub164
    .long vstub165
    .long vstub166
    .long vstub167
    .long vstub168
    .long vstub169
    .long vstub170
    .long vstub171
    .long vstub172
    .long vstub173
    .long vstub174
    .long vstub175
    .long vstub176
    .long vstub177
    .long vstub178
    .long vstub179
    .long vstub180
    .long vstub181
    .long vstub182
    .long vstub183
    .long vstub184
    .long vstub185
    .long vstub186
    .long vstub187
    .long vstub188
    .long vstub189
    .long vstub190
    .long vstub191
    .long vstub192
    .long vstub193
    .long vstub194
    .long vstub195
    .long vstub196
    .long vstub197
    .long vstub198
    .long vstub199
    .long vstub200
    .long vstub201
    .long vstub202
    .long vstub203
    .long vstub204
    .long vstub205
    .long vstub206
    .long vstub207
    .long vstub208
    .long vstub209
    .long vstub210
    .long vstub211
    .long vstub212
    .long vstub213
    .long vstub214
    .long vstub215
    .long vstub216
    .long vstub217
    .long vstub218
    .long vstub219
    .long vstub220
    .long vstub221
    .long vstub222
    .long vstub223
    .long vstub224
    .long vstub225
    .long vstub226
    .long vstub227
    .long vstub228
    .long vstub229
    .long vstub230
    .long vstub231
    .long vstub232
    .long vstub233
    .long vstub234
    .long vstub235
    .long vstub236
    .long vstub237
    .long vstub238
    .long vstub239
    .long vstub240
    .long vstub241
    .long vstub242
    .long vstub243
    .long vstub244
    .long vstub245
    .long vstub246
    .long vstub247
    .long vstub248
    .long vstub249
    .long vstub250
    .long vstub251
    .long vstub252
    .long vstub253
    .long vstub254
    .long vstub255
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
vstub24:
    addq.w #1,scd_vec_hits+48
    bra.w prof_isr
vstub25:
    addq.w #1,scd_vec_hits+50
    bra.w prof_isr
vstub26:
    addq.w #1,scd_vec_hits+52
    bra.w prof_isr
vstub27:
    addq.w #1,scd_vec_hits+54
    bra.w prof_isr
vstub28:
    addq.w #1,scd_vec_hits+56
    bra.w prof_isr
vstub29:
    addq.w #1,scd_vec_hits+58
    bra.w prof_isr
vstub30:
    addq.w #1,scd_vec_hits+60
    bra.w prof_isr
vstub31:
    addq.w #1,scd_vec_hits+62
    bra.w prof_isr
vstub32:
    addq.w #1,scd_vec_hits+64
    bra.w prof_isr
vstub33:
    addq.w #1,scd_vec_hits+66
    bra.w prof_isr
vstub34:
    addq.w #1,scd_vec_hits+68
    bra.w prof_isr
vstub35:
    addq.w #1,scd_vec_hits+70
    bra.w prof_isr
vstub36:
    addq.w #1,scd_vec_hits+72
    bra.w prof_isr
vstub37:
    addq.w #1,scd_vec_hits+74
    bra.w prof_isr
vstub38:
    addq.w #1,scd_vec_hits+76
    bra.w prof_isr
vstub39:
    addq.w #1,scd_vec_hits+78
    bra.w prof_isr
vstub40:
    addq.w #1,scd_vec_hits+80
    bra.w prof_isr
vstub41:
    addq.w #1,scd_vec_hits+82
    bra.w prof_isr
vstub42:
    addq.w #1,scd_vec_hits+84
    bra.w prof_isr
vstub43:
    addq.w #1,scd_vec_hits+86
    bra.w prof_isr
vstub44:
    addq.w #1,scd_vec_hits+88
    bra.w prof_isr
vstub45:
    addq.w #1,scd_vec_hits+90
    bra.w prof_isr
vstub46:
    addq.w #1,scd_vec_hits+92
    bra.w prof_isr
vstub47:
    addq.w #1,scd_vec_hits+94
    bra.w prof_isr
vstub48:
    addq.w #1,scd_vec_hits+96
    bra.w prof_isr
vstub49:
    addq.w #1,scd_vec_hits+98
    bra.w prof_isr
vstub50:
    addq.w #1,scd_vec_hits+100
    bra.w prof_isr
vstub51:
    addq.w #1,scd_vec_hits+102
    bra.w prof_isr
vstub52:
    addq.w #1,scd_vec_hits+104
    bra.w prof_isr
vstub53:
    addq.w #1,scd_vec_hits+106
    bra.w prof_isr
vstub54:
    addq.w #1,scd_vec_hits+108
    bra.w prof_isr
vstub55:
    addq.w #1,scd_vec_hits+110
    bra.w prof_isr
vstub56:
    addq.w #1,scd_vec_hits+112
    bra.w prof_isr
vstub57:
    addq.w #1,scd_vec_hits+114
    bra.w prof_isr
vstub58:
    addq.w #1,scd_vec_hits+116
    bra.w prof_isr
vstub59:
    addq.w #1,scd_vec_hits+118
    bra.w prof_isr
vstub60:
    addq.w #1,scd_vec_hits+120
    bra.w prof_isr
vstub61:
    addq.w #1,scd_vec_hits+122
    bra.w prof_isr
vstub62:
    addq.w #1,scd_vec_hits+124
    bra.w prof_isr
vstub63:
    addq.w #1,scd_vec_hits+126
    bra.w prof_isr
vstub64:
    addq.w #1,scd_vec_hits+128
    bra.w prof_isr
vstub65:
    addq.w #1,scd_vec_hits+130
    bra.w prof_isr
vstub66:
    addq.w #1,scd_vec_hits+132
    bra.w prof_isr
vstub67:
    addq.w #1,scd_vec_hits+134
    bra.w prof_isr
vstub68:
    addq.w #1,scd_vec_hits+136
    bra.w prof_isr
vstub69:
    addq.w #1,scd_vec_hits+138
    bra.w prof_isr
vstub70:
    addq.w #1,scd_vec_hits+140
    bra.w prof_isr
vstub71:
    addq.w #1,scd_vec_hits+142
    bra.w prof_isr
vstub72:
    addq.w #1,scd_vec_hits+144
    bra.w prof_isr
vstub73:
    addq.w #1,scd_vec_hits+146
    bra.w prof_isr
vstub74:
    addq.w #1,scd_vec_hits+148
    bra.w prof_isr
vstub75:
    addq.w #1,scd_vec_hits+150
    bra.w prof_isr
vstub76:
    addq.w #1,scd_vec_hits+152
    bra.w prof_isr
vstub77:
    addq.w #1,scd_vec_hits+154
    bra.w prof_isr
vstub78:
    addq.w #1,scd_vec_hits+156
    bra.w prof_isr
vstub79:
    addq.w #1,scd_vec_hits+158
    bra.w prof_isr
vstub80:
    addq.w #1,scd_vec_hits+160
    bra.w prof_isr
vstub81:
    addq.w #1,scd_vec_hits+162
    bra.w prof_isr
vstub82:
    addq.w #1,scd_vec_hits+164
    bra.w prof_isr
vstub83:
    addq.w #1,scd_vec_hits+166
    bra.w prof_isr
vstub84:
    addq.w #1,scd_vec_hits+168
    bra.w prof_isr
vstub85:
    addq.w #1,scd_vec_hits+170
    bra.w prof_isr
vstub86:
    addq.w #1,scd_vec_hits+172
    bra.w prof_isr
vstub87:
    addq.w #1,scd_vec_hits+174
    bra.w prof_isr
vstub88:
    addq.w #1,scd_vec_hits+176
    bra.w prof_isr
vstub89:
    addq.w #1,scd_vec_hits+178
    bra.w prof_isr
vstub90:
    addq.w #1,scd_vec_hits+180
    bra.w prof_isr
vstub91:
    addq.w #1,scd_vec_hits+182
    bra.w prof_isr
vstub92:
    addq.w #1,scd_vec_hits+184
    bra.w prof_isr
vstub93:
    addq.w #1,scd_vec_hits+186
    bra.w prof_isr
vstub94:
    addq.w #1,scd_vec_hits+188
    bra.w prof_isr
vstub95:
    addq.w #1,scd_vec_hits+190
    bra.w prof_isr
vstub96:
    addq.w #1,scd_vec_hits+192
    bra.w prof_isr
vstub97:
    addq.w #1,scd_vec_hits+194
    bra.w prof_isr
vstub98:
    addq.w #1,scd_vec_hits+196
    bra.w prof_isr
vstub99:
    addq.w #1,scd_vec_hits+198
    bra.w prof_isr
vstub100:
    addq.w #1,scd_vec_hits+200
    bra.w prof_isr
vstub101:
    addq.w #1,scd_vec_hits+202
    bra.w prof_isr
vstub102:
    addq.w #1,scd_vec_hits+204
    bra.w prof_isr
vstub103:
    addq.w #1,scd_vec_hits+206
    bra.w prof_isr
vstub104:
    addq.w #1,scd_vec_hits+208
    bra.w prof_isr
vstub105:
    addq.w #1,scd_vec_hits+210
    bra.w prof_isr
vstub106:
    addq.w #1,scd_vec_hits+212
    bra.w prof_isr
vstub107:
    addq.w #1,scd_vec_hits+214
    bra.w prof_isr
vstub108:
    addq.w #1,scd_vec_hits+216
    bra.w prof_isr
vstub109:
    addq.w #1,scd_vec_hits+218
    bra.w prof_isr
vstub110:
    addq.w #1,scd_vec_hits+220
    bra.w prof_isr
vstub111:
    addq.w #1,scd_vec_hits+222
    bra.w prof_isr
vstub112:
    addq.w #1,scd_vec_hits+224
    bra.w prof_isr
vstub113:
    addq.w #1,scd_vec_hits+226
    bra.w prof_isr
vstub114:
    addq.w #1,scd_vec_hits+228
    bra.w prof_isr
vstub115:
    addq.w #1,scd_vec_hits+230
    bra.w prof_isr
vstub116:
    addq.w #1,scd_vec_hits+232
    bra.w prof_isr
vstub117:
    addq.w #1,scd_vec_hits+234
    bra.w prof_isr
vstub118:
    addq.w #1,scd_vec_hits+236
    bra.w prof_isr
vstub119:
    addq.w #1,scd_vec_hits+238
    bra.w prof_isr
vstub120:
    addq.w #1,scd_vec_hits+240
    bra.w prof_isr
vstub121:
    addq.w #1,scd_vec_hits+242
    bra.w prof_isr
vstub122:
    addq.w #1,scd_vec_hits+244
    bra.w prof_isr
vstub123:
    addq.w #1,scd_vec_hits+246
    bra.w prof_isr
vstub124:
    addq.w #1,scd_vec_hits+248
    bra.w prof_isr
vstub125:
    addq.w #1,scd_vec_hits+250
    bra.w prof_isr
vstub126:
    addq.w #1,scd_vec_hits+252
    bra.w prof_isr
vstub127:
    addq.w #1,scd_vec_hits+254
    bra.w prof_isr
vstub128:
    addq.w #1,scd_vec_hits+256
    bra.w prof_isr
vstub129:
    addq.w #1,scd_vec_hits+258
    bra.w prof_isr
vstub130:
    addq.w #1,scd_vec_hits+260
    bra.w prof_isr
vstub131:
    addq.w #1,scd_vec_hits+262
    bra.w prof_isr
vstub132:
    addq.w #1,scd_vec_hits+264
    bra.w prof_isr
vstub133:
    addq.w #1,scd_vec_hits+266
    bra.w prof_isr
vstub134:
    addq.w #1,scd_vec_hits+268
    bra.w prof_isr
vstub135:
    addq.w #1,scd_vec_hits+270
    bra.w prof_isr
vstub136:
    addq.w #1,scd_vec_hits+272
    bra.w prof_isr
vstub137:
    addq.w #1,scd_vec_hits+274
    bra.w prof_isr
vstub138:
    addq.w #1,scd_vec_hits+276
    bra.w prof_isr
vstub139:
    addq.w #1,scd_vec_hits+278
    bra.w prof_isr
vstub140:
    addq.w #1,scd_vec_hits+280
    bra.w prof_isr
vstub141:
    addq.w #1,scd_vec_hits+282
    bra.w prof_isr
vstub142:
    addq.w #1,scd_vec_hits+284
    bra.w prof_isr
vstub143:
    addq.w #1,scd_vec_hits+286
    bra.w prof_isr
vstub144:
    addq.w #1,scd_vec_hits+288
    bra.w prof_isr
vstub145:
    addq.w #1,scd_vec_hits+290
    bra.w prof_isr
vstub146:
    addq.w #1,scd_vec_hits+292
    bra.w prof_isr
vstub147:
    addq.w #1,scd_vec_hits+294
    bra.w prof_isr
vstub148:
    addq.w #1,scd_vec_hits+296
    bra.w prof_isr
vstub149:
    addq.w #1,scd_vec_hits+298
    bra.w prof_isr
vstub150:
    addq.w #1,scd_vec_hits+300
    bra.w prof_isr
vstub151:
    addq.w #1,scd_vec_hits+302
    bra.w prof_isr
vstub152:
    addq.w #1,scd_vec_hits+304
    bra.w prof_isr
vstub153:
    addq.w #1,scd_vec_hits+306
    bra.w prof_isr
vstub154:
    addq.w #1,scd_vec_hits+308
    bra.w prof_isr
vstub155:
    addq.w #1,scd_vec_hits+310
    bra.w prof_isr
vstub156:
    addq.w #1,scd_vec_hits+312
    bra.w prof_isr
vstub157:
    addq.w #1,scd_vec_hits+314
    bra.w prof_isr
vstub158:
    addq.w #1,scd_vec_hits+316
    bra.w prof_isr
vstub159:
    addq.w #1,scd_vec_hits+318
    bra.w prof_isr
vstub160:
    addq.w #1,scd_vec_hits+320
    bra.w prof_isr
vstub161:
    addq.w #1,scd_vec_hits+322
    bra.w prof_isr
vstub162:
    addq.w #1,scd_vec_hits+324
    bra.w prof_isr
vstub163:
    addq.w #1,scd_vec_hits+326
    bra.w prof_isr
vstub164:
    addq.w #1,scd_vec_hits+328
    bra.w prof_isr
vstub165:
    addq.w #1,scd_vec_hits+330
    bra.w prof_isr
vstub166:
    addq.w #1,scd_vec_hits+332
    bra.w prof_isr
vstub167:
    addq.w #1,scd_vec_hits+334
    bra.w prof_isr
vstub168:
    addq.w #1,scd_vec_hits+336
    bra.w prof_isr
vstub169:
    addq.w #1,scd_vec_hits+338
    bra.w prof_isr
vstub170:
    addq.w #1,scd_vec_hits+340
    bra.w prof_isr
vstub171:
    addq.w #1,scd_vec_hits+342
    bra.w prof_isr
vstub172:
    addq.w #1,scd_vec_hits+344
    bra.w prof_isr
vstub173:
    addq.w #1,scd_vec_hits+346
    bra.w prof_isr
vstub174:
    addq.w #1,scd_vec_hits+348
    bra.w prof_isr
vstub175:
    addq.w #1,scd_vec_hits+350
    bra.w prof_isr
vstub176:
    addq.w #1,scd_vec_hits+352
    bra.w prof_isr
vstub177:
    addq.w #1,scd_vec_hits+354
    bra.w prof_isr
vstub178:
    addq.w #1,scd_vec_hits+356
    bra.w prof_isr
vstub179:
    addq.w #1,scd_vec_hits+358
    bra.w prof_isr
vstub180:
    addq.w #1,scd_vec_hits+360
    bra.w prof_isr
vstub181:
    addq.w #1,scd_vec_hits+362
    bra.w prof_isr
vstub182:
    addq.w #1,scd_vec_hits+364
    bra.w prof_isr
vstub183:
    addq.w #1,scd_vec_hits+366
    bra.w prof_isr
vstub184:
    addq.w #1,scd_vec_hits+368
    bra.w prof_isr
vstub185:
    addq.w #1,scd_vec_hits+370
    bra.w prof_isr
vstub186:
    addq.w #1,scd_vec_hits+372
    bra.w prof_isr
vstub187:
    addq.w #1,scd_vec_hits+374
    bra.w prof_isr
vstub188:
    addq.w #1,scd_vec_hits+376
    bra.w prof_isr
vstub189:
    addq.w #1,scd_vec_hits+378
    bra.w prof_isr
vstub190:
    addq.w #1,scd_vec_hits+380
    bra.w prof_isr
vstub191:
    addq.w #1,scd_vec_hits+382
    bra.w prof_isr
vstub192:
    addq.w #1,scd_vec_hits+384
    bra.w prof_isr
vstub193:
    addq.w #1,scd_vec_hits+386
    bra.w prof_isr
vstub194:
    addq.w #1,scd_vec_hits+388
    bra.w prof_isr
vstub195:
    addq.w #1,scd_vec_hits+390
    bra.w prof_isr
vstub196:
    addq.w #1,scd_vec_hits+392
    bra.w prof_isr
vstub197:
    addq.w #1,scd_vec_hits+394
    bra.w prof_isr
vstub198:
    addq.w #1,scd_vec_hits+396
    bra.w prof_isr
vstub199:
    addq.w #1,scd_vec_hits+398
    bra.w prof_isr
vstub200:
    addq.w #1,scd_vec_hits+400
    bra.w prof_isr
vstub201:
    addq.w #1,scd_vec_hits+402
    bra.w prof_isr
vstub202:
    addq.w #1,scd_vec_hits+404
    bra.w prof_isr
vstub203:
    addq.w #1,scd_vec_hits+406
    bra.w prof_isr
vstub204:
    addq.w #1,scd_vec_hits+408
    bra.w prof_isr
vstub205:
    addq.w #1,scd_vec_hits+410
    bra.w prof_isr
vstub206:
    addq.w #1,scd_vec_hits+412
    bra.w prof_isr
vstub207:
    addq.w #1,scd_vec_hits+414
    bra.w prof_isr
vstub208:
    addq.w #1,scd_vec_hits+416
    bra.w prof_isr
vstub209:
    addq.w #1,scd_vec_hits+418
    bra.w prof_isr
vstub210:
    addq.w #1,scd_vec_hits+420
    bra.w prof_isr
vstub211:
    addq.w #1,scd_vec_hits+422
    bra.w prof_isr
vstub212:
    addq.w #1,scd_vec_hits+424
    bra.w prof_isr
vstub213:
    addq.w #1,scd_vec_hits+426
    bra.w prof_isr
vstub214:
    addq.w #1,scd_vec_hits+428
    bra.w prof_isr
vstub215:
    addq.w #1,scd_vec_hits+430
    bra.w prof_isr
vstub216:
    addq.w #1,scd_vec_hits+432
    bra.w prof_isr
vstub217:
    addq.w #1,scd_vec_hits+434
    bra.w prof_isr
vstub218:
    addq.w #1,scd_vec_hits+436
    bra.w prof_isr
vstub219:
    addq.w #1,scd_vec_hits+438
    bra.w prof_isr
vstub220:
    addq.w #1,scd_vec_hits+440
    bra.w prof_isr
vstub221:
    addq.w #1,scd_vec_hits+442
    bra.w prof_isr
vstub222:
    addq.w #1,scd_vec_hits+444
    bra.w prof_isr
vstub223:
    addq.w #1,scd_vec_hits+446
    bra.w prof_isr
vstub224:
    addq.w #1,scd_vec_hits+448
    bra.w prof_isr
vstub225:
    addq.w #1,scd_vec_hits+450
    bra.w prof_isr
vstub226:
    addq.w #1,scd_vec_hits+452
    bra.w prof_isr
vstub227:
    addq.w #1,scd_vec_hits+454
    bra.w prof_isr
vstub228:
    addq.w #1,scd_vec_hits+456
    bra.w prof_isr
vstub229:
    addq.w #1,scd_vec_hits+458
    bra.w prof_isr
vstub230:
    addq.w #1,scd_vec_hits+460
    bra.w prof_isr
vstub231:
    addq.w #1,scd_vec_hits+462
    bra.w prof_isr
vstub232:
    addq.w #1,scd_vec_hits+464
    bra.w prof_isr
vstub233:
    addq.w #1,scd_vec_hits+466
    bra.w prof_isr
vstub234:
    addq.w #1,scd_vec_hits+468
    bra.w prof_isr
vstub235:
    addq.w #1,scd_vec_hits+470
    bra.w prof_isr
vstub236:
    addq.w #1,scd_vec_hits+472
    bra.w prof_isr
vstub237:
    addq.w #1,scd_vec_hits+474
    bra.w prof_isr
vstub238:
    addq.w #1,scd_vec_hits+476
    bra.w prof_isr
vstub239:
    addq.w #1,scd_vec_hits+478
    bra.w prof_isr
vstub240:
    addq.w #1,scd_vec_hits+480
    bra.w prof_isr
vstub241:
    addq.w #1,scd_vec_hits+482
    bra.w prof_isr
vstub242:
    addq.w #1,scd_vec_hits+484
    bra.w prof_isr
vstub243:
    addq.w #1,scd_vec_hits+486
    bra.w prof_isr
vstub244:
    addq.w #1,scd_vec_hits+488
    bra.w prof_isr
vstub245:
    addq.w #1,scd_vec_hits+490
    bra.w prof_isr
vstub246:
    addq.w #1,scd_vec_hits+492
    bra.w prof_isr
vstub247:
    addq.w #1,scd_vec_hits+494
    bra.w prof_isr
vstub248:
    addq.w #1,scd_vec_hits+496
    bra.w prof_isr
vstub249:
    addq.w #1,scd_vec_hits+498
    bra.w prof_isr
vstub250:
    addq.w #1,scd_vec_hits+500
    bra.w prof_isr
vstub251:
    addq.w #1,scd_vec_hits+502
    bra.w prof_isr
vstub252:
    addq.w #1,scd_vec_hits+504
    bra.w prof_isr
vstub253:
    addq.w #1,scd_vec_hits+506
    bra.w prof_isr
vstub254:
    addq.w #1,scd_vec_hits+508
    bra.w prof_isr
vstub255:
    addq.w #1,scd_vec_hits+510
    bra.w prof_isr
prof_isr:
.ifdef PROF_MIN
    rte
.endif
    movem.l %d0/%a0,-(%sp)
    move.l 10(%sp),%d0
    cmpi.l #0x40000,%d0
    bcc.s 4f
    lsr.l #6,%d0
    add.l %d0,%d0
    lea scd_prof_bins,%a0
    addq.w #1,0(%a0,%d0.l)
    bcc.s 4f
    subq.w #1,0(%a0,%d0.l)
4:  movem.l (%sp)+,%d0/%a0
    rte
fault:
    move.w #0xdead,0xff8020
    bra.s fault
