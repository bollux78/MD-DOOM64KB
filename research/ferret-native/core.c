/* Ferret-derived independent scalar reference, v0.
 * No original executable code, hardcoded ROM addresses or game state.
 * Host C implementation first; target memory layout/assembly are separate work.
 */
#include <stdint.h>
#include <stddef.h>
#define W 160
#define H 72
#define FB (W*H)
typedef struct { uint8_t pixels[FB]; uint16_t depth[W], owner[W], top[W], bottom[W]; } Frame;
typedef struct { const uint8_t *data; size_t size; int32_t origin; } Asset;
typedef struct {
    int32_t x0,width,inv0,inv1,scale_step,variant,textured,linear;
    uint32_t u0,du;
    int32_t z, heights[4], ceiling,floor;
} WallJob;
static int32_t s16(int64_t n) { uint32_t v=(uint32_t)n&65535u; return v>=32768u?(int32_t)v-65536:(int32_t)v; }
/* bits [lo,lo+16) of a 32-bit value as a signed 16-bit result: identical to s16(sar(n,lo)) whenever lo+16<=32 */
static int32_t s16bits(uint32_t v,unsigned lo){uint32_t t=(v>>lo)&65535u;return t>=32768u?(int32_t)t-65536:(int32_t)t;}
static int32_t min(int32_t a,int32_t b){return a<b?a:b;}
static int32_t max(int32_t a,int32_t b){return a>b?a:b;}
/* Both target and host GCC implement arithmetic right shift; assert that contract. */
typedef char fr_arithmetic_shift_required[((-1LL >> 1)==-1LL)?1:-1];
static int32_t sar(int64_t n,unsigned bits){return (int32_t)(n>>bits);}
static size_t pixel(int x,int y){return (size_t)(x/2)*144u+(x&1)+2u*(unsigned)y;}
static int has(unsigned mask,int v){return (mask>>v)&1u;}
static int sample(Asset a,int64_t off,uint8_t *out){
    int64_t p=(int64_t)a.origin+off;
    if(!a.data||p<0||(uint64_t)p>=a.size)return -1;
    *out=a.data[p];return 0;
}
void fr_begin(Frame *f){
    for(int x=0;x<W;x++){f->top[x]=0;f->bottom[x]=H;f->owner[x]=0;}
}
/* Variant capabilities, indexed by renderer's 18 decoded wall classes. */
#define B(i) (1u<<(i))
static const unsigned ceilings=B(0)|B(1)|B(2)|B(3)|B(6)|B(7)|B(8)|B(9)|B(10)|B(11)|B(12)|B(13)|B(14)|B(15)|B(16)|B(17);
static const unsigned uppers=B(0)|B(1)|B(2)|B(3)|B(9)|B(10)|B(11)|B(15)|B(16)|B(17);
static const unsigned lowers=B(1)|B(3)|B(5)|B(8)|B(11)|B(14)|B(17);
static const unsigned floors=B(0)|B(1)|B(2)|B(3)|B(4)|B(5)|B(7)|B(8)|B(10)|B(11)|B(13)|B(14)|B(16)|B(17);
static const unsigned skies=B(2)|B(3)|B(12)|B(13)|B(14)|B(15)|B(16)|B(17);
static uint8_t pair_phase(uint8_t c,int y){return (y&1)?(uint8_t)((c<<4)|(c>>4)):c;}
static int fill(Frame *f,int x,int t,int b,int lo,int hi,uint8_t c,const uint8_t *sky,int pair){
    const int y0=max(t,lo),y1=min(b,hi);
    if(y0>=y1)return 0;
    uint8_t *dst=f->pixels+pixel(x,y0);
    if(sky){const uint8_t *s=sky+x*H;for(int y=y0;y<y1;y++,dst+=2){uint8_t v=s[y];*dst=pair?pair_phase(v,y):v;}}
    else if(pair){const uint8_t e=c,o=pair_phase(c,1);int y=y0;if(y&1){*dst=o;dst+=2;y++;}
        for(;y+1<y1;y+=2,dst+=4){dst[0]=e;dst[2]=o;} if(y<y1)*dst=e;}
    else for(int y=y0;y<y1;y++,dst+=2)*dst=c;
    return 0;
}
#ifdef __m68k__
extern void fr_col_pair(uint8_t *dst,const uint8_t *src,const int16_t *sc,int32_t base,uint32_t n,uint32_t odd_first,const uint8_t *swap);
#endif
static uint8_t swap_lut[256];static int swap_ready;
static int tex(Frame *f,int x,int t,int b,int lo,int hi,Asset a,int offset,const int16_t *sc,int packed){
    if(packed==2&&a.data&&a.size==8192){
        /* Fast path. Scaler rows are affine in y (monotonic), so checking the two end rows bounds every row;
         * otherwise fall through to the checked per-row loop below, which keeps the exact error behaviour. */
        const int y0=max(t,lo),y1=min(b,hi);
        if(y0>=y1)return 0;
        const int32_t base=offset+a.origin,pa=base+sc[y0],pb=base+sc[y1-1];
        if(pa>=0&&pa<24576&&pb>=0&&pb<24576){
            uint8_t *dst=f->pixels+pixel(x,y0);
            if(!swap_ready){for(unsigned i=0;i<256;i++)swap_lut[i]=(uint8_t)((i<<4)|(i>>4));swap_ready=1;}
#ifdef __m68k__
            fr_col_pair(dst,a.data,sc+y0,base,(uint32_t)(y1-y0),(uint32_t)(y0&1),swap_lut);
#else
            for(int y=y0;y<y1;y++,dst+=2){uint8_t c=a.data[(unsigned)(base+sc[y])&8191u];*dst=(y&1)?swap_lut[c]:c;}
#endif
            return 0;
        }
    }
    for(int y=max(t,lo);y<min(b,hi);y++){
        uint8_t c;
        if(packed==2){
            int32_t p=offset+sc[y]+a.origin;
            if(!a.data||a.size!=8192||p<0||p>=24576)return -2;
            c=pair_phase(a.data[(unsigned)p&8191u],y);
        }else if(packed){
            int32_t p=offset+sc[y]+a.origin;
            if(!a.data||a.size!=4096||p<0||p>=24576)return -2;
            unsigned i=(unsigned)p&8191u;uint8_t b=a.data[i>>1];
            c=(uint8_t)((i&1?b&15:b>>4)*17u);
        }else if(sample(a,(int64_t)offset+sc[y],&c))return -2;
        f->pixels[pixel(x,y)]=c;
    }
    return 0;
}
/* Offset table is pure numeric data, indexed by (scale >> 5), 72 entries per row.
 * sky is a caller-supplied visible 160x72 column-major sample array.
 * Assets provide a bounded byte view and a logical texture origin.
 */
