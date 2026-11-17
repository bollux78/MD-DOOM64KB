static inline void R22_Plot(int16_t x,int16_t y,uint8_t c) {
    if((uint16_t)x>=R22_W || (uint16_t)y>=R22_H)return;
    /* Same8px top/left safety border as the38x22 reference. */
    if(_g_gamestate==GS_LEVEL && (x<2 || y<2))return;
    uint8_t *p = r22_fb.pixels + (uint16_t)y * 38u + ((uint16_t)x >> 1);
    *p = (x & 1) ? (uint8_t)((*p & 0xf0u) | (c & 15u))
                 : (uint8_t)((*p & 15u) | (c << 4));
}
void R_DrawColumnSprite(const draw_column_vars_t *v) {
    int16_t n=v->yh-v->yl+1;if(n<=0)return;
    uint16_t frac=(uint16_t)((v->texturemid>>7)+(v->yl-CENTERY)*v->fracstep);
    for(int16_t y=v->yl;y<=v->yh;y++) {
        uint8_t c=v->source[frac>>9];
        if(v->colormap)c=v->colormap[c];
        R22_Plot(v->x,y,r22_color[c]);frac+=v->fracstep;
    }
}
void R_DrawColumnWall(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
void R_DrawFuzzColumn(const draw_column_vars_t *v){R_DrawColumnSprite(v);}
void R_DrawColumnFlat(uint8_t c,const draw_column_vars_t *v){
    c=r22_color[c];for(int16_t y=v->yl;y<=v->yh;y++)R22_Plot(v->x,y,c);
}

/* Pair-V-only fast paths in the R128 seg loop must use the original C kernels. */
uint8_t *R95_FlatSetup(const uint8_t **lut) { (void)lut; return 0; }
uint8_t *R96_WallSetup(const uint8_t *colormap, const uint8_t **lut)
{ (void)colormap; (void)lut; return 0; }
