#ifndef S2D_LIVE_WIRE_H
#define S2D_LIVE_WIRE_H
#include <stdint.h>
#define S2D_MAGIC 0x53324446UL
#define S2D_INPUT_MAGIC 0x53324449UL
#define S2D_FRAME_OFFSET 0x1000UL
#define S2D_MAX_FRAME 16384UL
/* Frame header8u32: magic,version,tic,total,worldbytes,actorbytes,status,hash.
 * Camera32 at32; player24u32 at64; psprites2*16 at160; input echo16 at192.
 * Blobs start256: one complete S2b world and one complete S2c actor frame.
 * Input16: magic32,expected tic32,forward8,side8,turn16,buttons16,stop16.
 * Each completed swap gives MD the sub's previous state and sub its next cmd. */
#endif
