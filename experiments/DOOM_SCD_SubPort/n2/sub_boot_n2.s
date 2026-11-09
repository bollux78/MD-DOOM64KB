/* N2 sub boot: 256 vectors, every exception names itself through the sub I_Error channel
 * (message address in $FF802A/2C, 0xDEAD in $FF8020) instead of jumping into the void. */
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
vex2:
    move.l #vmsg2,%d0
    bra.w vexc
vex3:
    move.l #vmsg3,%d0
    bra.w vexc
vex4:
    move.l #vmsg4,%d0
    bra.w vexc
vex5:
    move.l #vmsg5,%d0
    bra.w vexc
vex6:
    move.l #vmsg6,%d0
    bra.w vexc
vex7:
    move.l #vmsg7,%d0
    bra.w vexc
vex8:
    move.l #vmsg8,%d0
    bra.w vexc
vex9:
    move.l #vmsg9,%d0
    bra.w vexc
vex10:
    move.l #vmsg10,%d0
    bra.w vexc
vex11:
    move.l #vmsg11,%d0
    bra.w vexc
vex12:
    move.l #vmsg12,%d0
    bra.w vexc
vex13:
    move.l #vmsg13,%d0
    bra.w vexc
vex14:
    move.l #vmsg14,%d0
    bra.w vexc
vex15:
    move.l #vmsg15,%d0
    bra.w vexc
vex16:
    move.l #vmsg16,%d0
    bra.w vexc
vex17:
    move.l #vmsg17,%d0
    bra.w vexc
vex18:
    move.l #vmsg18,%d0
    bra.w vexc
vex19:
    move.l #vmsg19,%d0
    bra.w vexc
vex20:
    move.l #vmsg20,%d0
    bra.w vexc
vex21:
    move.l #vmsg21,%d0
    bra.w vexc
vex22:
    move.l #vmsg22,%d0
    bra.w vexc
vex23:
    move.l #vmsg23,%d0
    bra.w vexc
vex24:
    move.l #vmsg24,%d0
    bra.w vexc
vex25:
    move.l #vmsg25,%d0
    bra.w vexc
vex26:
    move.l #vmsg26,%d0
    bra.w vexc
vex27:
    move.l #vmsg27,%d0
    bra.w vexc
vex28:
    move.l #vmsg28,%d0
    bra.w vexc
vex29:
    move.l #vmsg29,%d0
    bra.w vexc
vex30:
    move.l #vmsg30,%d0
    bra.w vexc
vex31:
    move.l #vmsg31,%d0
    bra.w vexc
vex32:
    move.l #vmsg32,%d0
    bra.w vexc
vex33:
    move.l #vmsg33,%d0
    bra.w vexc
vex34:
    move.l #vmsg34,%d0
    bra.w vexc
vex35:
    move.l #vmsg35,%d0
    bra.w vexc
vex36:
    move.l #vmsg36,%d0
    bra.w vexc
vex37:
    move.l #vmsg37,%d0
    bra.w vexc
vex38:
    move.l #vmsg38,%d0
    bra.w vexc
vex39:
    move.l #vmsg39,%d0
    bra.w vexc
vex40:
    move.l #vmsg40,%d0
    bra.w vexc
vex41:
    move.l #vmsg41,%d0
    bra.w vexc
vex42:
    move.l #vmsg42,%d0
    bra.w vexc
vex43:
    move.l #vmsg43,%d0
    bra.w vexc
vex44:
    move.l #vmsg44,%d0
    bra.w vexc
vex45:
    move.l #vmsg45,%d0
    bra.w vexc
vex46:
    move.l #vmsg46,%d0
    bra.w vexc
vex47:
    move.l #vmsg47,%d0
    bra.w vexc
vex48:
    move.l #vmsg48,%d0
    bra.w vexc
vex49:
    move.l #vmsg49,%d0
    bra.w vexc
vex50:
    move.l #vmsg50,%d0
    bra.w vexc
vex51:
    move.l #vmsg51,%d0
    bra.w vexc
vex52:
    move.l #vmsg52,%d0
    bra.w vexc
vex53:
    move.l #vmsg53,%d0
    bra.w vexc
vex54:
    move.l #vmsg54,%d0
    bra.w vexc
vex55:
    move.l #vmsg55,%d0
    bra.w vexc
vex56:
    move.l #vmsg56,%d0
    bra.w vexc
vex57:
    move.l #vmsg57,%d0
    bra.w vexc
vex58:
    move.l #vmsg58,%d0
    bra.w vexc
vex59:
    move.l #vmsg59,%d0
    bra.w vexc
vex60:
    move.l #vmsg60,%d0
    bra.w vexc
vex61:
    move.l #vmsg61,%d0
    bra.w vexc
vex62:
    move.l #vmsg62,%d0
    bra.w vexc
