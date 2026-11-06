#include <genesis.h>
#include <string.h>
#include "sub_program.h"
#include "../scene.h"

#define HW_VERSION (*(volatile const u8 *)0xA10001)
#define CD_BIOS_HEADER (*(volatile const u32 *)0x400100)
#define CD_SUB_BYTE (*(volatile u8 *)0xA12001)
#define CD_SUBCTRL (*(volatile const u16 *)0xA12000)
#define CD_MEMCTRL (*(volatile u16 *)0xA12002)
#define CD_MAIN_SEQ (*(volatile u16 *)0xA12010)
#define CD_MAIN_X (*(volatile u16 *)0xA12012)
#define CD_MAIN_Y (*(volatile u16 *)0xA12014)
#define CD_MAIN_HEADING (*(volatile u16 *)0xA12016)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_SUB_READY (*(volatile const u16 *)0xA12028)
#define CD_SUB_ACK (*(volatile const u16 *)0xA12026)
#define CD_PRGRAM ((volatile u16 *)0x420000)

#define SUB_READY 0x5343u
#define SUB_FAULT 0xDEADu
#define TIMEOUT_VBLANKS 60u
#define RENDER_TIMEOUT_VBLANKS 12u
#define SWAP_TIMEOUT_VBLANKS 6u
#define WORD_ID (*(volatile const u16 *)0x600000)
#define WORD_DATA ((volatile const u16 *)0x600020)
#define VDP_CTRL (*(volatile u32 *)0xc00004)
#define VDP_DATA (*(volatile u16 *)0xc00000)

_Static_assert(SUB_PROGRAM_WORDS > 0 && SUB_PROGRAM_WORDS <= 65536u,
               "Sub-CPU image must fit in one Program RAM bank");

static void number(const char *label, u32 value, u16 y)
{
    char line[40], digits[12];
    uintToStr(value, digits, 1);
    strcpy(line, label);
    strcat(line, digits);
    VDP_clearTextLine(y);
    VDP_drawText(line, 2, y);
}

static bool wait_sub(u8 mask, u8 expected)
{
    for (u16 frame = 0; frame < TIMEOUT_VBLANKS; frame++)
    {
        if ((CD_SUB_BYTE & mask) == expected)
            return TRUE;
        SYS_doVBlankProcess();
    }
    return FALSE;
}

static const char *boot_sub(void)
{
    /* Gate Array reset sequence for cartridge boot. */
    SYS_disableInts();
    CD_MEMCTRL = 0xFF00;
    CD_SUB_BYTE = 3;
    CD_SUB_BYTE = 2;
    CD_SUB_BYTE = 0;
    SYS_enableInts();
    for (u16 i = 0; i < 128; i++)
        __asm__ volatile ("nop");

    if (!wait_sub(1, 0))
        return "RESET TIMEOUT";

    CD_SUB_BYTE = 3;
    if (!wait_sub(3, 3))
        return "BUS REQUEST TIMEOUT";

    CD_MEMCTRL = 0;
    CD_MAIN_SEQ = 0;
    CD_MAIN_X = 0;
    CD_MAIN_Y = 0;
    CD_MAIN_HEADING = 0;
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++)
        CD_PRGRAM[i] = sub_program[i];
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++)
    {
        if (CD_PRGRAM[i] != sub_program[i])
        {
            CD_SUB_BYTE = 0;
            return "PRG RAM VERIFY FAILED";
        }
    }

    CD_SUB_BYTE = 0;
    if (!wait_sub(1, 0))
        return "SECOND RESET TIMEOUT";

    CD_SUB_BYTE = 1;
    if (!wait_sub(3, 1))
        return "RELEASE TIMEOUT";
    return NULL;
}

static u32 scd_frames;
static volatile u16 scd_vram_readback[WORD_COUNT];

__attribute__((noinline, noclone))
static void scd_gate_fail(const char *message)
{
    VDP_clearTextLine(2);
    VDP_drawText(message, 2, 2);
    number("FRAMES: ", scd_frames, 3);
    while (TRUE)
        SYS_doVBlankProcess();
}

static void await_frame(u16 id, bool swap, u16 next_bank)
{
    const u32 start = vtimer;
    const u16 limit = swap ? SWAP_TIMEOUT_VBLANKS : RENDER_TIMEOUT_VBLANKS;
    for (;;)
    {
        if (CD_SUB_SIG == SUB_FAULT)
            scd_gate_fail("SUB CPU EXCEPTION");
        if (!swap && CD_SUB_READY == id)
            return;
        if (swap && CD_SUB_ACK == id && (CD_MEMCTRL & 7u) == (4u | next_bank))
            return;
        if (vtimer - start >= limit)
            scd_gate_fail(swap ? "SWAP TIMEOUT" : "FRAME TIMEOUT");
    }
}

static u32 vram_command(u16 address)
{
    return ((u32)(address & 0x3fffu) << 16) | (address >> 14);
}

static s16 camera_x = START_X, camera_y = START_Y;
static u16 heading, previous_buttons;
static s16 auto_step = 16;
static bool autoplay = TRUE;

static bool camera_fits(s16 x, s16 y)
{
    const s16 r = 32;
    return scene[(y - r) >> 8][(x - r) >> 8] == '0'
        && scene[(y - r) >> 8][(x + r) >> 8] == '0'
        && scene[(y + r) >> 8][(x - r) >> 8] == '0'
        && scene[(y + r) >> 8][(x + r) >> 8] == '0';
}

