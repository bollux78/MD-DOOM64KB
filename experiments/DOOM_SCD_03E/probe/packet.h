#ifndef SCD_PACKET_H
#define SCD_PACKET_H

#include <stdint.h>

enum {
    SCD_FRAME_BYTES = 3344,
    SCD_STRIDE = 152,
    SCD_MAX_ROWS = 44,
    SCD_MAX_COLUMNS = 256,
    SCD_MAX_LUTS = 64,
    SCD_FLAT = 0xffff
};

typedef struct {
    uint16_t offset, phase, step, rows, odd, lut;
    uint8_t source[128];
} ScdColumn;

typedef struct {
    uint16_t sequence, columns, luts, reserved;
    uint16_t frame[SCD_FRAME_BYTES / 2];
    ScdColumn column[SCD_MAX_COLUMNS];
    uint32_t lut_key[SCD_MAX_LUTS];
    uint8_t lut[SCD_MAX_LUTS][256];
} ScdPacket;

_Static_assert(sizeof(ScdPacket) <= 128UL * 1024, "packet exceeds Word RAM bank");

#endif
