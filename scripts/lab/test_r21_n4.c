/* R21 N4 equivalence test (host C, exhaustive over small ranges + random).
 * Reference: the tier logic of R_RenderSegLoop (R20h), reduced to "does any
 * code in this column read texturecolumn/fracstep?". Candidate: the N4
 * predicate, copied verbatim from the patch. Types match the game:
 * int16_t clips, int32_t fixed_t, FRACBITS 16, FRACUNIT 65536.
 * Build: cc -O2 -o t test_n4_predicate.c && ./t                       */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef int32_t fixed_t;
typedef int boolean;
#define FRACBITS 16
#define FRACUNIT (1 << FRACBITS)

/* reference: run the tier code; report whether texturecolumn was read */
static boolean ref_reads_tex(boolean midtexture, boolean toptexture, boolean bottomtexture,
                             boolean maskedtexture, boolean markceiling,
                             int16_t yl, int16_t yh, int16_t cc_rwx, int16_t fc_rwx,
                             fixed_t pixhigh, fixed_t pixlow)
{
    boolean used = 0;
    if (midtexture)
        return 1;                       /* mid tier is drawn unconditionally */
    if (toptexture)
    {
        int16_t mid = pixhigh>>FRACBITS;
        if (mid >= fc_rwx) mid = fc_rwx-1;
        if (mid >= yl) { used = 1; cc_rwx = mid; }
        else cc_rwx = yl-1;
    }
    else if (markceiling)
        cc_rwx = yl-1;
    if (bottomtexture)
    {
        int16_t mid = ((fixed_t)((uint32_t)pixlow + FRACUNIT - 1u)) >> FRACBITS;
        if (mid <= cc_rwx) mid = cc_rwx+1;
        if (mid <= yh) { used = 1; fc_rwx = mid; }
        else fc_rwx = yh+1;
    }
    if (maskedtexture)
        used = 1;                       /* maskedtexturecol[rw_x] = texturecolumn */
    return used;
}

/* candidate: verbatim from the patch */
static boolean n4_need_tex(boolean midtexture, boolean toptexture, boolean bottomtexture,
                           boolean maskedtexture, boolean markceiling,
                           int16_t yl, int16_t yh, int16_t cc_rwx, int16_t fc_rwx,
                           fixed_t pixhigh, fixed_t pixlow)
{
        boolean r21_need_tex = midtexture || maskedtexture;
        if (!r21_need_tex && toptexture)
        {
            int16_t mid = pixhigh>>FRACBITS;
            if (mid >= fc_rwx)
                mid = fc_rwx-1;
            r21_need_tex = (mid >= yl);
        }
        if (!r21_need_tex && bottomtexture)
        {
            const int16_t cc = (toptexture || markceiling) ? yl-1 : cc_rwx;
            int16_t mid = ((fixed_t)((uint32_t)pixlow + FRACUNIT - 1u)) >> FRACBITS;
            if (mid <= cc)
                mid = cc+1;
            r21_need_tex = (mid <= yh);
        }
        return r21_need_tex;
}

static uint64_t rng = 0x9E3779B97F4A7C15ull;
static uint32_t rnd(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return (uint32_t)rng; }

int main(void)
{
    uint64_t n = 0, bad = 0, skippable = 0;
    /* exhaustive: 32 flag combinations x clip/row grid x pix in rows -3..24 */
    for (int f = 0; f < 32; f++)
    for (int yl = -2; yl <= 23; yl++)
    for (int yh = -2; yh <= 23; yh++)
    for (int cc = -2; cc <= 23; cc += 1)
    for (int fc = -1; fc <= 23; fc += 2)
    for (int ph = -3; ph <= 24; ph += 3)
    for (int pl = -3; pl <= 24; pl += 3)
    for (int frac = 0; frac < 3; frac++)
    {
        fixed_t pixhigh = (ph * FRACUNIT) + (frac == 0 ? 0 : frac == 1 ? 1 : FRACUNIT-1);
        fixed_t pixlow  = (pl * FRACUNIT) + (frac == 0 ? 0 : frac == 1 ? 1 : FRACUNIT-1);
        boolean a = ref_reads_tex(f&1, (f>>1)&1, (f>>2)&1, (f>>3)&1, (f>>4)&1, yl, yh, cc, fc, pixhigh, pixlow);
        boolean b = n4_need_tex  (f&1, (f>>1)&1, (f>>2)&1, (f>>3)&1, (f>>4)&1, yl, yh, cc, fc, pixhigh, pixlow);
        n++;
        if (a != b) { if (bad < 5) printf("MISMATCH f=%d yl=%d yh=%d cc=%d fc=%d ph=%d pl=%d frac=%d ref=%d n4=%d\n", f,yl,yh,cc,fc,ph,pl,frac,a,b); bad++; }
        if (!b) skippable++;
    }
    /* random: full int16/fixed ranges */
    for (uint32_t i = 0; i < 20000000u; i++)
    {
        int f = rnd() & 31;
        int16_t yl = (int16_t)rnd(), yh = (int16_t)rnd(), cc = (int16_t)rnd(), fc = (int16_t)rnd();
        fixed_t ph = (fixed_t)rnd(), pl = (fixed_t)rnd();
        if (i & 1) { yl = rnd()%30-3; yh = rnd()%30-3; cc = rnd()%30-3; fc = rnd()%30-3; ph = (fixed_t)(rnd()%(30u<<16)) - (3<<16); pl = (fixed_t)(rnd()%(30u<<16)) - (3<<16); }
        boolean a = ref_reads_tex(f&1, (f>>1)&1, (f>>2)&1, (f>>3)&1, (f>>4)&1, yl, yh, cc, fc, ph, pl);
        boolean b = n4_need_tex  (f&1, (f>>1)&1, (f>>2)&1, (f>>3)&1, (f>>4)&1, yl, yh, cc, fc, ph, pl);
        n++;
        if (a != b) { if (bad < 10) printf("MISMATCH(random) f=%d\n", f); bad++; }
    }
    printf("cases %llu, mismatches %llu (grid: %.1f%% of cases skippable)\n",
           (unsigned long long)n, (unsigned long long)bad, 100.0 * (double)skippable / (double)(n - 20000000u));
    return bad != 0;
}
