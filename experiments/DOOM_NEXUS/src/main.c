#include "nexus.h"
#include <genesis.h>

enum {
    TILE_COUNT = NX_VIEW_WIDTH * NX_VIEW_HEIGHT / 64,
    VIEW_X = (320 - NX_VIEW_WIDTH) / 16,
    VIEW_Y = (200 - NX_VIEW_HEIGHT) / 16, RUN_SAMPLES = 39
};

extern const NxMap nexus_map;
#ifndef NX_WIREFRAME_ROM
extern const uint16_t nexus_palette[16];
#endif
#ifdef NX_LINE_TEST
extern const uint16_t nexus_wall_seg;
extern const NxCamera nexus_wall_camera;
#endif
extern const char nexus_map_name[];
extern const NxCamera nexus_cameras[];
extern const unsigned int nexus_camera_count;

_Alignas(4) static uint8_t linear[NX_WIDTH * NX_HEIGHT];
static uint32_t packed[NX_TILE_BYTES / 4];
static unsigned displayed = 1;
#ifdef NX_2X2
enum { SOLID_COLORS = 16, DMA_SAFE_BYTES = 6800, DMA_CHUNK = 200 };
static uint16_t mixed_map[TILE_COUNT];
static unsigned solid_base(void)
{
    return TILE_USER_INDEX + 2 * TILE_COUNT;
}
#endif

typedef struct {
    u32 draw, pack, wait, dma, frame;
} Timing;

