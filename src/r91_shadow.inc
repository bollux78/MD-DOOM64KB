/* R91: one offline joint A/B decision per 8x8 block, no new WRAM.
 * This is a faster final pass, NOT independent per-pixel shadow. */
static void R91_ConvertFast(uint16_t *pixels,const uint32_t *table)
{
    for(uint16_t y=1;y<22;y++){
        uint16_t *a=pixels+y*76,*b=a+38;
        for(uint16_t x=0;x<38;x++){
            uint16_t key=(uint16_t)(((a[x]&255u)<<8)|(b[x]&255u));
            uint32_t pair=table[key];
            a[x]=(uint16_t)(pair>>16);b[x]=(uint16_t)pair;
        }
    }
}