static int wall_impl(Frame *f,const WallJob *w,Asset upper,Asset lower,const int16_t *scalers,const uint8_t *sky,int packed,const uint8_t *indices){
    int v=w->variant,n=w->width;
    if(v<0||v>17||n<=0||w->x0<0||w->x0>=W||n>W-w->x0)return -1;
    if(has(skies,v)&&!sky)return -1;
    if(w->textured&&!scalers)return -1;
    int32_t e[4],d[4];
    for(int k=0;k<4;k++){
        int32_t h=w->heights[k]-w->z;
        int32_t a=sar(w->inv0,5)*h,b=sar(w->inv1,5)*h;
        e[k]=a+9344;d[k]=(b-a)/n;
    }
    int c=has(ceilings,v),u=has(uppers,v),l=has(lowers,v),fl=has(floors,v);
    uint32_t acc[4]={(uint32_t)e[0],(uint32_t)e[1],(uint32_t)e[2],(uint32_t)e[3]};
    uint32_t inv_acc=(uint32_t)w->inv0,q_acc=w->u0; /* running inv0+step*j and u0+du*j (same modular values, no multiply per column) */
    for(int j=0;j<n;j++){
        int x=w->x0+j,t=f->top[x],b=f->bottom[x];
        /* e+d*j kept as a running 32-bit sum: only bits 8..23 are used, so the 64-bit product was redundant */
        const uint32_t c0=acc[0],c1=acc[1],c2=acc[2],c3=acc[3];
        acc[0]+=(uint32_t)d[0];acc[1]+=(uint32_t)d[1];acc[2]+=(uint32_t)d[2];acc[3]+=(uint32_t)d[3];
        const uint32_t inv_j=inv_acc,q_j=q_acc;inv_acc+=(uint32_t)w->scale_step;q_acc+=w->du;
        if(t>H||b>H)return -3;
        if(t==0&&b==0)continue;
        int r[4];r[0]=s16bits(c0,8);r[1]=s16bits(c1,8);r[2]=s16bits(c2,8);r[3]=s16bits(c3,8);
        uint16_t inv=(uint16_t)inv_j;
        int low=(v==1||v==3)?r[1]:r[2],fs=(v==0||v==2)?r[1]:(l?r[3]:r[2]);
        if(c)fill(f,x,t,b,t,r[0],(uint8_t)w->ceiling,has(skies,v)?sky:NULL,packed==2);
        if(w->textured&&(u||l)){
            uint32_t q=q_j;
            if(!w->linear&&!inv)return -4;
            int offset=(int)((w->linear?q:q/inv)&0x1f80u)+sar(w->z,1);
            const int16_t *sc=scalers+(indices?indices[inv>>5]:(inv>>5))*H;
            if(u&&tex(f,x,t,b,r[0],r[1],upper,offset,sc,packed))return -2;
            if(l&&tex(f,x,t,b,low,r[3],lower,offset,sc,packed))return -2;
        }
        if(fl){int color=((v==11||v==17)&&t>=r[2]&&b>=r[3])?0:w->floor;fill(f,x,t,b,fs,b,(uint8_t)color,NULL,packed==2);}
        if(v<=3){f->top[x]=f->bottom[x]=0;f->depth[x]=inv;}
        else {
            int et=u?r[1]:(c?r[0]:t),eb=l?low:(fl?fs:b);
            f->top[x]=(uint16_t)min(b,max(t,et));f->bottom[x]=(uint16_t)max(t,min(b,eb));
            if((c&&b<et)||(fl&&t>=eb)){f->top[x]=f->bottom[x]=0;f->depth[x]=inv;}
        }
    }
    return 0;
}
int fr_wall(Frame *f,const WallJob *w,Asset upper,Asset lower,const int16_t *scalers,const uint8_t *sky){
    return wall_impl(f,w,upper,lower,scalers,sky,0,NULL);
}
/* Same geometry and clipping, packed 4bpp data read directly from ROM.
 * origin remains in logical expanded-byte coordinates (normally 8192).
 */
