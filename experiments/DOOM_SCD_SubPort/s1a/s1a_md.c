/* S1a, Mega Drive side, linked inside the R128 All build (installed by build.py).
 * Boots the sub-CPU with engine code, runs the same engine checks natively, serves the
 * E1M1 lumps from the ROM WAD through Word RAM 1M, compares everything, shows the result
 * and stops (test ROM: the game does not start). */
#include <stddef.h>
#include <stdint.h>
#include <genesis.h>
#include "doomdef.h"
#include "doomtype.h"
#include "compiler.h"
#include "w_wad.h"
#include "i_system.h"
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

/* No new BSS: R128 is 40 bytes from the RAM limit. Results live at the end of the Word RAM bank
 * the MD holds when the test finishes (read by test_s1a.py at s1a_complete). */
typedef struct { u16 state, tests_bad, lumps, lump_bad; u32 bytes, cache_md, cache_sub, md[S1A_TESTS], sub[S1A_TESTS]; u16 stage; } S1aResult;
#define BANKRES (*(volatile S1aResult *)0x61F000)
static S1aResult *res_ptr;
#define R (*res_ptr)

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


void __attribute__((noipa)) s1a_complete(void) { __asm__ volatile ("" ::: "memory"); }
void __attribute__((noipa)) s1a_mark(u16 stage) { R.stage = stage; BANKRES.stage = stage; __asm__ volatile ("" ::: "memory"); }

static void run(void)
{
    u16 request = 0;
    for (int k = 0; k < S1A_TESTS; k++) R.md[k] = s1a_test(k);
    if ((HW_VERSION & 0x20u) || CD_BIOS_HEADER != 0x53454741UL) { R.state = 1; return; }
    s1a_mark(1);
    if (!boot_sub()) { R.state = 2; return; }
    s1a_mark(2);
    u32 crc;
    for (int k = 0; k < S1A_TESTS; k++)
    {
        if (!call(++request | 0x8000u, &crc)) { R.state = 3; return; }
        R.sub[k] = crc;
        R.tests_bad += crc != R.md[k];
    }
    s1a_mark(3);
    /* Serve E1M1's lumps exactly as the sub will request them in S1. */
    s1a_mark(4);
    const int16_t first = W_GetNumForName("E1M1");
    s1a_mark(5);
    for (int16_t n = first; n < first + 16; n++)
    {
        const char __far *name = W_GetNameForNum(n);
        if (n > first && name[0] == 'E' && name[2] == 'M') break;
        s1a_mark(0x200 + (u16)(n - first));
        const u16 size = W_LumpLength(n);
        const u8 *src = W_GetLumpByNum(n);
        BANK[0] = size >> 8; BANK[1] = size; BANK[2] = 0; BANK[3] = 0;
        for (u16 i = 0; i < size; i++) BANK[4 + i] = src[i];
        s1a_mark(0x300 + (u16)(n - first));
        const u32 mine = s1a_crc(0, src, size);
        s1a_mark(0x400 + (u16)(n - first));
        if (!call(++request & 0x7fffu, &crc)) { R.state = 3; return; }
        s1a_mark(0x100 + R.lumps);
        ++R.lumps; R.bytes += size;
        R.lump_bad += crc != mine;
        if (R.bytes <= 160u * 1024u) R.cache_md = s1a_crc(R.cache_md, src, size);
    }
    if (!call(++request | 0x800Fu, &crc)) { R.state = 3; return; }
    R.cache_sub = crc;
    R.state = 4;
}

void S1A_Test(void)
{
    S1aResult r;
    memset(&r, 0, sizeof r);
    res_ptr = &r;
    SYS_disableInts();
    run();
    BANKRES = r;                       /* into whichever bank the MD holds now */
    SYS_enableInts();
    s1a_complete();
    const bool pass = r.state == 4 && !r.tests_bad && !r.lump_bad && r.cache_md == r.cache_sub;
    static const char *const st[] = { "?", "NO SEGA CD", "SUB BOOT FAILED", "SUB CALL TIMEOUT", "OK" };
    I_Error("doom-md-scd-s1a.bin\nS1A %s (%s)\nSUB BYTES %u\nENGINE TESTS DIFF %u\nE1M1 LUMPS %u / %u BYTES\nLUMP CRC BAD %u\nSUB CACHE %s\nTEST ROM: GAME DOES NOT START",
            pass ? "PASS" : "FAIL", st[r.state < 5 ? r.state : 0], (unsigned)(SUB_PROGRAM_WORDS * 2u),
            (unsigned)r.tests_bad, (unsigned)r.lumps, (unsigned)r.bytes, (unsigned)r.lump_bad,
            r.cache_md == r.cache_sub ? "MATCH" : "DIFFERENT");
}
