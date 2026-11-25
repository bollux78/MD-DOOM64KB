/* Ferret-derived projection, adaptive affine/perspective U and direct scaler
 * offsets, adapted to C7 BSP order, mutable sectors, tile layout and full WAD
 * pixels. This is a new implementation, not Ferret's executable/visibility
 * stream. UV coordinates remain in world units: no repeated half-width door.
 * Segment conversion bounds length to 256; source widths are <=256.
 */
#ifndef DREAD_SOURCE_PIXELS
#error Ferret backend requires full source columns regenerated from WAD
#endif
#if !defined(__m68k__) && !defined(__mc68000__)
extern const int16_t *const ferret_sample_offsets[2048];
#endif
#if defined(__m68k__) || defined(__mc68000__)
extern const uint8_t *const ferret_scalers_byte[2048],*const ferret_scalers_pair[2048];
extern void col_native_run(uint8_t*,const uint8_t*,const uint8_t*,uint32_t);
#endif
static int fr_offset(uint16_t scale,int y)
{
#if defined(__m68k__) || defined(__mc68000__)
    /* The MOVE displacement is the offset table; avoid storing it twice. */
    return *(const int16_t *)(ferret_scalers_byte[scale]+y*12+2);
#else
    return ferret_sample_offsets[scale][y];
#endif
}
static int fr_clamp(int y, int lo, int hi) { return y<lo?lo:y>hi?hi:y; }

/* Signed clipping: use a full quotient (not a 16-bit DIVS result) for products
 * of a plane distance and an endpoint delta. Setup is outside the column loop. */