int fr_wall_packed(Frame *f,const WallJob *w,Asset upper,Asset lower,const int16_t *scalers,const uint8_t *sky){
    return wall_impl(f,w,upper,lower,scalers,sky,1,NULL);
}
/* 158 unique rows, 2048 byte indices, instead of a 288 KiB dense table. */
int fr_wall_indexed(Frame *f,const WallJob *w,Asset upper,Asset lower,const int16_t *rows,const uint8_t *indices,const uint8_t *sky){
    return wall_impl(f,w,upper,lower,rows,sky,1,indices);
}
/* Full byte per sample: independent left/right palette nibbles, same geometry. */
int fr_wall_indexed_pair(Frame *f,const WallJob *w,Asset upper,Asset lower,const int16_t *rows,const uint8_t *indices,const uint8_t *sky){
    return wall_impl(f,w,upper,lower,rows,sky,2,indices);
}
/* Public projection takes transformed endpoints, near rule, and resource U coordinates.
 * Return 1 for visible, 0 for rejected, negative for unrepresentable division.
 */
static int divword(int32_t a,int32_t b,int32_t *out){
    if(!b)return -1;
    int64_t q=(int64_t)a/b;if(q<-32768||q>32767)return -1;
    *out=(int32_t)q;return 0;
}
#define DIVSUB(dst,delta,num,den) do {int32_t q_;if(divword(s16(delta)*(num),(den),&q_))return -5;(dst)=s16((dst)-q_);}while(0)
int fr_project(int32_t x0,int32_t z0,int32_t x1,int32_t z1,int32_t near,int32_t u0,int32_t u1,WallJob *w){
    int textured=near&1;int32_t l0=s16(x0+z0),r1,l1,r0,den,q0,q1;
    w->textured=textured;w->linear=0;w->u0=w->du=0;
    if(l0<0){l1=s16(x1+z1);if(l1<0)return 0;den=s16(l1-l0);
        if(textured)DIVSUB(u0,u1-u0,l0,den);
        DIVSUB(x0,x1-x0,l0,den);z0=s16(-x0);}
    r1=s16(z1-x1);
    if(r1<0){r0=s16(z0-x0);if(r0<0)return 0;den=s16(r0-r1);
        DIVSUB(x1,x0-x1,r1,den);if(textured)DIVSUB(u1,u0-u1,r1,den);z1=x1;}
    z0=s16(z0-near);z1=s16(z1-near);
    if(z0<0){if(z1<0)return 0;den=s16(z0-z1);
        if(textured)DIVSUB(u0,u0-u1,z0,den);
        DIVSUB(x0,x0-x1,z0,den);z0=0;}
    else if(z1<0){den=s16(z0-z1);if(textured)DIVSUB(u1,u0-u1,z1,den);
        DIVSUB(x1,x0-x1,z1,den);z1=0;}
    z0=s16(z0+near);z1=s16(z1+near);
    if(divword(x0*80,z0,&q0)||divword(x1*80,z1,&q1))return -5;
    w->x0=max(0,s16(q0+80));int xend=min(W,s16(q1+80));w->width=s16(xend-w->x0);
    if(w->width<=0)return 0;
    if(!z0||!z1)return -5;
    w->inv0=0x500000/(uint16_t)z0;w->inv1=0x500000/(uint16_t)z1;
    if(w->inv0>65535||w->inv1>65535||divword(w->inv1-w->inv0,w->width,&w->scale_step))return -5;
    if(textured){
        uint32_t a=((uint32_t)u0<<7)&65535u,b=((uint32_t)u1<<7)&65535u;
        uint32_t p0=a*(uint32_t)w->inv0,p1=b*(uint32_t)w->inv1,mi=(w->inv0+w->inv1)/2;
        if(!mi)return -5;
        uint32_t ap=(uint32_t)(((uint64_t)p0+p1)/2/mi),mu=(a+b)/2;
        if(ap>65535)return -5;
        uint32_t er=(mu-ap)&65535u;if(s16(mu)<s16(ap))er=(-er)&65535u;
        w->linear=er<512||((er-512)&65535u)<10000000u/mi;
        uint32_t left=w->linear?a:p0,right=w->linear?b:p1;
        w->u0=left;w->du=(uint32_t)(((int64_t)right-left)/w->width);
    }
    return 1;
}
#undef DIVSUB
/* Portable transformed vertex, with explicit 16-bit wrap. */
void fr_transform(int32_t x,int32_t y,int32_t cx,int32_t cy,int32_t co,int32_t si,int32_t *tx,int32_t *tz){
    int32_t dx=s16(s16((int64_t)x*8)-cx),dy=s16(s16((int64_t)y*8)-cy);
    /* |dx|,|dy|<=32768 and |co|,|si|<=16384: each product fits 31 bits; only bits 14..29 of the sum are used, so wrapping 32-bit math is exact */
    *tx=s16bits((uint32_t)(dx*co)-(uint32_t)(dy*si),14);
    *tz=s16bits((uint32_t)(dx*si)+(uint32_t)(dy*co),14);
}