vex63:
    move.l #vmsg63,%d0
    bra.w vexc
vex64:
    move.l #vmsg64,%d0
    bra.w vexc
vex65:
    move.l #vmsg65,%d0
    bra.w vexc
vex66:
    move.l #vmsg66,%d0
    bra.w vexc
vex67:
    move.l #vmsg67,%d0
    bra.w vexc
vex68:
    move.l #vmsg68,%d0
    bra.w vexc
vex69:
    move.l #vmsg69,%d0
    bra.w vexc
vex70:
    move.l #vmsg70,%d0
    bra.w vexc
vex71:
    move.l #vmsg71,%d0
    bra.w vexc
vex72:
    move.l #vmsg72,%d0
    bra.w vexc
vex73:
    move.l #vmsg73,%d0
    bra.w vexc
vex74:
    move.l #vmsg74,%d0
    bra.w vexc
vex75:
    move.l #vmsg75,%d0
    bra.w vexc
vex76:
    move.l #vmsg76,%d0
    bra.w vexc
vex77:
    move.l #vmsg77,%d0
    bra.w vexc
vex78:
    move.l #vmsg78,%d0
    bra.w vexc
vex79:
    move.l #vmsg79,%d0
    bra.w vexc
vex80:
    move.l #vmsg80,%d0
    bra.w vexc
vex81:
    move.l #vmsg81,%d0
    bra.w vexc
vex82:
    move.l #vmsg82,%d0
    bra.w vexc
vex83:
    move.l #vmsg83,%d0
    bra.w vexc
vex84:
    move.l #vmsg84,%d0
    bra.w vexc
vex85:
    move.l #vmsg85,%d0
    bra.w vexc
vex86:
    move.l #vmsg86,%d0
    bra.w vexc
vex87:
    move.l #vmsg87,%d0
    bra.w vexc
vex88:
    move.l #vmsg88,%d0
    bra.w vexc
vex89:
    move.l #vmsg89,%d0
    bra.w vexc
vex90:
    move.l #vmsg90,%d0
    bra.w vexc
vex91:
    move.l #vmsg91,%d0
    bra.w vexc
vex92:
    move.l #vmsg92,%d0
    bra.w vexc
vex93:
    move.l #vmsg93,%d0
    bra.w vexc
vex94:
    move.l #vmsg94,%d0
    bra.w vexc
vex95:
    move.l #vmsg95,%d0
    bra.w vexc
vex96:
    move.l #vmsg96,%d0
    bra.w vexc
vex97:
    move.l #vmsg97,%d0
    bra.w vexc
vex98:
    move.l #vmsg98,%d0
    bra.w vexc
vex99:
    move.l #vmsg99,%d0
    bra.w vexc
vex100:
    move.l #vmsg100,%d0
    bra.w vexc
vex101:
    move.l #vmsg101,%d0
    bra.w vexc
vex102:
    move.l #vmsg102,%d0
    bra.w vexc
vex103:
    move.l #vmsg103,%d0
    bra.w vexc
vex104:
    move.l #vmsg104,%d0
    bra.w vexc
vex105:
    move.l #vmsg105,%d0
    bra.w vexc
vex106:
    move.l #vmsg106,%d0
    bra.w vexc
vex107:
    move.l #vmsg107,%d0
    bra.w vexc
vex108:
    move.l #vmsg108,%d0
    bra.w vexc
vex109:
    move.l #vmsg109,%d0
    bra.w vexc
vex110:
    move.l #vmsg110,%d0
    bra.w vexc
vex111:
    move.l #vmsg111,%d0
    bra.w vexc
vex112:
    move.l #vmsg112,%d0
    bra.w vexc
vex113:
    move.l #vmsg113,%d0
    bra.w vexc
vex114:
    move.l #vmsg114,%d0
    bra.w vexc
vex115:
    move.l #vmsg115,%d0
    bra.w vexc
vex116:
    move.l #vmsg116,%d0
    bra.w vexc
vex117:
    move.l #vmsg117,%d0
    bra.w vexc
vex118:
    move.l #vmsg118,%d0
    bra.w vexc
vex119:
    move.l #vmsg119,%d0
    bra.w vexc
vex120:
    move.l #vmsg120,%d0
    bra.w vexc
vex121:
    move.l #vmsg121,%d0
    bra.w vexc
vex122:
    move.l #vmsg122,%d0
    bra.w vexc
vex123:
    move.l #vmsg123,%d0
    bra.w vexc
vex124:
    move.l #vmsg124,%d0
    bra.w vexc
vex125:
    move.l #vmsg125,%d0
    bra.w vexc
vex126:
    move.l #vmsg126,%d0
    bra.w vexc
vex127:
    move.l #vmsg127,%d0
    bra.w vexc
