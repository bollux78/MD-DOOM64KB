/* S2a wire: fixed 32-bit big-endian words, never native engine pointers.
 * Camera replay only; local MD actors/doors remain at initial state. */
#ifndef S2A_CAMERA_WIRE_H
#define S2A_CAMERA_WIRE_H
#include <stdint.h>
#define S2A_CAMERA_MAGIC 0x53324341UL
#define S2A_META_MAGIC 0x53324142UL
#define S2A_CAMERA_COUNT 27u
#define S2A_CAMERA_WORDS 8u
#define S2A_CAMERA_BYTES 32u
#define S2A_SUB_CAMERA 0x7C400UL
#define S2A_SUB_META 0x7C780UL
#define S2A_MD_CAMERA 0x61A000UL
#define S2A_MD_META 0x61A380UL
#define S2A_MD_REPORT 0x61B000UL
/* [magic,tic,x,y,z,angle,viewz,health]; metadata [magic,count,stride,hash]. */
#endif
