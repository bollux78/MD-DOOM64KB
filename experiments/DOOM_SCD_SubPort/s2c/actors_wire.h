#ifndef S2C_ACTORS_WIRE_H
#define S2C_ACTORS_WIRE_H
#include <stdint.h>
#define S2C_MAGIC 0x53324342UL
#define S2C_SUB_BASE 0x68000UL
#define S2C_MD_BASE 0x608000UL
#define S2C_CAPACITY 49152UL
#define S2C_MAX_ACTORS 64u
#define S2C_MAX_ROM 512u
#define S2C_RECORD_BYTES 36u
#define S2C_MD_POOL 0x614000UL
#define S2C_MD_APPLIED 0x617000UL
#define S2C_MD_REPORT 0x61B040UL
/* Header8u32: magic,version,count,romcount,used,checksum,stride,reserved.
 * offsets[27] at32; records start256. Frame16: tic32,nactors16,nrom16,
 * canonical hash32,playerid16,reserved16. Actor36: id/type16,xyz32,
 * angle/flags32,state/sprite/frame16,health/tics s16,sector16.
 * R24 delta8: index16,removed16,delay16,reserved16. */
#endif
