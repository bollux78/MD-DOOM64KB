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
        if (column->lut == SCD_FLAT)
        {
            uint8_t shade = column->step;
            if (shade > 15)
                return 3;
            if (odd)
            {
                *dst = (*dst & 0xf0u) | shade;
                dst += SCD_STRIDE;
                --rows;
            }
            for (uint16_t pairs = rows >> 1; pairs; --pairs, dst += SCD_STRIDE)
                *dst = (shade << 4) | shade;
            if (rows & 1u)
                *dst = (*dst & 0x0fu) | (shade << 4);
        }
        else
        {
            if (column->lut >= packet->luts)
                return 4;
            R60_WallDraw(dst, column->source, packet->lut[column->lut],
                         column->phase, column->step, rows, odd);
        }
    }
    return 0;
}
