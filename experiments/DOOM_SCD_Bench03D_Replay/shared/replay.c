#include <stdint.h>

extern const uint8_t scd_fixture[];
extern void scd_wall(uint8_t *, const uint8_t *, const uint8_t *, uint32_t, uint32_t,
                     uint32_t, uint32_t);

typedef struct {
    uint16_t offset, phase, step, texture, lut;
    uint8_t count, flags, before[23], after[23];
} Command;
_Static_assert(sizeof(Command) == 58, "fixture command layout");

uint32_t scd_replay(uint32_t index, uint8_t *output, uint32_t verify)
{
    const uint32_t *header = (const uint32_t *)scd_fixture;
    const uint8_t *textures = scd_fixture + header[0];
    const uint32_t *luts = (const uint32_t *)(scd_fixture + header[1]);
    const uint8_t *frame = scd_fixture + header[2 + index];
    const uint16_t count = ((const uint16_t *)frame)[1];
    const uint8_t *reference = frame + 4;
    const uint8_t *mask = reference + 3344;
    const Command *command = (const Command *)(mask + 3344);

    uint8_t replayed[3344];
    if (verify)
        for (uint16_t i = 0; i < 3344; i++) replayed[i] = 0;

    for (uint16_t n = 0; n < count; n++, command++)
    {
        uint8_t *dst = output + command->offset;
        const uint16_t words = (command->count + (command->flags & 1) + 1) / 2;
        if (verify)
        {
            for (uint16_t i = 0; i < words; i++)
                dst[i * 152u] = command->before[i];
        }
        scd_wall(dst, textures + 128u * command->texture,
                 scd_fixture + luts[command->lut], command->phase,
                 command->step, command->count, command->flags);
        if (verify)
        {
            for (uint16_t i = 0; i < words; i++)
                if (dst[i * 152u] != command->after[i])
                    return n + 1u;
            for (uint16_t row = 0; row < command->count; row++)
            {
                const uint16_t y = row + (command->flags & 1u);
                const uint16_t pos = command->offset + 152u * (y / 2u);
                const uint8_t nibble = (y & 1u) ? 0x0fu : 0xf0u;
                replayed[pos] = (replayed[pos] & ~nibble) | (output[pos] & nibble);
            }
        }
    }

    if (verify)
    {
        /* Preserve the last written nibble independently of any captured
           pre-call byte used by a later kernel touching the other nibble. */
        for (uint16_t i = 0; i < 3344; i++)
            output[i] = (replayed[i] & mask[i]) | (reference[i] & ~mask[i]);
        for (uint16_t i = 0; i < 3344; i++)
            if (output[i] != reference[i])
                return 0x8000u + i;
    }
    return 0;
}