static Timing show(const NxCamera *camera, int mode, int scene)
{
    Timing time;
    u32 start = getSubTick();
#ifdef NX_WIREFRAME_ROM
    (void)mode;
    (void)scene;
    nx_render_wire(&nexus_map, camera, linear);
#elif defined(NX_LINE_TEST)
    NxMap single = nexus_map;
    NxLeaf leaf = {nexus_wall_seg, 1};
    if (scene == 2) {
        single.root = 0x8000;
        single.leaves = &leaf;
    }
    nx_render_walls(scene == 2 ? &single : &nexus_map, camera, linear, mode);
#else
    (void)scene;
    nx_render_walls(&nexus_map, camera, linear, mode);
#endif
    u32 drawn = getSubTick();
    unsigned bank = displayed ^ 1;
    unsigned base = TILE_USER_INDEX + bank * TILE_COUNT;
    unsigned count = nx_pack_mixed(linear, (uint8_t *)packed, mixed_map,
                       TILE_ATTR_FULL(PAL1, 0, 0, 0, base),
                       TILE_ATTR_FULL(PAL1, 0, 0, 0, solid_base()));
    u32 ready = getSubTick();
    unsigned sent = 0;
    const unsigned last_capacity = (DMA_SAFE_BYTES - TILE_COUNT * 2) / 32;
    time.wait = 0;
    time.dma = 0;
    u32 previous = ready;
    while (count - sent > last_capacity) {
        unsigned chunk = count - sent - last_capacity;
        if (chunk > DMA_CHUNK)
            chunk = DMA_CHUNK;
        SYS_doVBlankProcessEx(ON_VBLANK_START);
        u32 blank = getSubTick();
        VDP_loadTileData(packed + sent * 8, base + sent, chunk, DMA);
        DMA_waitCompletion();
        u32 done = getSubTick();
        time.wait += blank - previous;
        time.dma += done - blank;
        previous = done;
        sent += chunk;
    }
    SYS_doVBlankProcessEx(ON_VBLANK_START);
    u32 blank = getSubTick();
    if (count > sent)
        VDP_loadTileData(packed + sent * 8, base + sent, count - sent, DMA);
    VDP_setTileMapDataRect(BG_A, mixed_map, VIEW_X, VIEW_Y,
                          NX_VIEW_WIDTH / 8, NX_VIEW_HEIGHT / 8, NX_VIEW_WIDTH / 8, DMA);
    DMA_waitCompletion();
    displayed = bank;
    u32 done = getSubTick();
    time.draw = drawn - start;
    time.pack = ready - drawn;
    time.wait += blank - previous;
    time.dma += done - blank;
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

#if defined(NX_UV_INCREMENTAL) && defined(NX_RECIP_LUT) && defined(NX_COLUMN_ASM)
#define VARIANT_NAME "ALL"
#elif defined(NX_UV_INCREMENTAL)
#define VARIANT_NAME "UV"
#elif defined(NX_RECIP_LUT)
#define VARIANT_NAME "LUT"
#elif defined(NX_COLUMN_ASM)
#define VARIANT_NAME "ASM"
#else
#define VARIANT_NAME "BASE"
#endif

#ifdef NX_WIREFRAME_ROM
enum { BENCH_MODES = 1 };
static const char *const mode_name[] = {"WIREFRAME"};
#else
enum { BENCH_MODES = NX_MODE_COUNT };
static const char *const mode_name[] = {"FLAT", "PERSPECTIVE", "STRIPS",
#ifdef NX_LINE_TEST
                                        "OUTLINE",
#endif
};
#endif

static void show_timing(Timing t, unsigned pose, int mode, int free_camera, int scene)
{
    SYS_doVBlankProcess();
    VDP_clearText(0, 0, 40);
    VDP_drawText("NEXUS", 1, 0);
    VDP_drawText(nexus_map_name, 8, 0);
#ifdef NX_LINE_TEST
    if (scene)
        VDP_drawText(scene == 1 ? "MAP WALL" : "ONE SEG", 25, 0);
#else
    (void)scene;
#ifndef NX_WIREFRAME_ROM
    VDP_drawText(VARIANT_NAME, 28, 0);
#endif
#endif
    VDP_drawText(mode_name[mode], 15, 0);
    if (free_camera)
        VDP_drawText("FREE", 33, 0);
    else
        value(pose, 34, 0);
    VDP_clearTextArea(0, 25, 40, 3);
    VDP_drawText("DRAW PACK WAIT DMA  TOTAL (ms)", 1, 25);
    value(millis(t.draw), 1, 26);
    value(millis(t.pack), 6, 26);
    value(millis(t.wait), 11, 26);
    value(millis(t.dma), 16, 26);
    value(millis(t.frame), 21, 26);
#ifdef NX_WIREFRAME_ROM
    VDP_drawText("LEFT/RIGHT POSES  C BENCH  START CAM", 1, 27);
#elif defined(NX_LINE_TEST)
    VDP_drawText("A FLAT/LINE  B TEX  UP WALL  C BENCH", 1, 27);
#else
    VDP_drawText("A FLAT  B TEXTURES  C BENCH  START CAM", 1, 27);
#endif
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
    u32 frames[BENCH_MODES][RUN_SAMPLES];
    for (unsigned i = 0; i < RUN_SAMPLES; ++i) {
        unsigned pose = i % nexus_camera_count;
        for (unsigned j = 0; j < BENCH_MODES; ++j) {
            unsigned mode = (i + j) % BENCH_MODES;
            frames[mode][i] = show(&nexus_cameras[pose], mode, 0).frame;
        }
    }
    SYS_doVBlankProcess();
    VDP_clearText(0, 0, 40);
    VDP_drawText("BENCH (ms)      MED   P95   MAX", 1, 0);
#if !defined(NX_LINE_TEST) && !defined(NX_WIREFRAME_ROM)
    VDP_drawText(VARIANT_NAME, 35, 0);
#endif
    VDP_clearTextArea(0, 24, 40, 4);
    for (unsigned mode = 0; mode < BENCH_MODES; ++mode) {
        unsigned row = 24 + mode;
        sort(frames[mode]);
        VDP_drawText(mode_name[mode], 1, row);
        value(millis(frames[mode][19]), 17, row);
        value(millis(frames[mode][37]), 23, row);
        value(millis(frames[mode][38]), 29, row);
    }
}

#ifdef NX_LINE_TEST
static void benchmark_wall(void)
{
    u32 draw[2][RUN_SAMPLES], frames[2][RUN_SAMPLES];
    for (unsigned i = 0; i < RUN_SAMPLES; ++i) {
        for (unsigned j = 0; j < 2; ++j) {
            unsigned scene = (i + j) & 1;
            Timing result = show(&nexus_wall_camera, NX_FLAT, scene + 1);
            draw[scene][i] = result.draw;
            frames[scene][i] = result.frame;
        }
    }
    SYS_doVBlankProcess();
    VDP_clearText(0, 0, 40);
    VDP_drawText("ONE WALL TEST (ms)", 1, 0);
    VDP_clearTextArea(0, 24, 40, 4);
    VDP_drawText("DRAW MED  FRAME MED  P95", 14, 24);
    for (unsigned scene = 0; scene < 2; ++scene) {
        unsigned row = 25 + scene;
        sort(draw[scene]);
        sort(frames[scene]);
        VDP_drawText(scene ? "ONE SEG" : "MAP WALL", 1, row);
        value(millis(draw[scene][19]), 15, row);
        value(millis(frames[scene][19]), 25, row);
        value(millis(frames[scene][37]), 35, row);
    }
}
#endif

enum { ANGLES = 32, MOVE_STEP = 12 };

static const int16_t sine[ANGLES] = {
    0, 50, 98, 142, 181, 213, 237, 251,
    256, 251, 237, 213, 181, 142, 98, 50,
    0, -50, -98, -142, -181, -213, -237, -251,
    -256, -251, -237, -213, -181, -142, -98, -50,
};

static int16_t cosine(unsigned angle)
{
    return sine[(angle + ANGLES / 4) & (ANGLES - 1)];
}

static unsigned nearest_angle(NxCamera camera)
{
    unsigned best = 0;
    int score = -131073;
    for (unsigned i = 0; i < ANGLES; ++i) {
        int dot = camera.cosine * cosine(i) + camera.sine * sine[i];
        if (dot > score) {
            score = dot;
            best = i;
        }
    }
    return best;
}

static int16_t move_axis(int16_t coordinate, int delta)
{
    int result = coordinate + delta;
    if (result < INT16_MIN)
        return INT16_MIN;
    if (result > INT16_MAX)
        return INT16_MAX;
    return result;
}

int main(bool hard_reset)
{
    (void)hard_reset;
    VDP_setScreenWidth320();
#ifdef NX_WIREFRAME_ROM
    static const u16 wire_palette[16] = {[15] = 0xEEE};
    PAL_setPalette(PAL1, wire_palette, CPU);
#else
    PAL_setPalette(PAL1, nexus_palette, CPU);
#endif
    VDP_setTextPlane(BG_B);
    if (solid_base() + SOLID_COLORS - 1 > TILE_USER_MAX_INDEX) {
        VDP_drawText("INSUFFICIENT VRAM FOR VIEWPORT", 2, 1);
        for (;;) SYS_doVBlankProcess();
    }

    /* Install the shared uniform tiles once, before either image bank is shown. */
    for (unsigned color = 0; color < SOLID_COLORS; ++color)
        for (unsigned i = 0; i < 8; ++i)
            packed[color * 8 + i] = UINT32_C(0x11111111) * color;
    SYS_doVBlankProcessEx(ON_VBLANK_START);
    VDP_loadTileData(packed, solid_base(), SOLID_COLORS, DMA);
    DMA_waitCompletion();

    unsigned pose = 0;
#if defined(NX_WIREFRAME_ROM) || defined(NX_LINE_TEST)
    int mode = NX_FLAT;
#else
    int mode = NX_PERSPECTIVE;
#endif
    int scene = 0;
    int free_camera = 0;
    unsigned angle = 0;
    NxCamera camera = nexus_cameras[pose];
    show_timing(show(&camera, mode, scene), pose, mode, free_camera, scene);
    u16 previous = 0;
    for (;;) {
        SYS_doVBlankProcess();
        u16 held = JOY_readJoypad(JOY_1);
        u16 pressed = held & ~previous;
        previous = held;
        if (pressed & BUTTON_C) {
#ifdef NX_LINE_TEST
            if (scene)
                benchmark_wall();
            else
#endif
                benchmark();
            continue;
        }
        int redraw = pressed & (BUTTON_START | BUTTON_A | BUTTON_B);
#ifndef NX_WIREFRAME_ROM
        if (pressed & BUTTON_A) {
#ifdef NX_LINE_TEST
            mode = mode == NX_FLAT ? NX_OUTLINE : NX_FLAT;
#else
            mode = NX_FLAT;
#endif
        }
        if (pressed & BUTTON_B)
            mode = mode == NX_PERSPECTIVE ? NX_STRIP : NX_PERSPECTIVE;
#endif
        if (pressed & BUTTON_START) {
            free_camera ^= 1;
            scene = 0;
            camera = nexus_cameras[pose];
            angle = nearest_angle(camera);
        }
        if (free_camera) {
            if (held & (BUTTON_LEFT | BUTTON_RIGHT | BUTTON_UP | BUTTON_DOWN)) {
                angle = (angle + !!(held & BUTTON_LEFT) - !!(held & BUTTON_RIGHT)) & (ANGLES - 1);
                camera.cosine = cosine(angle);
                camera.sine = sine[angle];
                int step = MOVE_STEP * (!!(held & BUTTON_UP) - !!(held & BUTTON_DOWN));
                camera.x = move_axis(camera.x, step * camera.cosine / 256);
                camera.y = move_axis(camera.y, step * camera.sine / 256);
                if (step)
                    nx_camera_floor(&nexus_map, &camera);
                redraw = 1;
            }
#ifdef NX_LINE_TEST
        } else if (pressed & BUTTON_UP) {
            scene = (scene + 1) % 3;
            camera = scene ? nexus_wall_camera : nexus_cameras[pose];
            redraw = 1;
#endif
        } else if (pressed & (BUTTON_LEFT | BUTTON_RIGHT)) {
            scene = 0;
            unsigned step = (pressed & BUTTON_LEFT) ? nexus_camera_count - 1 : 1;
            pose = (pose + step) % nexus_camera_count;
            camera = nexus_cameras[pose];
            redraw = 1;
        }
        if (redraw) {
            show_timing(show(&camera, mode, scene), pose, mode, free_camera, scene);
        }
    }
}
