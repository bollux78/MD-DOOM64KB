/* Experiment: two banks of complete 8x8 BG A patterns, four 4x4 samples each.
 * The default Pair-V renderer supplies the indices. Both experiment builds
 * pack them into the same single PAL0 tile and use the same viewport and HUD. */
enum { RAW_X = 5, RAW_Y = 5, RAW_W = 29, RAW_H = 13, RAW_N = RAW_W * RAW_H,
       RAW_BASE = 16, RAW_HASH_SIZE = 512, RAW_MISSING = 0xffff };

typedef struct {
    uint16_t map[RAW_N];
#if R128_RAW_CACHE
    uint16_t keys[2][RAW_N];
    uint16_t resident[2];
    uint16_t hash[RAW_HASH_SIZE]; /* slot + 1; zero means empty */
    uint8_t pinned[(RAW_N + 7) / 8];
#endif
} R128RawWork;

_Static_assert(sizeof(R128RawWork) <= R22_FB_BYTES, "raw BG scratch exceeds the spare framebuffer");
_Static_assert(RAW_BASE + 2 * RAW_N <= 800, "raw BG banks overlap the HUD");

static uint8_t raw_active, raw_pending, raw_front;
static R57ViewConfig raw_saved_view;
static uint32_t raw_uploads __attribute__((section(".data"))) = 0;
volatile uint32_t r128_raw_presented __attribute__((used, externally_visible, section(".data"))) = 0;

uint32_t R128_RawUploads(void) { return raw_uploads; }
uint32_t R128_RawFrames(void) { return r128_raw_presented; }

static void R128_RawBegin(void)
{
    const bool want = _g_timingdemo && _g_gamestate == GS_LEVEL;
    if (want == raw_active) return;
    R20_StopVideo();
    if (want) {
        raw_saved_view = r57_view;
        r57_view = R57_ViewMake(0, 32, 32);
        r57_was_level = 0;
        raw_front = 1;
        raw_uploads = 0;
        r128_raw_presented = 0;
#if R128_RAW_CACHE
        if (r115_fb2) {
            R128RawWork *const work = (R128RawWork *)(void *)r115_fb2;
            work->resident[0] = work->resident[1] = 0;
        }
#endif
        VDP_clearPlane(BG_B, TRUE);
        VDP_waitDMACompletion();
    } else {
        r57_view = raw_saved_view;
        r57_was_level = 0;
        if (r35_native_active < 0) R47_LoadPairTiles();
    }
    raw_active = want;
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

#if R128_RAW_CACHE
static inline uint16_t R128_RawBucket(const R128RawWork *work, const uint16_t *keys, uint16_t key)
{
    uint16_t bucket = (key ^ (key >> 7) ^ (key << 5)) & (RAW_HASH_SIZE - 1u);
    while (work->hash[bucket] && keys[work->hash[bucket] - 1u] != key)
        bucket = (bucket + 1u) & (RAW_HASH_SIZE - 1u);
    return bucket;
}
static inline void R128_RawPin(R128RawWork *work, uint16_t slot)
{
    work->pinned[slot >> 3] |= (uint8_t)(1u << (slot & 7u));
}
#endif

static void R128_RawPrepare(void)
{
    if (!r115_fb2) I_Error("Raw BG requires the E1M1 spare framebuffer");
    R128RawWork *const work = (R128RawWork *)(void *)r115_fb2;
    const uint16_t bank = raw_front ^ 1u, base = RAW_BASE + bank * RAW_N;
    /* Byte +1 is the two palette indices, independent of tile attributes. */
    const uint8_t *const start = r115_draw + RAW_Y * 152u + RAW_X * 2u + 1u;
#if R128_RAW_CACHE
    uint16_t *const keys = work->keys[bank];
    memset(work->hash, 0, sizeof(work->hash));
    memset(work->pinned, 0, sizeof(work->pinned));
    for (uint16_t i = 0; i < work->resident[bank]; ++i)
        work->hash[R128_RawBucket(work, keys, keys[i])] = i + 1u;

    /* Pin all hits before replacing a slot. This keeps a tile available even
     * when the next frame uses it at a different map position. */
    uint16_t *map = work->map;
    const uint8_t *row = start;
    for (uint16_t y = 0; y < RAW_H; ++y, row += 152u) {
        for (uint16_t x = 0; x < RAW_W; ++x) {
            const uint16_t key = R128_RawKey(row, x);
            const uint16_t entry = work->hash[R128_RawBucket(work, keys, key)];
            if (entry) {
                R128_RawPin(work, entry - 1u);
                *map++ = base + entry - 1u;
            } else {
                *map++ = RAW_MISSING;
            }
        }
    }

    /* The second hash contains only newly uploaded patterns, so replacement
     * never leaves stale hash entries. Equal misses share the first upload. */
    memset(work->hash, 0, sizeof(work->hash));
    uint16_t slot = 0, uploads = 0;
    map = work->map;
    row = start;
    for (uint16_t y = 0; y < RAW_H; ++y, row += 152u) {
        for (uint16_t x = 0; x < RAW_W; ++x, ++map) {
            if (*map != RAW_MISSING) continue;
            const uint16_t key = R128_RawKey(row, x);
            const uint16_t bucket = R128_RawBucket(work, keys, key);
            uint16_t entry = work->hash[bucket];
            if (!entry) {
                while (work->pinned[slot >> 3] & (1u << (slot & 7u))) ++slot;
                entry = slot + 1u;
                if (entry > work->resident[bank]) work->resident[bank] = entry;
                keys[slot] = key;
                work->hash[bucket] = entry;
                R128_RawUpload(base + slot, key);
                ++slot;
                ++uploads;
            }
            *map = base + entry - 1u;
        }
    }
    raw_uploads += uploads;
#else
    uint16_t i = 0;
    const uint8_t *row = start;
    for (uint16_t y = 0; y < RAW_H; ++y, row += 152u) {
        for (uint16_t x = 0; x < RAW_W; ++x, ++i) {
            work->map[i] = base + i;
            R128_RawUpload(base + i, R128_RawKey(row, x));
        }
    }
    raw_uploads += RAW_N;
#endif
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
    ++r128_raw_presented;
}