/* Native sprite ABI: decoded column ranges and opaque spans, not ROM pointers.
 * Offsets are relative to an asset origin; per-scale numeric tables are supplied
 * by the caller. Column offsets are indexes into the span array.
 */
typedef struct { int32_t offset; int16_t lo,hi; } SpriteSpan;
typedef struct { uint32_t first,count; } SpriteColumn;
typedef struct {
    int32_t width,origin;
    Asset pixels;
    const SpriteColumn *columns;
    const SpriteSpan *spans;
    uint32_t span_count;
} Sprite;
typedef struct { const Sprite *sprite; int32_t dx,dy; } SpritePart;
typedef struct { uint32_t writes,tags,projected,overflow; } SpriteStats;
typedef struct { int32_t left,right,x0,x1; uint32_t step,u,scale,overflow; } SpriteJob;
/* 68000 DIVS.W leaves destination unchanged on signed quotient overflow. */
static int32_t sprite_div(int32_t n,int32_t d,uint32_t *overflow){
    int64_t q=(int64_t)n/d;
    if(q < -32768 || q > 32767){*overflow=1;return n;}
    return (int32_t)q;
}
int fr_sprite_project(int32_t width,int32_t origin,int32_t tx,int32_t tz,SpriteJob *j){
    j->left=j->right=j->x0=j->x1=0;
    j->step=j->u=j->scale=j->overflow=0;
    tz=s16(tz);if(tz<81)return 0;
    if(width<=0||width>32767)return -1;
    int32_t l=s16(tx-s16((int64_t)origin*8)),r=s16(l+s16((int64_t)width*8));
    r=s16(sprite_div(r*80,tz,&j->overflow)+80);if(r<0)return 0;
    l=s16(sprite_div(l*80,tz,&j->overflow)+80);if(l>=W)return 0;
    int n=s16(r-l);if(n<=0)return 0;
    j->step=((uint32_t)width*2u<<16)/(uint32_t)n;
    j->u=l<0?(uint32_t)(-l)*j->step:0;
    j->scale=(uint16_t)sprite_div(0x500000,tz,&j->overflow);
    j->left=l;j->right=r;j->x0=max(0,l);j->x1=min(W,r);
    return j->x0<j->x1;
}
int fr_sprite(Frame *f,const Sprite *s,int32_t tx,int32_t tz,int32_t delta,uint16_t tag,
              const int16_t *factors,const int16_t *scalers,SpriteStats *st){
    st->writes=st->tags=st->projected=st->overflow=0;
    if(!s||!s->columns||!factors||!scalers)return -1;
    SpriteJob j;int ret=fr_sprite_project(s->width,s->origin,tx,tz,&j);
    if(ret<=0)return ret;
    st->projected=1;st->overflow=j.overflow;
    int factor=factors[j.scale>>5];const int16_t *sc=scalers+(j.scale>>5)*H;
    int32_t eye=s16((int64_t)delta*64);
    for(int x=j.x0;x<j.x1;x++){
        uint32_t col=((j.u>>16)&0xfffeu)/2u;j.u+=j.step;
        if(j.scale<f->depth[x])continue;
        if(col>=(uint32_t)s->width)return -2;
        if(tag){f->owner[x]=tag;st->tags++;}
        SpriteColumn c=s->columns[col];
        if(c.first>s->span_count||c.count>s->span_count-c.first||(c.count&&!s->spans))return -2;
        for(uint32_t i=0;i<c.count;i++){
            SpriteSpan p=s->spans[c.first+i];
            if(p.lo>=p.hi)return -2;
            int a=max(-144,s16(sar((int64_t)s16(p.lo-eye)*factor,16))&~3);
            int b=min(144,s16(sar((int64_t)s16(p.hi-eye)*factor,16))&~3);
            for(int y=36+a/4;y<36+b/4;y++){
                uint8_t v;if(sample(s->pixels,(int64_t)delta+p.offset+sc[y],&v))return -3;
                f->pixels[pixel(x,y)]=v;st->writes++;
            }
        }
    }
    return 1;
}
int fr_composite(Frame *f,const SpritePart *parts,uint32_t n,int32_t tx,int32_t tz,int32_t delta,uint16_t tag,
                 const int16_t *factors,const int16_t *scalers,SpriteStats *st){
    st->writes=st->tags=st->projected=st->overflow=0;if(n>256||(!parts&&n))return -1;
    for(uint32_t i=0;i<n;i++){
        SpriteStats p;int ret=fr_sprite(f,parts[i].sprite,s16(tx-s16((int64_t)parts[i].dx*8)),tz,
                                       s16(delta+parts[i].dy),tag,factors,scalers,&p);
        if(ret<0)return ret;
        st->writes+=p.writes;st->tags+=p.tags;st->projected+=p.projected;st->overflow+=p.overflow;
    }
    return 0;
}
typedef struct { uint32_t id; int32_t key; } SpriteOrder;
void fr_sprite_order(SpriteOrder *a,uint32_t n){
    if(!a||n<2)return;
    for(uint32_t i=n-1;i>0;i--){
        if(a[i-1].key>a[i].key){SpriteOrder t=a[i-1];a[i-1]=a[i];a[i]=t;}
    }
}
/* Graphics-only Q14 door motion. Game code owns collision and trigger logic. */
int fr_door_phase(int32_t phase,int32_t speed,int32_t ticks,int32_t *out_phase,int32_t *out_speed){
    int32_t p=s16(phase+(int64_t)s16(speed)*s16(ticks));
    if(p>=16384){p=16384;speed=0;}else if(p<=0){p=0;speed=0;}
    *out_phase=p;*out_speed=speed;return p<16384;
}
int32_t fr_door_lerp(int32_t a,int32_t b,int32_t phase){return s16(a+sar((int64_t)(b-a)*phase,14));}
