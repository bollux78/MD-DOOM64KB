#include "packet.h"
#include "r60_pair_wall.h"

uint32_t scd_render_world(ScdPacket *packet, uint32_t sequence)
{
    if (packet->sequence != sequence ||
        packet->columns > SCD_MAX_COLUMNS || packet->luts > SCD_MAX_LUTS)
        return 1;

    for (uint16_t i = 0; i < packet->columns; ++i)
    {
        const ScdColumn *column = &packet->column[i];
        uint16_t rows = column->rows, odd = column->odd;
        if (!rows || rows > SCD_MAX_ROWS || odd > 1 ||
            column->offset + SCD_STRIDE * ((rows + odd - 1u) >> 1) >= SCD_FRAME_BYTES)
            return 2;
        uint8_t *dst = (uint8_t *)packet->frame + column->offset;
        if ((column->lut >= packet->luts && column->lut < SCD_MAX_LUTS) ||
            column->lut >= SCD_MAX_LUTS + SCD_RESIDENT_LUTS ||
            column->source_slot > i)
            return 4;
        R60_WallDraw(dst, packet->source[column->source_slot], packet->lut[column->lut],
                     column->phase, column->step, rows, odd);
    }
    return 0;
}
