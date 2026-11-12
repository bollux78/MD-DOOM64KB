#include "nexus.h"
#include <genesis.h>

enum {
    TILE_COUNT = NX_WIDTH * NX_HEIGHT / 64,
    VIEW_X = 12, VIEW_Y = 7, RUN_SAMPLES = 39
};

extern const NxMap nexus_map;
extern const NxCamera nexus_cameras[];
extern const unsigned int nexus_camera_count;

static uint8_t linear[NX_WIDTH * NX_HEIGHT];
static uint32_t packed[NX_TILE_BYTES / 4];
static uint16_t tilemap[2][TILE_COUNT];
static unsigned displayed = 1;

typedef struct {
    u32 draw, pack, wait, dma, frame;
} Timing;

static Timing show(unsigned pose, int layout)
{
    Timing time;
    u32 start = getSubTick();
    uint8_t *tiles = (uint8_t *)packed;
    nx_render(&nexus_map, &nexus_cameras[pose], layout == NX_LINEAR ? linear : tiles, layout);
    u32 drawn = getSubTick();
    if (layout == NX_LINEAR)
        nx_pack(linear, tiles);
    u32 ready = getSubTick();

    unsigned bank = displayed ^ 1;
    SYS_doVBlankProcessEx(ON_VBLANK_START);
    u32 blank = getSubTick();
    VDP_loadTileData(packed, TILE_USER_INDEX + bank * TILE_COUNT, TILE_COUNT, DMA);
    VDP_setTileMapDataRect(BG_A, tilemap[bank], VIEW_X, VIEW_Y,
                          NX_WIDTH / 8, NX_HEIGHT / 8, NX_WIDTH / 8, DMA);
    DMA_waitCompletion();
    displayed = bank;
    u32 done = getSubTick();

    time.draw = drawn - start;
    time.pack = layout == NX_LINEAR ? ready - drawn : 0;
    time.wait = blank - ready;
    time.dma = done - blank;
    time.frame = done - start;
    return time;
}

static unsigned millis(u32 subticks)
{
    return (subticks + 38) / 77;
}

static void value(unsigned n, unsigned x, unsigned y)
{
    char text[9];
    uintToStr(n, text, 4);
    VDP_drawText(text, x, y);
}

static void show_timing(Timing t, unsigned pose, int layout)
{
    SYS_doVBlankProcess();
    VDP_drawText(layout == NX_LINEAR ? "A LINEAR+PACK  POSE" : "B DIRECT TILES POSE", 3, 3);
    value(pose, 24, 3);
    VDP_drawText("DRAW PACK WAIT DMA  TOTAL (ms)", 3, 21);
    value(millis(t.draw), 3, 22);
    value(millis(t.pack), 8, 22);
    value(millis(t.wait), 13, 22);
    value(millis(t.dma), 18, 22);
    value(millis(t.frame), 23, 22);
}

static void sort(u32 *values)
{
    for (unsigned i = 1; i < RUN_SAMPLES; ++i) {
        u32 current = values[i];
        unsigned j = i;
        while (j && values[j - 1] > current) {
            values[j] = values[j - 1];
            --j;
        }
        values[j] = current;
    }
}

static void benchmark(void)
{
    u32 frames[2][RUN_SAMPLES];
    for (unsigned i = 0; i < RUN_SAMPLES; ++i) {
        unsigned pose = i % nexus_camera_count;
        int first = i & 1;
        frames[first][i] = show(pose, first).frame;
        frames[first ^ 1][i] = show(pose, first ^ 1).frame;
    }

    SYS_doVBlankProcess();
    VDP_drawText("A/B 39 FRAMES EACH (ms)             ", 3, 3);
    VDP_drawText("       MED  P95  MAX                ", 3, 21);
    VDP_drawText("A                                   ", 3, 22);
    VDP_drawText("B", 3, 23);
    for (int layout = 0; layout < 2; ++layout) {
        sort(frames[layout]);
        value(millis(frames[layout][19]), 10, 22 + layout);
        value(millis(frames[layout][37]), 15, 22 + layout);
        value(millis(frames[layout][38]), 20, 22 + layout);
    }
}

int main(bool hard_reset)
{
    (void)hard_reset;
    static const u16 colors[16] = {
        0x000, 0x844, 0x246, 0x08e, 0x04c, 0x26a, 0x48c, 0xe0e
    };
    VDP_setScreenWidth320();
    PAL_setPalette(PAL1, colors, CPU);
    VDP_setTextPlane(BG_B);
    VDP_drawText("NEXUS N01   E1M1", 3, 1);
    VDP_drawText("LEFT/RIGHT pose  A/B layout  C run", 3, 26);

    for (unsigned bank = 0; bank < 2; ++bank)
        for (unsigned i = 0; i < TILE_COUNT; ++i)
            tilemap[bank][i] = TILE_ATTR_FULL(PAL1, 0, 0, 0, TILE_USER_INDEX + bank * TILE_COUNT + i);

    unsigned pose = 0;
    int layout = NX_TILES;
    show_timing(show(pose, layout), pose, layout);
    u16 previous = 0;
    for (;;) {
        SYS_doVBlankProcess();
        u16 held = JOY_readJoypad(JOY_1);
        u16 pressed = held & ~previous;
        previous = held;
        if (pressed & BUTTON_C) {
            benchmark();
            continue;
        }
        if (pressed & BUTTON_LEFT)
            pose = (pose + nexus_camera_count - 1) % nexus_camera_count;
        if (pressed & BUTTON_RIGHT)
            pose = (pose + 1) % nexus_camera_count;
        if (pressed & BUTTON_A)
            layout = NX_LINEAR;
        if (pressed & BUTTON_B)
            layout = NX_TILES;
        if (pressed & (BUTTON_LEFT | BUTTON_RIGHT | BUTTON_A | BUTTON_B)) {
            VDP_drawText("                                    ", 3, 23);
            VDP_drawText("                                    ", 3, 3);
            VDP_drawText("                                    ", 3, 22);
            show_timing(show(pose, layout), pose, layout);
        }
    }
}
