/* Pixel4 presentation: one full 8x8 pattern per cell, always using PAL0. */
enum { RAW_X = 5, RAW_Y = 5, RAW_W = 29, RAW_H = 13, RAW_N = RAW_W * RAW_H,
       RAW_BASE = 16 };

typedef struct { uint16_t map[RAW_N]; } R128RawWork;

_Static_assert(RAW_BASE + 2 * RAW_N <= 800, "Pixel4 banks overlap the HUD");
static uint8_t raw_active, raw_pending, raw_front;

static void R128_RawBegin(void)
{
    const bool want = _g_gamestate == GS_LEVEL;
    if (want == raw_active) return;
    R20_StopVideo();
    raw_active = want;
    if (want) {
        r57_view = R57_ViewMake(0, 32, 32);
        r57_was_level = 0;
        raw_front = 1;
        VDP_clearPlane(BG_B, TRUE);
        VDP_waitDMACompletion();
        R22_Palette(0);
    }
}

static inline uint16_t R128_RawKey(const uint8_t *row, uint16_t x)
{
    const uint8_t *a = row + 2u * x;
    return (uint16_t)((uint16_t)a[0] << 8) | a[76];
}

static void R128_RawUpload(uint16_t index, uint16_t key)
{
    const uint8_t a = key >> 8, b = key;
    const uint32_t top = R22_ExpandPair((a & 0xf0u) | (b >> 4));
    const uint32_t bottom = R22_ExpandPair((a << 4) | (b & 15u));
    volatile uint32_t *const ctrl = (volatile uint32_t *)0xc00004;
    volatile uint32_t *const data = (volatile uint32_t *)0xc00000;
    const uint16_t sr = R22_Lock();
    VDP_setAutoInc(2);
    *ctrl = VDP_WRITE_VRAM_ADDR(index * 32u);
    *data = top; *data = top; *data = top; *data = top;
    *data = bottom; *data = bottom; *data = bottom; *data = bottom;
    R22_Unlock(sr);
}

static void R128_RawPrepare(void)
{
    R128RawWork *const work = (R128RawWork *)(void *)r115_fb2;
    const uint16_t bank = raw_front ^ 1u, base = RAW_BASE + bank * RAW_N;
    const uint8_t *row = r115_draw + RAW_Y * 152u + RAW_X * 2u + 1u;
    struct { uint16_t key, tile; } cache[64] = {0};
    uint16_t i = 0;
    for (uint16_t y = 0; y < RAW_H; ++y, row += 152u) {
        for (uint16_t x = 0; x < RAW_W; ++x, ++i) {
            const uint16_t key = R128_RawKey(row, x);
            const uint16_t bucket = (key ^ (key >> 6) ^ (key >> 12)) & 63u;
            if (cache[bucket].tile && cache[bucket].key == key) {
                work->map[i] = cache[bucket].tile;
                continue;
            }
            const uint16_t tile = base + i;
            R128_RawUpload(tile, key);
            cache[bucket].key = key;
            cache[bucket].tile = tile;
            work->map[i] = tile;
        }
    }
    raw_pending = 1;
}

static void R128_RawPresent(volatile uint16_t *ctrl)
{
    const R128RawWork *work = (const R128RawWork *)(const void *)r115_fb2;
    uint32_t source = ((uint32_t)(uintptr_t)work->map) >> 1;
    uint16_t dest = VDP_BG_A + RAW_Y * 128u + RAW_X * 2u;
    *ctrl = 0x9400;
    *ctrl = 0x9700 | ((source >> 16) & 127u);
    for (uint16_t y = 0; y < RAW_H; ++y, source += RAW_W, dest += 128u) {
        *ctrl = 0x9300 | RAW_W;
        *ctrl = 0x9500 | (source & 255u);
        *ctrl = 0x9600 | ((source >> 8) & 255u);
        volatile uint32_t command = VDP_DMA_VRAM_ADDR(dest);
        volatile uint16_t *words = (volatile uint16_t *)&command;
        *ctrl = words[0];
        __asm__ volatile("move.w %0,(%1)"::"m"(words[1]),"a"(ctrl):"cc","memory");
    }
    raw_front ^= 1u;
    raw_pending = 0;
}
