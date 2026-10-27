/* ROM cost/map tables. In-place postpass AFTER rendering, BEFORE publication.
 * Pair-V B is shifted +4px relative to A. Keep all B priorities low: A's
 * tile-wide priority then controls BOTH four-pixel halves of each 8x8 block,
 * even where A is transparent. No independently shadowed column claim.
 * No additional permanent WRAM, operator sprites, or highlight. */
static void R79_Convert(uint16_t *pixels,const uint16_t maps[2][2][256],
                        const uint16_t costs[2][2][256])
{
    for(uint16_t y=1u;y<22u;y++){
        uint16_t *a=pixels+y*76u,*b=a+38u;
        for(uint16_t x=0;x<38u;x++){
            uint16_t ca=a[x]&255u,cb=b[x]&255u;
            uint32_t n=(uint32_t)costs[0][0][ca]+costs[0][1][cb];
            uint32_t s=(uint32_t)costs[1][0][ca]+costs[1][1][cb];
            uint16_t shadow=s<n;
            a[x]=maps[shadow][0][ca];b[x]=maps[shadow][1][cb];
        }
    }
}
