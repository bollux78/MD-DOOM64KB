/* S1a, Mega Drive side, linked inside the R128 All build (installed by build.py).
 * Boots the sub-CPU with engine code, runs the same engine checks natively, serves the
 * E1M1 lumps from the ROM WAD through Word RAM 1M, compares everything, shows the result
 * and stops (test ROM: the game does not start). */
#include <genesis.h>
#include "w_wad.h"
#include "s1a_tests.h"
#include "s1a_sub.h"

#define HW_VERSION (*(volatile const u8 *)0xA10001)
#define CD_BIOS_HEADER (*(volatile const u32 *)0x400100)
#define CD_SUB_BYTE (*(volatile u8 *)0xA12001)
#define CD_MEMCTRL (*(volatile u16 *)0xA12002)
#define CD_MAIN_SWAP (*(volatile u16 *)0xA12018)
#define CD_SUB_SIG (*(volatile const u16 *)0xA12020)
#define CD_SUB_ACK (*(volatile const u16 *)0xA12026)
#define CD_SUB_DONE (*(volatile const u16 *)0xA12028)
#define CD_SUB_HI (*(volatile const u16 *)0xA1202A)
#define CD_SUB_LO (*(volatile const u16 *)0xA1202C)
#define CD_PRGRAM ((volatile u16 *)0x420000)
#define BANK ((volatile u8 *)0x600000)

volatile u16 s1a_state;                 /* 1 no CD, 2 boot fail, 3 swap fail, 4 done */
volatile u32 s1a_md[S1A_TESTS], s1a_sub[S1A_TESTS];
volatile u16 s1a_lumps, s1a_lump_bad, s1a_tests_bad;
volatile u32 s1a_bytes, s1a_cache_md, s1a_cache_sub;
static u16 request;

static bool wait_sub(u8 mask, u8 expected)
{
    for (u32 n = 0; n < 400000UL; n++)
        if ((CD_SUB_BYTE & mask) == expected)
            return TRUE;
    return FALSE;
}

static bool boot_sub(void)
{
    CD_MEMCTRL = 0xFF00;
    CD_SUB_BYTE = 3; CD_SUB_BYTE = 2; CD_SUB_BYTE = 0;
    for (u16 i = 0; i < 128; i++) __asm__ volatile ("nop");
    if (!wait_sub(1, 0)) return FALSE;
    CD_SUB_BYTE = 3;
    if (!wait_sub(3, 3)) return FALSE;
    CD_MEMCTRL = 0;
    CD_MAIN_SWAP = 0;
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++) CD_PRGRAM[i] = sub_program[i];
    for (u32 i = 0; i < SUB_PROGRAM_WORDS; i++) if (CD_PRGRAM[i] != sub_program[i]) return FALSE;
    CD_SUB_BYTE = 0;
    if (!wait_sub(1, 0)) return FALSE;
    CD_SUB_BYTE = 1;
    if (!wait_sub(3, 1)) return FALSE;
    for (u32 n = 0; n < 4000000UL; n++)
        if (CD_SUB_SIG == 0x5343u && (CD_MEMCTRL & 5u) == 4u) return TRUE;
    return FALSE;
}

static bool call(u16 id, u32 *crc)
{
    const u16 mode = (CD_MEMCTRL & 5u) ^ 1u;
    CD_MAIN_SWAP = id;
    for (u32 n = 0; n < 4000000UL; n++)
        if (CD_SUB_ACK == id && CD_SUB_DONE == id && (CD_MEMCTRL & 5u) == mode)
        {
            *crc = ((u32)CD_SUB_HI << 16) | CD_SUB_LO;
            return TRUE;
        }
    return FALSE;
}

static void line(const char *label, u32 value, u16 y)
{
    char t[40], d[12];
    uintToStr(value, d, 1); strcpy(t, label); strcat(t, d);
    VDP_drawText(t, 1, y);
}

void __attribute__((noipa)) s1a_complete(void) { __asm__ volatile ("" ::: "memory"); }

static void run(void)
{
    for (int k = 0; k < S1A_TESTS; k++) s1a_md[k] = s1a_test(k);
    if ((HW_VERSION & 0x20u) || CD_BIOS_HEADER != 0x53454741UL) { s1a_state = 1; return; }
    if (!boot_sub()) { s1a_state = 2; return; }
    u32 crc;
    for (int k = 0; k < S1A_TESTS; k++)
    {
        if (!call(++request | 0x8000u, &crc)) { s1a_state = 3; return; }
        s1a_sub[k] = crc;
        s1a_tests_bad += crc != s1a_md[k];
    }
    /* Serve E1M1's lumps exactly as the sub will request them in S1. */
    const int16_t first = W_GetNumForName("E1M1");
    for (int16_t n = first; n < first + 16; n++)
    {
        const char __far *name = W_GetNameForNum(n);
        if (n > first && name[0] == 'E' && name[2] == 'M') break;
        const u16 size = W_LumpLength(n);
        const u8 *src = W_GetLumpByNum(n);
        BANK[0] = size >> 8; BANK[1] = size; BANK[2] = 0; BANK[3] = 0;
        for (u16 i = 0; i < size; i++) BANK[4 + i] = src[i];
        const u32 mine = s1a_crc(0, src, size);
        if (!call(++request & 0x7fffu, &crc)) { s1a_state = 3; return; }
        ++s1a_lumps; s1a_bytes += size;
        s1a_lump_bad += crc != mine;
        if (s1a_bytes <= 160u * 1024u) s1a_cache_md = s1a_crc(s1a_cache_md, src, size);
    }
    if (!call(++request | 0x800Fu, &crc)) { s1a_state = 3; return; }
    s1a_cache_sub = crc;
    s1a_state = 4;
}

void S1A_Test(void)
{
    SYS_disableInts();
    run();
    SYS_enableInts();
    s1a_complete();
    VDP_init();
    VDP_drawText("doom-md-scd-s1a.bin", 1, 1);
    static const char *const st[] = { "?", "NO SEGA CD", "SUB BOOT FAILED", "SUB CALL TIMEOUT", "" };
    const bool pass = s1a_state == 4 && !s1a_tests_bad && !s1a_lump_bad && s1a_cache_md == s1a_cache_sub;
    VDP_drawText(pass ? "S1A PASS: ENGINE CODE ON SUB-CPU" : "S1A FAIL", 1, 3);
    VDP_drawText(st[s1a_state < 5 ? s1a_state : 0], 1, 4);
    line("SUB PROGRAM BYTES: ", SUB_PROGRAM_WORDS * 2u, 6);
    line("ENGINE TESTS DIFFERENT: ", s1a_tests_bad, 7);
    line("E1M1 LUMPS SERVED: ", s1a_lumps, 9);
    line("E1M1 BYTES SERVED: ", s1a_bytes, 10);
    line("LUMP CRC MISMATCHES: ", s1a_lump_bad, 11);
    VDP_drawText(s1a_cache_md == s1a_cache_sub ? "SUB CACHE CRC: MATCH" : "SUB CACHE CRC: DIFFERENT", 1, 12);
    VDP_drawText("TEST ROM: GAME DOES NOT START", 1, 15);
    for (;;) ;
}
