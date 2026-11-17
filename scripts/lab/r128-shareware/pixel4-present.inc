/* R22 viewport: 38 by 21 hardware tiles, with the original top guard row.
 * Front and back normally use separate dictionaries of distinct patterns.
 * Overflow uses a full-sized bank with the display blanked during the upload. */
enum { P4_COLS = 38, P4_ROWS = 21, P4_COUNT = P4_COLS * P4_ROWS,
       P4_BASE = 16, P4_BANK = P4_COUNT / 2, P4_HASH = 512,
       P4_IMAGE = 38 * 44, P4_MISSING = 0xffff };
typedef struct { uint16_t slots[P4_HASH], keys[P4_BANK]; } Pixel4Cache;
_Static_assert(P4_BASE + P4_COUNT <= HUDW_VRAM_BASE, "Pixel4 patterns overlap HUD");
_Static_assert(P4_IMAGE + P4_COUNT * 2 <= R22_FB_BYTES, "Pixel4 buffers do not fit");
static uint8_t pixel4_active, pixel4_pending, pixel4_front, pixel4_full;
volatile uint32_t pixel4_overflows __attribute__((used, externally_visible, section(".data"))) = 0;

static uint16_t *Pixel4_Map(void) { return (uint16_t *)(void *)(r22_fb.pixels + P4_IMAGE); }

static void Pixel4_Begin(void)
{
    const bool want = _g_gamestate == GS_LEVEL;
    if (want == pixel4_active) return;
    R20_StopVideo();
    pixel4_active = want;
    if (want) {
        r57_view = R57_ViewMake(0, 0, 0);
        r57_was_level = 0;
        pixel4_front = 1;
        pixel4_full = 0;
        memset(r22_fb.pixels, 0, P4_IMAGE);
        VDP_clearPlane(BG_B, TRUE);
        VDP_waitDMACompletion();
        R22_Palette(0);
    }
}

static uint16_t Pixel4_Key(uint16_t i)
{
    const uint16_t row = i / P4_COLS, x = i % P4_COLS;
    const uint8_t *p = r22_fb.pixels + (row + 1u) * (2u * P4_COLS) + x;
    return (uint16_t)((uint16_t)p[0] << 8) | p[P4_COLS];
}

static void Pixel4_Upload(uint16_t slot, uint16_t key)
{
    const uint32_t top = R22_ExpandPair((uint8_t)(key >> 8));
    const uint32_t bottom = R22_ExpandPair((uint8_t)key);
    volatile uint32_t *const ctrl = (volatile uint32_t *)0xc00004;
    volatile uint32_t *const data = (volatile uint32_t *)0xc00000;
    const uint16_t sr = R22_Lock();
    VDP_setAutoInc(2);
    *ctrl = VDP_WRITE_VRAM_ADDR(slot * 32u);
    *data = top; *data = top; *data = top; *data = top;
    *data = bottom; *data = bottom; *data = bottom; *data = bottom;
    R22_Unlock(sr);
}

static void Pixel4_Prepare(void)
{
    Pixel4Cache *const cache = (Pixel4Cache *)(void *)r115_fb2;
    uint16_t *const map = Pixel4_Map();
    const uint16_t base = P4_BASE + (pixel4_front ^ 1u) * P4_BANK;
    uint16_t count = 0;
    // Tile indices are decided before VRAM uploads, so fallback is atomic.
    memset(cache->slots, 0, sizeof(cache->slots));
    for (uint16_t i = 0; i < P4_COUNT; ++i) {
        const uint16_t key = Pixel4_Key(i);
        const uint16_t solid = R22_TileIndex(key >> 8, (uint8_t)key, P4_MISSING);
        if (solid != P4_MISSING) { map[i] = solid; continue; }
        uint16_t j = (key ^ (key >> 7) ^ (key << 5)) & (P4_HASH - 1u);
        while (cache->slots[j] && cache->keys[cache->slots[j] - 1u] != key)
            j = (j + 1u) & (P4_HASH - 1u);
        if (!cache->slots[j]) {
            if (count == P4_BANK) goto full;
            cache->keys[count++] = key;
            cache->slots[j] = count;
        }
        map[i] = base + cache->slots[j] - 1u;
    }
    if (pixel4_full) VDP_setEnable(FALSE);
    for (uint16_t j = 0; j < count; ++j) Pixel4_Upload(base + j, cache->keys[j]);
    pixel4_pending = pixel4_full ? 2 : 1;
    pixel4_full = 0;
    return;

full:
    VDP_setEnable(FALSE);
    for (uint16_t i = 0; i < P4_COUNT; ++i) {
        const uint16_t key = Pixel4_Key(i);
        const uint16_t tile = R22_TileIndex(key >> 8, (uint8_t)key, P4_BASE + i);
        map[i] = tile;
        if (tile >= P4_BASE) Pixel4_Upload(tile, key);
    }
    ++pixel4_overflows;
    pixel4_full = 1;
    pixel4_pending = 2;
}

static void Pixel4_Present(volatile uint16_t *ctrl)
{
    uint32_t source = ((uint32_t)(uintptr_t)Pixel4_Map()) >> 1;
    uint16_t dest = VDP_BG_A + 128u;
    *ctrl = 0x9400;
    *ctrl = 0x9700 | ((source >> 16) & 127u);
    for (uint16_t y = 0; y < P4_ROWS; ++y, source += P4_COLS, dest += 128u) {
        *ctrl = 0x9300 | P4_COLS;
        *ctrl = 0x9500 | (source & 255u);
        *ctrl = 0x9600 | ((source >> 8) & 255u);
        volatile uint32_t command = VDP_DMA_VRAM_ADDR(dest);
        volatile uint16_t *words = (volatile uint16_t *)&command;
        *ctrl = words[0];
        __asm__ volatile("move.w %0,(%1)"::"m"(words[1]),"a"(ctrl):"cc","memory");
    }
    if (pixel4_pending == 2) VDP_setEnable(TRUE);
    pixel4_front ^= 1u;
    pixel4_pending = 0;
}