vex128:
    move.l #vmsg128,%d0
    bra.w vexc
vex129:
    move.l #vmsg129,%d0
    bra.w vexc
vex130:
    move.l #vmsg130,%d0
    bra.w vexc
vex131:
    move.l #vmsg131,%d0
    bra.w vexc
vex132:
    move.l #vmsg132,%d0
    bra.w vexc
vex133:
    move.l #vmsg133,%d0
    bra.w vexc
vex134:
    move.l #vmsg134,%d0
    bra.w vexc
vex135:
    move.l #vmsg135,%d0
    bra.w vexc
vex136:
    move.l #vmsg136,%d0
    bra.w vexc
vex137:
    move.l #vmsg137,%d0
    bra.w vexc
vex138:
    move.l #vmsg138,%d0
    bra.w vexc
vex139:
    move.l #vmsg139,%d0
    bra.w vexc
vex140:
    move.l #vmsg140,%d0
    bra.w vexc
vex141:
    move.l #vmsg141,%d0
    bra.w vexc
vex142:
    move.l #vmsg142,%d0
    bra.w vexc
vex143:
    move.l #vmsg143,%d0
    bra.w vexc
vex144:
    move.l #vmsg144,%d0
    bra.w vexc
vex145:
    move.l #vmsg145,%d0
    bra.w vexc
vex146:
    move.l #vmsg146,%d0
    bra.w vexc
vex147:
    move.l #vmsg147,%d0
    bra.w vexc
vex148:
    move.l #vmsg148,%d0
    bra.w vexc
vex149:
    move.l #vmsg149,%d0
    bra.w vexc
vex150:
    move.l #vmsg150,%d0
    bra.w vexc
vex151:
    move.l #vmsg151,%d0
    bra.w vexc
vex152:
    move.l #vmsg152,%d0
    bra.w vexc
vex153:
    move.l #vmsg153,%d0
    bra.w vexc
vex154:
    move.l #vmsg154,%d0
    bra.w vexc
vex155:
    move.l #vmsg155,%d0
    bra.w vexc
vex156:
    move.l #vmsg156,%d0
    bra.w vexc
vex157:
    move.l #vmsg157,%d0
    bra.w vexc
vex158:
    move.l #vmsg158,%d0
    bra.w vexc
vex159:
    move.l #vmsg159,%d0
    bra.w vexc
vex160:
    move.l #vmsg160,%d0
    bra.w vexc
vex161:
    move.l #vmsg161,%d0
    bra.w vexc
vex162:
    move.l #vmsg162,%d0
    bra.w vexc
vex163:
    move.l #vmsg163,%d0
    bra.w vexc
vex164:
    move.l #vmsg164,%d0
    bra.w vexc
vex165:
    move.l #vmsg165,%d0
    bra.w vexc
vex166:
    move.l #vmsg166,%d0
    bra.w vexc
vex167:
    move.l #vmsg167,%d0
    bra.w vexc
vex168:
    move.l #vmsg168,%d0
    bra.w vexc
vex169:
    move.l #vmsg169,%d0
    bra.w vexc
vex170:
    move.l #vmsg170,%d0
    bra.w vexc
vex171:
    move.l #vmsg171,%d0
    bra.w vexc
vex172:
    move.l #vmsg172,%d0
    bra.w vexc
vex173:
    move.l #vmsg173,%d0
    bra.w vexc
vex174:
    move.l #vmsg174,%d0
    bra.w vexc
vex175:
    move.l #vmsg175,%d0
    bra.w vexc
vex176:
    move.l #vmsg176,%d0
    bra.w vexc
vex177:
    move.l #vmsg177,%d0
    bra.w vexc
vex178:
    move.l #vmsg178,%d0
    bra.w vexc
vex179:
    move.l #vmsg179,%d0
    bra.w vexc
vex180:
    move.l #vmsg180,%d0
    bra.w vexc
vex181:
    move.l #vmsg181,%d0
    bra.w vexc
vex182:
    move.l #vmsg182,%d0
    bra.w vexc
vex183:
    move.l #vmsg183,%d0
    bra.w vexc
vex184:
    move.l #vmsg184,%d0
    bra.w vexc
vex185:
    move.l #vmsg185,%d0
    bra.w vexc
vex186:
    move.l #vmsg186,%d0
    bra.w vexc
vex187:
    move.l #vmsg187,%d0
    bra.w vexc
vex188:
    move.l #vmsg188,%d0
    bra.w vexc
vex189:
    move.l #vmsg189,%d0
    bra.w vexc
vex190:
    move.l #vmsg190,%d0
    bra.w vexc
vex191:
    move.l #vmsg191,%d0
    bra.w vexc
vex192:
    move.l #vmsg192,%d0
    bra.w vexc
vex193:
    move.l #vmsg193,%d0
    bra.w vexc
