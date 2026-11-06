#include <stdint.h>

extern const uint8_t scd_fixture[];
extern uint32_t scd_replay(uint32_t index, uint8_t *output, uint32_t verify);

const uint8_t *scene_reference(void)
{
    const uint32_t *offsets = (const uint32_t *)scd_fixture;
    return scd_fixture + offsets[2] + 4;
}

/* Two contiguous name-table spans, each with the VDP's 64-word pitch. */
void scene_render(uint16_t *planes)
{
    uint8_t raw[3344];
    const uint8_t *reference = scene_reference();
    const uint8_t *mask = reference + sizeof(raw);
    for (uint16_t i = 0; i < sizeof(raw); ++i)
        raw[i] = reference[i] & ~mask[i];
    scd_replay(0, raw, 0);
    for (uint16_t y = 0; y < 21; ++y)
        for (uint16_t plane = 0; plane < 2; ++plane)
        {
            const uint16_t from = (y + 1u) * 152u + plane * 76u;
            uint16_t *dst = planes + plane * 1344u + y * 64u;
            for (uint16_t x = 0; x < 38; ++x)
            {
                const uint16_t pos = from + x * 2u;
                const uint8_t color = (raw[pos + 1] & mask[pos + 1]) |
                                      (reference[pos + 1] & ~mask[pos + 1]);
                dst[x] = (uint16_t)reference[pos] << 8 | color;
            }
            for (uint16_t x = 38; x < 64; ++x)
                dst[x] = 0;
        }
    planes[2688] = 0; /* guard word for the Word RAM DMA workaround */
}
