/* S1: Sega CD sub-CPU WAD directory + bounded per-map resident lump cache.
 *
 * This module compiles instead of src/w_wad.c in the sub's link.
 * The transport hooks are intentionally external: the MD must implement
 * the DIR/LUMP transactions before this can run a Doom game on the sub.
 * Never return a temporary Word RAM pointer to the engine: cache entries
 * must survive MD-driven bank swaps during rendering and P_Ticker.
 */
#include <stdint.h>
#include <string.h>
#include "doomtype.h"
#include "w_wad.h"
#include "i_system.h"

#define SCD_WAD_MAX_LUMPS 2048u
#define SCD_WAD_CACHE_BYTES (128UL * 1024UL)

typedef struct {
    char name[8];
    uint16_t size;
} scd_lump_dirent_t;

/* These callbacks must perform synchronous 1M bank exchanges through MD.
 * Return nonzero on success, zero on timeout or corrupt packet. */
extern int scd_fetch_directory(scd_lump_dirent_t *entries, uint16_t capacity,
                               uint16_t *count);
extern int scd_fetch_lump(uint16_t lump, void *destination, uint16_t bytes);

static scd_lump_dirent_t scd_directory[SCD_WAD_MAX_LUMPS];
static const uint8_t *scd_slots[SCD_WAD_MAX_LUMPS];
static uint8_t scd_cache[SCD_WAD_CACHE_BYTES];
static uint32_t scd_cache_used, scd_cache_peak;
static uint16_t scd_lump_count, scd_cache_misses;

static uint8_t upper_ascii(uint8_t c)
{
    return (c >= (uint8_t)'a' && c <= (uint8_t)'z') ? (uint8_t)(c - 32u) : c;
}

void W_FlushCache(void)
{
    for (uint16_t i = 0; i < scd_lump_count; i++) scd_slots[i] = 0;
    scd_cache_used = 0;
}

void W_Init(void)
{
    uint16_t count = 0;
    if (!scd_fetch_directory(scd_directory, SCD_WAD_MAX_LUMPS, &count) ||
        count == 0 || count > SCD_WAD_MAX_LUMPS)
        I_Error("SCD WAD DIRECTORY FAILED");
    scd_lump_count = count;
    scd_cache_peak = 0;
    scd_cache_misses = 0;
    W_FlushCache();
}

static void scd_check_num(int16_t n)
{
    if (n < 0 || (uint16_t)n >= scd_lump_count)
        I_Error("SCD BAD LUMP %d", n);
}

const char __far* W_GetNameForNum(int16_t n)
{
    scd_check_num(n);
    return scd_directory[n].name;
}

uint16_t W_LumpLength(int16_t n)
{
    scd_check_num(n);
    return scd_directory[n].size;
}

int16_t W_GetNumForName(const char *name)
{
    char desired[8] = {0};
    for (uint16_t j = 0; j < 8u && name[j]; j++)
        desired[j] = (char)upper_ascii((uint8_t)name[j]);
    for (uint16_t i = 0; i < scd_lump_count; i++)
    {
        uint16_t ok = 1;
        for (uint16_t j = 0; j < 8u; j++)
            if (upper_ascii((uint8_t)scd_directory[i].name[j]) != (uint8_t)desired[j])
            { ok = 0; break; }
        if (ok) return (int16_t)i;
    }
    I_Error("SCD LUMP %.8s NOT FOUND", name);
    return -1;
}

const void __far* W_GetLumpByNum(int16_t n)
{
    scd_check_num(n);
    if (scd_slots[n]) return scd_slots[n];
    const uint32_t size = scd_directory[n].size;
    /* Align each lump for 68000 word/long accesses, including the first.
       Zero-length label lumps still require a stable non-NULL pointer. */
    const uint32_t offset = (scd_cache_used + 3u) & ~3UL;
    const uint32_t next = offset + (size ? size : 1u);
    if (next > sizeof scd_cache)
        I_Error("SCD LUMP CACHE FULL %d", n);
    uint8_t *dest = scd_cache + offset;
    if (size && !scd_fetch_lump((uint16_t)n, dest, (uint16_t)size))
        I_Error("SCD LUMP TRANSFER FAILED %d", n);
    scd_cache_used = next;
    if (next > scd_cache_peak) scd_cache_peak = next;
    scd_cache_misses++;
    scd_slots[n] = dest;
    return dest;
}

void W_ReadLumpByNum(int16_t n, void __far* ptr)
{
    const uint16_t size = W_LumpLength(n);
    if (size) memcpy(ptr, W_GetLumpByNum(n), size);
}

uint32_t SCD_WadCachePeak(void) { return scd_cache_peak; }
uint32_t SCD_WadCacheCurrent(void) { return scd_cache_used; }
uint16_t SCD_WadCacheMisses(void) { return scd_cache_misses; }
uint16_t SCD_WadLumpCount(void) { return scd_lump_count; }
