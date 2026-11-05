/* R131 SSF2 mapper diagnostic -- synthetic test only, no Doom/WAD assets. */
#include <genesis.h>
#include <stdint.h>

#ifndef R131_PAGES
#define R131_PAGES 8
#endif

#define PAGE_BYTES 0x80000UL
#define PROBE_OFF  0x100UL
#define SLOT7_ADDR 0x380100UL
#define SLOT7_REG  (*(volatile uint8_t *)0xA130FFUL)

static char line[31];
static uint16_t failures = 0;

static uint32_t signature(uint16_t p)
{
    return 0xA1310000UL ^ ((uint32_t)p * 0x00010203UL) ^ ((uint32_t)p << 24);
}

static void show_page(uint16_t p, uint16_t ok, uint16_t row)
{
    char *d = line;
    *d++ = 'P'; *d++ = 'A'; *d++ = 'G'; *d++ = 'E'; *d++ = ' ';
    *d++ = '0' + (p / 10);
    *d++ = '0' + (p % 10);
    *d++ = ' ';
    *d++ = ' ';
    *d++ = ok ? 'P' : 'F'; *d++ = ok ? 'A' : 'A';
    *d++ = ok ? 'S' : 'I'; *d++ = ok ? 'S' : 'L';
    *d = 0;
    VDP_drawText(line, 3, row);
}

static uint32_t read_identity(uint16_t p)
{
    volatile const uint32_t *a = (volatile const uint32_t *)(uintptr_t)((uint32_t)p * PAGE_BYTES + PROBE_OFF);
    return *a;
}

static uint32_t read_slot7(void)
{
    volatile const uint32_t *a = (volatile const uint32_t *)(uintptr_t)SLOT7_ADDR;
    return *a;
}

int main(bool hard)
{
    uint16_t p, row = 7;
    uint16_t ok;
    uint16_t switch_ok = 1;
    uint16_t n;
    (void)hard;
    VDP_setScreenWidth320();
    PAL_setColor(0, RGB24_TO_VDPCOLOR(0x10152C));
    PAL_setColor(15, RGB24_TO_VDPCOLOR(0xFFFFFF));
    VDP_setTextPalette(PAL0);
    VDP_clearPlane(BG_A, TRUE);
    VDP_drawText("R131 MAPPER DIAGNOSTIC", 3, 2);
#if R131_PAGES > 8
    VDP_drawText("SSF2 BANK SWITCH TEST", 3, 4);
#else
    VDP_drawText("4 MIB STANDARD CART TEST", 3, 4);
    VDP_drawText("NO MAPPER WRITES", 3, 5);
#endif

    /* Unique synthetic signatures at offset 0x100 in each 512KiB page.
       Page 0 excluded: this offset contains the ROM header. */
    for (p = 1; p < 8; ++p)
    {
        ok = (read_identity(p) == signature(p));
        if (!ok) ++failures;
        show_page(p, ok, row++);
    }

#if R131_PAGES > 8
    /* Only slot 7 remapped; executable and VDP font stay in fixed page 0. */
    for (p = 8; p < R131_PAGES; ++p)
    {
        SLOT7_REG = (uint8_t)p;
        ok = (read_slot7() == signature(p));
        if (!ok) ++failures;
        if (p < 17) show_page(p, ok, row++);
    }
    for (n = 0; n < 1024; ++n)
    {
        p = (n & 1) ? (R131_PAGES - 1) : 8;
        SLOT7_REG = (uint8_t)p;
        if (read_slot7() != signature(p)) switch_ok = 0;
    }
    SLOT7_REG = 7;
    if (read_slot7() != signature(7)) switch_ok = 0;
    if (!switch_ok) ++failures;
    VDP_drawText(switch_ok ? "STRESS 1024: PASS" : "STRESS 1024: FAIL", 3, 22);
    if (R131_PAGES > 17)
        VDP_drawText("PAGES 17+ CHECKED TOO", 3, 23);
#endif
    if (failures)
    {
        VDP_drawText("RESULT: FAIL", 3, 25);
        PAL_setColor(0, RGB24_TO_VDPCOLOR(0x3F0010));
    }
    else
    {
        VDP_drawText("RESULT: PASS", 3, 25);
        PAL_setColor(0, RGB24_TO_VDPCOLOR(0x003020));
    }
#if R131_PAGES > 8
    VDP_drawText("NOT PROOF OF CLONE SUPPORT", 3, 27);
#else
    VDP_drawText("TESTS 4 MIB ROM READ ONLY", 3, 27);
#endif
    while (1)
        SYS_doVBlankProcess();
    return 0;
}
