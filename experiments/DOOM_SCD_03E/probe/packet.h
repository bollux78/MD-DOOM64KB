#ifndef SCD_PACKET_H
#define SCD_PACKET_H

#include <stdint.h>

enum {
    SCD_FRAME_BYTES = 3344,
    SCD_STRIDE = 152,
    SCD_MAX_ROWS = 44,
    SCD_MAX_COLUMNS = 32,
    SCD_BATCH_COLUMNS = SCD_MAX_COLUMNS,
    SCD_MAX_LUTS = 64,
    SCD_LUTS_PER_PARITY = 34,
    SCD_LUT_BANKS = 2,
    SCD_RESIDENT_LUTS = SCD_LUT_BANKS * SCD_LUTS_PER_PARITY
};

typedef struct {
    uint16_t offset, phase, step, rows, odd, lut, source_slot;
} ScdColumn;

typedef struct {
    uint16_t sequence, columns, luts, reserved;
    uint16_t frame[SCD_FRAME_BYTES / 2];
    ScdColumn column[SCD_MAX_COLUMNS];
    uint32_t lut_key[SCD_MAX_LUTS];
    uint8_t lut[SCD_MAX_LUTS + SCD_RESIDENT_LUTS][256];
    uint8_t source[SCD_MAX_COLUMNS][128];
    uint32_t lut_base[SCD_LUT_BANKS];
    uint32_t last_source;
    uint16_t last_slot, last_min, last_max;
} ScdPacket;

_Static_assert(sizeof(ScdPacket) <= 128UL * 1024, "packet exceeds Word RAM bank");

#endif