vex194:
    move.l #vmsg194,%d0
    bra.w vexc
vex195:
    move.l #vmsg195,%d0
    bra.w vexc
vex196:
    move.l #vmsg196,%d0
    bra.w vexc
vex197:
    move.l #vmsg197,%d0
    bra.w vexc
vex198:
    move.l #vmsg198,%d0
    bra.w vexc
vex199:
    move.l #vmsg199,%d0
    bra.w vexc
vex200:
    move.l #vmsg200,%d0
    bra.w vexc
vex201:
    move.l #vmsg201,%d0
    bra.w vexc
vex202:
    move.l #vmsg202,%d0
    bra.w vexc
vex203:
    move.l #vmsg203,%d0
    bra.w vexc
vex204:
    move.l #vmsg204,%d0
    bra.w vexc
vex205:
    move.l #vmsg205,%d0
    bra.w vexc
vex206:
    move.l #vmsg206,%d0
    bra.w vexc
vex207:
    move.l #vmsg207,%d0
    bra.w vexc
vex208:
    move.l #vmsg208,%d0
    bra.w vexc
vex209:
    move.l #vmsg209,%d0
    bra.w vexc
vex210:
    move.l #vmsg210,%d0
    bra.w vexc
vex211:
    move.l #vmsg211,%d0
    bra.w vexc
vex212:
    move.l #vmsg212,%d0
    bra.w vexc
vex213:
    move.l #vmsg213,%d0
    bra.w vexc
vex214:
    move.l #vmsg214,%d0
    bra.w vexc
vex215:
    move.l #vmsg215,%d0
    bra.w vexc
vex216:
    move.l #vmsg216,%d0
    bra.w vexc
vex217:
    move.l #vmsg217,%d0
    bra.w vexc
vex218:
    move.l #vmsg218,%d0
    bra.w vexc
vex219:
    move.l #vmsg219,%d0
    bra.w vexc
vex220:
    move.l #vmsg220,%d0
    bra.w vexc
vex221:
    move.l #vmsg221,%d0
    bra.w vexc
vex222:
    move.l #vmsg222,%d0
    bra.w vexc
vex223:
    move.l #vmsg223,%d0
    bra.w vexc
vex224:
    move.l #vmsg224,%d0
    bra.w vexc
vex225:
    move.l #vmsg225,%d0
    bra.w vexc
vex226:
    move.l #vmsg226,%d0
    bra.w vexc
vex227:
    move.l #vmsg227,%d0
    bra.w vexc
vex228:
    move.l #vmsg228,%d0
    bra.w vexc
vex229:
    move.l #vmsg229,%d0
    bra.w vexc
vex230:
    move.l #vmsg230,%d0
    bra.w vexc
vex231:
    move.l #vmsg231,%d0
    bra.w vexc
vex232:
    move.l #vmsg232,%d0
    bra.w vexc
vex233:
    move.l #vmsg233,%d0
    bra.w vexc
vex234:
    move.l #vmsg234,%d0
    bra.w vexc
vex235:
    move.l #vmsg235,%d0
    bra.w vexc
vex236:
    move.l #vmsg236,%d0
    bra.w vexc
vex237:
    move.l #vmsg237,%d0
    bra.w vexc
vex238:
    move.l #vmsg238,%d0
    bra.w vexc
vex239:
    move.l #vmsg239,%d0
    bra.w vexc
vex240:
    move.l #vmsg240,%d0
    bra.w vexc
vex241:
    move.l #vmsg241,%d0
    bra.w vexc
vex242:
    move.l #vmsg242,%d0
    bra.w vexc
vex243:
    move.l #vmsg243,%d0
    bra.w vexc
vex244:
    move.l #vmsg244,%d0
    bra.w vexc
vex245:
    move.l #vmsg245,%d0
    bra.w vexc
vex246:
    move.l #vmsg246,%d0
    bra.w vexc
vex247:
    move.l #vmsg247,%d0
    bra.w vexc
vex248:
    move.l #vmsg248,%d0
    bra.w vexc
vex249:
    move.l #vmsg249,%d0
    bra.w vexc
vex250:
    move.l #vmsg250,%d0
    bra.w vexc
vex251:
    move.l #vmsg251,%d0
    bra.w vexc
vex252:
    move.l #vmsg252,%d0
    bra.w vexc
vex253:
    move.l #vmsg253,%d0
    bra.w vexc
vex254:
    move.l #vmsg254,%d0
    bra.w vexc
vex255:
    move.l #vmsg255,%d0
    bra.w vexc
vexc:
    move.w #0x2700,%sr
    move.l 2(%sp),0xff8026
    move.w %d0,0xff802c
    swap %d0
    move.w %d0,0xff802a
    move.w #0xdead,0xff8020