static int32_t fr_ratio(int32_t value, int32_t a, int32_t den)
{
    return (int32_t)(((int64_t)value*a)/den);
}
static int fr_clip(int32_t *x0,int32_t *z0,int32_t *u0,
                   int32_t *x1,int32_t *z1,int32_t *u1,int plane)
{
    int32_t a=plane==0?*z0-40:plane==1?*z0+*x0:*z0-*x0;
    int32_t b=plane==0?*z1-40:plane==1?*z1+*x1:*z1-*x1;
    if(a<0 && b<0)return 0;
    if(a<0){int32_t den=b-a;*x0-=fr_ratio(*x1-*x0,a,den);*z0-=fr_ratio(*z1-*z0,a,den);*u0-=fr_ratio(*u1-*u0,a,den);}
    else if(b<0){int32_t den=a-b;*x1-=fr_ratio(*x0-*x1,b,den);*z1-=fr_ratio(*z0-*z1,b,den);*u1-=fr_ratio(*u0-*u1,b,den);}
    return 1;
}
static void fr_fill(int x,int y0,int y1,uint8_t color,int sky)
{
    if(y1<=y0)return;
    uint8_t *dst=FB_COL(rfb,x);
#if defined(__m68k__) || defined(__mc68000__)
    if(sky){
        const uint8_t *src=sky_blob+r_skyoff[x];
        for(int y=y0;y<y1;y++){dst[y*4]=src[y];if(COLB==2)dst[y*4+1]=src[y];}
        return;
    }
#else
    (void)sky;
#endif
    col_fill(dst+y0*4,(uint16_t)(y1-y0),color);
}
static void fr_texture(int x,int y0,int y1,const Part *p,uint16_t u,uint16_t inv)
{
    if(y1<=y0 || (dbg_flags&1))return;
    const uint8_t *source=texture_column(p,u);
    const uint16_t selector=inv>>5;
    const int base=p->vbase16>>16;
    uint8_t *dst=FB_COL(rfb,x);
#if defined(__m68k__) || defined(__mc68000__)
    /* Direct MOVE/DBRA scalers, with a scalar wrap fallback. No per-pixel
     * multiplication/division, and no expansion of the source texture. */
    int first=(uint16_t)(base+fr_offset(selector,y0))&p->hmask;
    int last=first+fr_offset(selector,y1-1)-fr_offset(selector,y0);
    if(last<=p->vlim){
        int32_t origin=first-fr_offset(selector,y0);
        const uint8_t *base_source=COLB==1?source:(const uint8_t *)rec+512;
        const uint8_t *src=(const uint8_t *)((unsigned long)base_source+origin*(COLB==1?1:2));
        const uint8_t *entry=(COLB==1?ferret_scalers_byte:ferret_scalers_pair)[inv>>5];
        if(entry){col_native_run(dst,src,entry+y0*12,(uint32_t)(y1-y0));return;}
    }
#endif
    for(int y=y0;y<y1;y++){
        uint8_t b=source[(uint16_t)(base+fr_offset(selector,y))&p->hmask];
        dst[y*4]=b;if(COLB==2)dst[y*4+1]=b;
    }
}
static void fr_draw_seg(const MapSeg *s)
{
    uint16_t a=xform(s->v1),b=xform(s->v2);
    int32_t x0=vtx[a],z0=vtz[a],x1=vtx[b],z1=vtz[b];
    if((int64_t)x0*z1-(int64_t)x1*z0>=0)return;
    /* Q6 U allows 511 source pixels and their inverse-depth products to fit
     * in unsigned 32 bits; modulo 256 preserves every supported material. */
    int32_t u0=(uint16_t)s->xoff&255,u1=u0+s->len;
#ifdef DREAD_GAMEPLAY
    if(s->flags&8){u0=(u0+r_scroll)&255;u1=u0+s->len;}
#endif
    u0*=64;u1*=64;
    for(int p=0;p<3;p++)if(!fr_clip(&x0,&z0,&u0,&x1,&z1,&u1,p))return;
    int xs=HALF_W+divs16((int32_t)x0*FOCAL,(int16_t)z0);
    int xe=HALF_W+divs16((int32_t)x1*FOCAL,(int16_t)z1);
    xs=fr_clamp(xs,0,VIEW_W);xe=fr_clamp(xe,0,VIEW_W);
    if(xe<=xs || find_open(xs)>=xe)return;
    const int n=xe-xs;
    const uint16_t iv0=divu16(0x280000UL,(uint16_t)z0),iv1=divu16(0x280000UL,(uint16_t)z1);
    const int16_t div=divs16((int32_t)iv1-iv0,(int16_t)n);
    const MapSector *f=&map_sectors[s->front],*back=s->back==NO_MAP_SECTOR?0:&map_sectors[s->back];
    int fc=sec_ceil[s->front],ff=f->floor,bc=back?sec_ceil[s->back]:fc,bf=back?back->floor:ff;
    const int up=back && bc<fc && !(f->sky&&back->sky) && s->upper!=255;
    const int lo=back && bf>ff && s->lower!=255;
    const int mid=!back && s->mid!=255;
    const int tex=mid||up||lo;
    uint16_t bucket=0;
#ifdef DREAD_GAMEPLAY
    bucket=r_fullbright?0:f->bucket;
#else
    bucket=f->bucket;
#endif
    if(mid)setup_part(&job.mid,s->mid,bucket,(s->flags&2)?ff+map_tex[s->mid].realh:fc,s->yoff,fc,0);
    if(up)setup_part(&job.up,s->upper,bucket,(s->flags&1)?fc:bc+map_tex[s->upper].realh,s->yoff,fc,0);
    if(lo)setup_part(&job.lo,s->lower,bucket,(s->flags&2)?fc:bf,s->yoff,bf,0);
    uint32_t start=0,end=0;int linear=1;int32_t du=0;
    if(tex){
        uint32_t p0=(uint32_t)u0*iv0,p1=(uint32_t)u1*iv1;
        uint16_t meaniv=((uint32_t)iv0+iv1)/2;
        uint32_t product=(p0>>1)+(p1>>1)+((p0&p1)&1);
        uint16_t approx=divu16(product,meaniv),mean=(u0+u1)/2;
        uint16_t error=mean>approx?mean-approx:approx-mean;
        linear=error<256 || (uint16_t)(error-256)<udiv32_16(5000000UL,meaniv);
        start=linear?(uint32_t)u0:p0;end=linear?(uint32_t)u1:p1;
        du=end>=start?(int32_t)udiv32_16(end-start,n):-(int32_t)udiv32_16(start-end,n);
    }
#if defined(DREAD_GAMEPLAY)
    /* Deferred masked walls keep C7's column ordering with sprites. Full
     * source U is supplied here; their existing coverage-run optimization stays. */
    if(back && s->mid!=255){
        int32_t iz0=inv_z((uint16_t)z0),iz1=inv_z((uint16_t)z1);
        int32_t uz0=(int32_t)(((int64_t)u0*(iz0>>8))/64),uz1=(int32_t)(((int64_t)u1*(iz1>>8))/64);
        queue_mask(s,xs,xe,iz0,(iz1-iz0)/n,uz0,(uz1-uz0)/n);
    }
#endif
    int heights[4]={fc,ff,bc,bf};int32_t edges[4],step[4];
    for(int k=0;k<4;k++){
        int32_t h=view_z-heights[k];
        edges[k]=(iv0>>5)*h+9344;
        step[k]=((int32_t)(iv1>>5)-(iv0>>5))*h/n;
    }
    uint32_t u=start;int32_t iv=iv0;
    rstats.segs_drawn++;if(tex)rstats.anchors++;
    for(int x=xs;x<xe;x++,u+=(uint32_t)du,iv+=div){
        int rows[4];for(int k=0;k<4;k++){rows[k]=edges[k]>>8;edges[k]+=step[k];}
        int top=ceilclip[x],bottom=floorclip[x];if(top>=bottom)continue;
        int yc=fr_clamp(rows[0],top,bottom),yf=fr_clamp(rows[1],yc,bottom);
        /* Adjacent sky sectors have no artificial upper wall at their seam. */
        if(back && f->sky && back->sky)yc=top;
        fr_fill(x,top,yc,f->ceilcol,f->sky&&sky_on);
        fr_fill(x,yf,bottom,f->floorcol,0);
        uint16_t source_u=0,scale=iv<1?1:iv>65535?65535:iv;
        if(tex)source_u=(linear?(uint16_t)u:divu16(u,scale))>>6;
        if(!back){if(mid)fr_texture(x,yc,yf,&job.mid,source_u,scale);close_col(x);closed++;}
        else{
            int ntop=yc,nbottom=yf;
            if(up){int y=fr_clamp(rows[2],yc,yf);fr_texture(x,yc,y,&job.up,source_u,scale);ntop=y;}
            if(lo){int y=fr_clamp(rows[3],ntop,yf);fr_texture(x,y,yf,&job.lo,source_u,scale);nbottom=y;}
            if(ntop>=nbottom){close_col(x);closed++;}
            else{ceilclip[x]=ntop;floorclip[x]=nbottom;}
        }
        rstats.col_visits++;
    }
}
