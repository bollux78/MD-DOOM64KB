/* S2b: world-visual delta stream. All fields big-endian, no native pointers.
 * Header 8*u32: magic,version,count,nsectors,nsides,used,stream_hash,reserved;
 * offsets[27] u32 at byte32, records begin byte256.
 * Frame: tic u32, ns u16, nd u16, canonical_hash u32, leveltime u32.
 * Sector16: id u16, light s16, floor s32, ceiling s32, floorpic/ceilpic s16.
 * Side12: id u16, textureoffset/top/bottom/mid s16, reserved u16.
 */
#ifndef S2B_WORLD_WIRE_H
#define S2B_WORLD_WIRE_H
#include <stdint.h>
#define S2B_MAGIC 0x53325742UL
#define S2B_VERSION 1u
#define S2B_COUNT 27u
#define S2B_CAPACITY 32768UL
#define S2B_SUB_WORLD 0x74000UL
#define S2B_MD_WORLD 0x600000UL
#define S2B_MD_REPORT 0x61B020UL
#define S2B_MAX_SECTORS 256u
#define S2B_MAX_SIDES 1024u
#endif