4:  bra.s 4b
vmsg2: .asciz "SUB EXCEPTION VECTOR 2"
vmsg3: .asciz "SUB EXCEPTION VECTOR 3"
vmsg4: .asciz "SUB EXCEPTION VECTOR 4"
vmsg5: .asciz "SUB EXCEPTION VECTOR 5"
vmsg6: .asciz "SUB EXCEPTION VECTOR 6"
vmsg7: .asciz "SUB EXCEPTION VECTOR 7"
vmsg8: .asciz "SUB EXCEPTION VECTOR 8"
vmsg9: .asciz "SUB EXCEPTION VECTOR 9"
vmsg10: .asciz "SUB EXCEPTION VECTOR 10"
vmsg11: .asciz "SUB EXCEPTION VECTOR 11"
vmsg12: .asciz "SUB EXCEPTION VECTOR 12"
vmsg13: .asciz "SUB EXCEPTION VECTOR 13"
vmsg14: .asciz "SUB EXCEPTION VECTOR 14"
vmsg15: .asciz "SUB EXCEPTION VECTOR 15"
vmsg16: .asciz "SUB EXCEPTION VECTOR 16"
vmsg17: .asciz "SUB EXCEPTION VECTOR 17"
vmsg18: .asciz "SUB EXCEPTION VECTOR 18"
vmsg19: .asciz "SUB EXCEPTION VECTOR 19"
vmsg20: .asciz "SUB EXCEPTION VECTOR 20"
vmsg21: .asciz "SUB EXCEPTION VECTOR 21"
vmsg22: .asciz "SUB EXCEPTION VECTOR 22"
vmsg23: .asciz "SUB EXCEPTION VECTOR 23"
vmsg24: .asciz "SUB EXCEPTION VECTOR 24"
vmsg25: .asciz "SUB EXCEPTION VECTOR 25"
vmsg26: .asciz "SUB EXCEPTION VECTOR 26"
vmsg27: .asciz "SUB EXCEPTION VECTOR 27"
vmsg28: .asciz "SUB EXCEPTION VECTOR 28"
vmsg29: .asciz "SUB EXCEPTION VECTOR 29"
vmsg30: .asciz "SUB EXCEPTION VECTOR 30"
vmsg31: .asciz "SUB EXCEPTION VECTOR 31"
vmsg32: .asciz "SUB EXCEPTION VECTOR 32"
vmsg33: .asciz "SUB EXCEPTION VECTOR 33"
vmsg34: .asciz "SUB EXCEPTION VECTOR 34"
vmsg35: .asciz "SUB EXCEPTION VECTOR 35"
vmsg36: .asciz "SUB EXCEPTION VECTOR 36"
vmsg37: .asciz "SUB EXCEPTION VECTOR 37"
vmsg38: .asciz "SUB EXCEPTION VECTOR 38"
vmsg39: .asciz "SUB EXCEPTION VECTOR 39"
vmsg40: .asciz "SUB EXCEPTION VECTOR 40"
vmsg41: .asciz "SUB EXCEPTION VECTOR 41"
vmsg42: .asciz "SUB EXCEPTION VECTOR 42"
vmsg43: .asciz "SUB EXCEPTION VECTOR 43"
vmsg44: .asciz "SUB EXCEPTION VECTOR 44"
vmsg45: .asciz "SUB EXCEPTION VECTOR 45"
vmsg46: .asciz "SUB EXCEPTION VECTOR 46"
vmsg47: .asciz "SUB EXCEPTION VECTOR 47"
vmsg48: .asciz "SUB EXCEPTION VECTOR 48"
vmsg49: .asciz "SUB EXCEPTION VECTOR 49"
vmsg50: .asciz "SUB EXCEPTION VECTOR 50"
vmsg51: .asciz "SUB EXCEPTION VECTOR 51"
vmsg52: .asciz "SUB EXCEPTION VECTOR 52"
vmsg53: .asciz "SUB EXCEPTION VECTOR 53"
vmsg54: .asciz "SUB EXCEPTION VECTOR 54"
vmsg55: .asciz "SUB EXCEPTION VECTOR 55"
vmsg56: .asciz "SUB EXCEPTION VECTOR 56"
vmsg57: .asciz "SUB EXCEPTION VECTOR 57"
vmsg58: .asciz "SUB EXCEPTION VECTOR 58"
vmsg59: .asciz "SUB EXCEPTION VECTOR 59"
vmsg60: .asciz "SUB EXCEPTION VECTOR 60"
vmsg61: .asciz "SUB EXCEPTION VECTOR 61"
vmsg62: .asciz "SUB EXCEPTION VECTOR 62"
vmsg63: .asciz "SUB EXCEPTION VECTOR 63"
vmsg64: .asciz "SUB EXCEPTION VECTOR 64"
vmsg65: .asciz "SUB EXCEPTION VECTOR 65"
vmsg66: .asciz "SUB EXCEPTION VECTOR 66"
vmsg67: .asciz "SUB EXCEPTION VECTOR 67"
vmsg68: .asciz "SUB EXCEPTION VECTOR 68"
vmsg69: .asciz "SUB EXCEPTION VECTOR 69"
vmsg70: .asciz "SUB EXCEPTION VECTOR 70"
vmsg71: .asciz "SUB EXCEPTION VECTOR 71"
vmsg72: .asciz "SUB EXCEPTION VECTOR 72"
vmsg73: .asciz "SUB EXCEPTION VECTOR 73"
vmsg74: .asciz "SUB EXCEPTION VECTOR 74"
vmsg75: .asciz "SUB EXCEPTION VECTOR 75"
vmsg76: .asciz "SUB EXCEPTION VECTOR 76"
vmsg77: .asciz "SUB EXCEPTION VECTOR 77"
vmsg78: .asciz "SUB EXCEPTION VECTOR 78"
vmsg79: .asciz "SUB EXCEPTION VECTOR 79"
vmsg80: .asciz "SUB EXCEPTION VECTOR 80"
vmsg81: .asciz "SUB EXCEPTION VECTOR 81"
vmsg82: .asciz "SUB EXCEPTION VECTOR 82"
vmsg83: .asciz "SUB EXCEPTION VECTOR 83"
vmsg84: .asciz "SUB EXCEPTION VECTOR 84"
vmsg85: .asciz "SUB EXCEPTION VECTOR 85"
vmsg86: .asciz "SUB EXCEPTION VECTOR 86"
vmsg87: .asciz "SUB EXCEPTION VECTOR 87"
vmsg88: .asciz "SUB EXCEPTION VECTOR 88"
vmsg89: .asciz "SUB EXCEPTION VECTOR 89"
vmsg90: .asciz "SUB EXCEPTION VECTOR 90"
vmsg91: .asciz "SUB EXCEPTION VECTOR 91"
vmsg92: .asciz "SUB EXCEPTION VECTOR 92"
vmsg93: .asciz "SUB EXCEPTION VECTOR 93"
vmsg94: .asciz "SUB EXCEPTION VECTOR 94"
vmsg95: .asciz "SUB EXCEPTION VECTOR 95"
vmsg96: .asciz "SUB EXCEPTION VECTOR 96"
vmsg97: .asciz "SUB EXCEPTION VECTOR 97"
vmsg98: .asciz "SUB EXCEPTION VECTOR 98"
vmsg99: .asciz "SUB EXCEPTION VECTOR 99"
vmsg100: .asciz "SUB EXCEPTION VECTOR 100"
vmsg101: .asciz "SUB EXCEPTION VECTOR 101"
vmsg102: .asciz "SUB EXCEPTION VECTOR 102"
vmsg103: .asciz "SUB EXCEPTION VECTOR 103"
vmsg104: .asciz "SUB EXCEPTION VECTOR 104"
vmsg105: .asciz "SUB EXCEPTION VECTOR 105"
vmsg106: .asciz "SUB EXCEPTION VECTOR 106"
vmsg107: .asciz "SUB EXCEPTION VECTOR 107"
vmsg108: .asciz "SUB EXCEPTION VECTOR 108"
vmsg109: .asciz "SUB EXCEPTION VECTOR 109"
vmsg110: .asciz "SUB EXCEPTION VECTOR 110"
vmsg111: .asciz "SUB EXCEPTION VECTOR 111"
vmsg112: .asciz "SUB EXCEPTION VECTOR 112"
vmsg113: .asciz "SUB EXCEPTION VECTOR 113"
vmsg114: .asciz "SUB EXCEPTION VECTOR 114"
vmsg115: .asciz "SUB EXCEPTION VECTOR 115"
vmsg116: .asciz "SUB EXCEPTION VECTOR 116"
vmsg117: .asciz "SUB EXCEPTION VECTOR 117"
vmsg118: .asciz "SUB EXCEPTION VECTOR 118"
vmsg119: .asciz "SUB EXCEPTION VECTOR 119"
vmsg120: .asciz "SUB EXCEPTION VECTOR 120"
vmsg121: .asciz "SUB EXCEPTION VECTOR 121"
vmsg122: .asciz "SUB EXCEPTION VECTOR 122"
vmsg123: .asciz "SUB EXCEPTION VECTOR 123"
vmsg124: .asciz "SUB EXCEPTION VECTOR 124"
vmsg125: .asciz "SUB EXCEPTION VECTOR 125"
vmsg126: .asciz "SUB EXCEPTION VECTOR 126"
vmsg127: .asciz "SUB EXCEPTION VECTOR 127"
vmsg128: .asciz "SUB EXCEPTION VECTOR 128"
vmsg129: .asciz "SUB EXCEPTION VECTOR 129"
vmsg130: .asciz "SUB EXCEPTION VECTOR 130"
vmsg131: .asciz "SUB EXCEPTION VECTOR 131"
vmsg132: .asciz "SUB EXCEPTION VECTOR 132"
vmsg133: .asciz "SUB EXCEPTION VECTOR 133"
vmsg134: .asciz "SUB EXCEPTION VECTOR 134"
vmsg135: .asciz "SUB EXCEPTION VECTOR 135"
vmsg136: .asciz "SUB EXCEPTION VECTOR 136"
vmsg137: .asciz "SUB EXCEPTION VECTOR 137"
vmsg138: .asciz "SUB EXCEPTION VECTOR 138"
vmsg139: .asciz "SUB EXCEPTION VECTOR 139"
vmsg140: .asciz "SUB EXCEPTION VECTOR 140"
vmsg141: .asciz "SUB EXCEPTION VECTOR 141"
vmsg142: .asciz "SUB EXCEPTION VECTOR 142"
vmsg143: .asciz "SUB EXCEPTION VECTOR 143"
vmsg144: .asciz "SUB EXCEPTION VECTOR 144"
vmsg145: .asciz "SUB EXCEPTION VECTOR 145"
vmsg146: .asciz "SUB EXCEPTION VECTOR 146"
vmsg147: .asciz "SUB EXCEPTION VECTOR 147"
vmsg148: .asciz "SUB EXCEPTION VECTOR 148"
vmsg149: .asciz "SUB EXCEPTION VECTOR 149"
vmsg150: .asciz "SUB EXCEPTION VECTOR 150"
vmsg151: .asciz "SUB EXCEPTION VECTOR 151"
vmsg152: .asciz "SUB EXCEPTION VECTOR 152"
vmsg153: .asciz "SUB EXCEPTION VECTOR 153"
vmsg154: .asciz "SUB EXCEPTION VECTOR 154"
vmsg155: .asciz "SUB EXCEPTION VECTOR 155"
vmsg156: .asciz "SUB EXCEPTION VECTOR 156"
vmsg157: .asciz "SUB EXCEPTION VECTOR 157"
vmsg158: .asciz "SUB EXCEPTION VECTOR 158"
vmsg159: .asciz "SUB EXCEPTION VECTOR 159"
vmsg160: .asciz "SUB EXCEPTION VECTOR 160"
vmsg161: .asciz "SUB EXCEPTION VECTOR 161"
vmsg162: .asciz "SUB EXCEPTION VECTOR 162"
vmsg163: .asciz "SUB EXCEPTION VECTOR 163"
vmsg164: .asciz "SUB EXCEPTION VECTOR 164"
vmsg165: .asciz "SUB EXCEPTION VECTOR 165"
vmsg166: .asciz "SUB EXCEPTION VECTOR 166"
vmsg167: .asciz "SUB EXCEPTION VECTOR 167"
vmsg168: .asciz "SUB EXCEPTION VECTOR 168"
vmsg169: .asciz "SUB EXCEPTION VECTOR 169"
vmsg170: .asciz "SUB EXCEPTION VECTOR 170"
vmsg171: .asciz "SUB EXCEPTION VECTOR 171"
vmsg172: .asciz "SUB EXCEPTION VECTOR 172"
vmsg173: .asciz "SUB EXCEPTION VECTOR 173"
vmsg174: .asciz "SUB EXCEPTION VECTOR 174"
vmsg175: .asciz "SUB EXCEPTION VECTOR 175"
vmsg176: .asciz "SUB EXCEPTION VECTOR 176"
vmsg177: .asciz "SUB EXCEPTION VECTOR 177"
vmsg178: .asciz "SUB EXCEPTION VECTOR 178"
vmsg179: .asciz "SUB EXCEPTION VECTOR 179"
vmsg180: .asciz "SUB EXCEPTION VECTOR 180"
vmsg181: .asciz "SUB EXCEPTION VECTOR 181"
vmsg182: .asciz "SUB EXCEPTION VECTOR 182"
vmsg183: .asciz "SUB EXCEPTION VECTOR 183"
vmsg184: .asciz "SUB EXCEPTION VECTOR 184"
vmsg185: .asciz "SUB EXCEPTION VECTOR 185"
vmsg186: .asciz "SUB EXCEPTION VECTOR 186"
vmsg187: .asciz "SUB EXCEPTION VECTOR 187"
vmsg188: .asciz "SUB EXCEPTION VECTOR 188"
vmsg189: .asciz "SUB EXCEPTION VECTOR 189"
vmsg190: .asciz "SUB EXCEPTION VECTOR 190"
vmsg191: .asciz "SUB EXCEPTION VECTOR 191"
vmsg192: .asciz "SUB EXCEPTION VECTOR 192"
vmsg193: .asciz "SUB EXCEPTION VECTOR 193"
vmsg194: .asciz "SUB EXCEPTION VECTOR 194"
vmsg195: .asciz "SUB EXCEPTION VECTOR 195"
vmsg196: .asciz "SUB EXCEPTION VECTOR 196"
vmsg197: .asciz "SUB EXCEPTION VECTOR 197"
vmsg198: .asciz "SUB EXCEPTION VECTOR 198"
vmsg199: .asciz "SUB EXCEPTION VECTOR 199"
vmsg200: .asciz "SUB EXCEPTION VECTOR 200"
vmsg201: .asciz "SUB EXCEPTION VECTOR 201"
vmsg202: .asciz "SUB EXCEPTION VECTOR 202"
vmsg203: .asciz "SUB EXCEPTION VECTOR 203"
vmsg204: .asciz "SUB EXCEPTION VECTOR 204"
vmsg205: .asciz "SUB EXCEPTION VECTOR 205"
vmsg206: .asciz "SUB EXCEPTION VECTOR 206"
vmsg207: .asciz "SUB EXCEPTION VECTOR 207"
vmsg208: .asciz "SUB EXCEPTION VECTOR 208"
vmsg209: .asciz "SUB EXCEPTION VECTOR 209"
vmsg210: .asciz "SUB EXCEPTION VECTOR 210"
vmsg211: .asciz "SUB EXCEPTION VECTOR 211"
vmsg212: .asciz "SUB EXCEPTION VECTOR 212"
vmsg213: .asciz "SUB EXCEPTION VECTOR 213"
vmsg214: .asciz "SUB EXCEPTION VECTOR 214"
vmsg215: .asciz "SUB EXCEPTION VECTOR 215"
vmsg216: .asciz "SUB EXCEPTION VECTOR 216"
vmsg217: .asciz "SUB EXCEPTION VECTOR 217"
vmsg218: .asciz "SUB EXCEPTION VECTOR 218"
vmsg219: .asciz "SUB EXCEPTION VECTOR 219"
vmsg220: .asciz "SUB EXCEPTION VECTOR 220"
vmsg221: .asciz "SUB EXCEPTION VECTOR 221"
vmsg222: .asciz "SUB EXCEPTION VECTOR 222"
vmsg223: .asciz "SUB EXCEPTION VECTOR 223"
vmsg224: .asciz "SUB EXCEPTION VECTOR 224"
vmsg225: .asciz "SUB EXCEPTION VECTOR 225"
vmsg226: .asciz "SUB EXCEPTION VECTOR 226"
vmsg227: .asciz "SUB EXCEPTION VECTOR 227"
vmsg228: .asciz "SUB EXCEPTION VECTOR 228"
vmsg229: .asciz "SUB EXCEPTION VECTOR 229"
vmsg230: .asciz "SUB EXCEPTION VECTOR 230"
vmsg231: .asciz "SUB EXCEPTION VECTOR 231"
vmsg232: .asciz "SUB EXCEPTION VECTOR 232"
vmsg233: .asciz "SUB EXCEPTION VECTOR 233"
vmsg234: .asciz "SUB EXCEPTION VECTOR 234"
vmsg235: .asciz "SUB EXCEPTION VECTOR 235"
vmsg236: .asciz "SUB EXCEPTION VECTOR 236"
vmsg237: .asciz "SUB EXCEPTION VECTOR 237"
vmsg238: .asciz "SUB EXCEPTION VECTOR 238"
vmsg239: .asciz "SUB EXCEPTION VECTOR 239"
vmsg240: .asciz "SUB EXCEPTION VECTOR 240"
vmsg241: .asciz "SUB EXCEPTION VECTOR 241"
vmsg242: .asciz "SUB EXCEPTION VECTOR 242"
vmsg243: .asciz "SUB EXCEPTION VECTOR 243"
vmsg244: .asciz "SUB EXCEPTION VECTOR 244"
vmsg245: .asciz "SUB EXCEPTION VECTOR 245"
vmsg246: .asciz "SUB EXCEPTION VECTOR 246"
vmsg247: .asciz "SUB EXCEPTION VECTOR 247"
vmsg248: .asciz "SUB EXCEPTION VECTOR 248"
vmsg249: .asciz "SUB EXCEPTION VECTOR 249"
vmsg250: .asciz "SUB EXCEPTION VECTOR 250"
vmsg251: .asciz "SUB EXCEPTION VECTOR 251"
vmsg252: .asciz "SUB EXCEPTION VECTOR 252"
vmsg253: .asciz "SUB EXCEPTION VECTOR 253"
vmsg254: .asciz "SUB EXCEPTION VECTOR 254"
vmsg255: .asciz "SUB EXCEPTION VECTOR 255"
    .even