static void move_camera(u16 buttons)
{
    if ((buttons & BUTTON_A) && !(previous_buttons & BUTTON_A))
    {
        autoplay = !autoplay;
        if (autoplay)
        {
            camera_x = START_X;
            camera_y = START_Y;
            heading = 0;
            auto_step = 16;
        }
    }
    previous_buttons = buttons;

    if (autoplay)
    {
        camera_x += auto_step;
        if (camera_x >= 11 * 256 + 128 || camera_x <= START_X)
            auto_step = -auto_step;
        return;
    }

    if (buttons & BUTTON_LEFT)
        heading = (heading - 1u) & 63u;
    if (buttons & BUTTON_RIGHT)
        heading = (heading + 1u) & 63u;
    const s16 speed = (buttons & BUTTON_UP ? 24 : 0) - (buttons & BUTTON_DOWN ? 24 : 0);
    const s16 next_x = camera_x + ((cosine[heading] * speed) >> 8);
    const s16 next_y = camera_y + ((cosine[(heading + 48u) & 63u] * speed) >> 8);
    if (camera_fits(next_x, camera_y))
        camera_x = next_x;
    if (camera_fits(camera_x, next_y))
        camera_y = next_y;
}

static void dispatch_camera(u16 id)
{
    CD_MAIN_X = camera_x;
    CD_MAIN_Y = camera_y;
    CD_MAIN_HEADING = heading;
    CD_MAIN_SEQ = id;
}

static void display_frame(bool verify)
{
    const u16 dest = TILE_USER_INDEX * 32u;
    const u16 first = WORD_DATA[0], second = WORD_DATA[1];

    /* The 03D transport verified this source offset and prefix repair. */
    DMA_doDma(DMA_VRAM, (void *)0x600022, dest, WORD_COUNT, 2);
    VDP_waitDMACompletion();
    SYS_disableInts();
    VDP_CTRL = vram_command(dest) | 0x40000000UL;
    VDP_DATA = first;
    VDP_DATA = second;

    u16 bad = WORD_COUNT;
    if (verify)
    {
        VDP_CTRL = vram_command(dest);
        for (u16 i = 0; i < WORD_COUNT; ++i)
        {
            const u16 value = VDP_DATA;
            scd_vram_readback[i] = value;
            if (value != WORD_DATA[i] && bad == WORD_COUNT)
                bad = i;
        }
    }
    SYS_enableInts();
    if (bad != WORD_COUNT)
    {
        number("FIRST BAD VRAM WORD: ", bad, 4);
        scd_gate_fail("VRAM DMA MISMATCH");
    }
}

__attribute__((noinline, noclone, used))
static void scd_visual_checkpoint(u16 frame)
{
    number("VERIFIED VRAM: ", frame, 3);
}

int main(bool hard)
{
    (void)hard;
    VDP_setScreenWidth320();
    VDP_setPlaneSize(64, 32, TRUE);
    VDP_drawText("DOOM SCD / LIVE 3D", 2, 0);
    VDP_drawText("SUB 68000 / WORD RAM 1M / VDP", 2, 1);

    if ((HW_VERSION & 0x20u) && CD_BIOS_HEADER != 0x53454741UL)
        scd_gate_fail("NO SEGA CD DETECTED");
    const char *failure = boot_sub();
    if (failure)
        scd_gate_fail(failure);
    for (u16 wait = 0; CD_SUB_SIG != SUB_READY || (CD_MEMCTRL & 7u) != 4u; wait++)
    {
        if (wait == TIMEOUT_VBLANKS)
            scd_gate_fail("WORD RAM 1M INIT TIMEOUT");
        SYS_doVBlankProcess();
    }

    static const u16 colors[16] = {
        0x000, 0x422, 0x644, 0x222, 0x666, 0x888, 0xaaa, 0x244,
        0x466, 0x068, 0x08c, 0x248, 0x24c, 0x4ae, 0x8ce, 0xcee,
    };
    PAL_setPalette(PAL1, colors, CPU);
    for (u16 i = 0; i < TILE_COUNT; i++)
        VDP_setTileMapXY(BG_B, TILE_ATTR_FULL(PAL1, 0, 0, 0, TILE_USER_INDEX + i),
                         10 + (i % TILES_W), 6 + (i / TILES_W));
    VDP_drawText("A: AUTO / MANUAL   D-PAD: MOVE", 2, 22);
    JOY_init();

    u16 id = 1;
    dispatch_camera(id);
    while (TRUE)
    {
        await_frame(id, FALSE, 0);
        const u16 next_bank = (CD_MEMCTRL ^ 1u) & 1u;
        CD_MEMCTRL = 0;
        await_frame(id, TRUE, next_bank);
        if (WORD_ID != id)
            scd_gate_fail("STALE WORD RAM FRAME");

        move_camera(JOY_readJoypad(JOY_1));
        dispatch_camera(id + 1u);

        /* The Sub CPU can draw the next frame while Main owns this bank. */
        scd_frames++;
        const bool verify = scd_frames == 1 || scd_frames == 65;
        display_frame(verify);
        if (verify)
            scd_visual_checkpoint(id);
        if ((scd_frames & 15u) == 0)
        {
            number("FRAMES: ", scd_frames, 2);
            VDP_drawText(autoplay ? "MODE: AUTO  " : "MODE: MANUAL", 23, 2);
        }
        id++;
        SYS_doVBlankProcess();
    }
}
