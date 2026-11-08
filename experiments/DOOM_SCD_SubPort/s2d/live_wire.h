#ifndef S2D_LIVE_WIRE_H
#define S2D_LIVE_WIRE_H
#include <stdint.h>
#if defined(SCD_FAST)
#define S2D_MAGIC 0x53324546UL
#define S2D_VERSION 2u
#define S2D_MARKER 0x5AADu
/* Non-cryptographic word checksum: all packet words including length/seq;
 * checksum slot7 treated as zero. Same endian numeric words on both68000s. */
static inline uint32_t S2E_Checksum(volatile const uint32_t *p,uint32_t bytes){
    uint32_t h=2166136261UL;
    for(uint32_t i=0;i<bytes/4;i++){
        h=(h<<5)|(h>>27);h^=i==7?0:p[i];h+=0x9e3779b9UL;
    }
    return h;
}
#else
#define S2D_MAGIC 0x53324446UL
#define S2D_VERSION 1u
#define S2D_MARKER 0x5A9Du
#endif
#define S2D_INPUT_MAGIC 0x53324449UL
#define S2D_FRAME_OFFSET 0x1000UL
#define S2D_MAX_FRAME 16384UL
/* Frame header8u32: magic,version,tic,total,worldbytes,actorbytes,status,hash.
 * Camera32 at32; player24u32 at64; psprites2*16 at160; input echo16 at192.
 * Blobs start256: one complete S2b world and one complete S2c actor frame.
 * Input16: magic32,expected tic32,forward8,side8,turn16,buttons16,stop16.
 * Each completed swap gives MD the sub's previous state and sub its next cmd. */
#endif
