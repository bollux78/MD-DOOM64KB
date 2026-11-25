/* Ferret-derived independent scalar reference, v0.
 * No original executable code, hardcoded ROM addresses or game state.
 * Host C implementation first; target memory layout/assembly are separate work.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
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
static int32_t min(int32_t a,int32_t b){return a<b?a:b;}
static int32_t max(int32_t a,int32_t b){return a>b?a:b;}
static int32_t sar(int64_t n,unsigned bits){int64_t d=(int64_t)1<<bits;return (int32_t)(n>=0?n/d:-((-n+d-1)/d));}
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
static int fill(Frame *f,int x,int t,int b,int lo,int hi,uint8_t c,const uint8_t *sky){
    for(int y=max(t,lo);y<min(b,hi);y++)f->pixels[pixel(x,y)]=sky?sky[x*H+y]:c;
    return 0;
}
static int tex(Frame *f,int x,int t,int b,int lo,int hi,Asset a,int offset,const int16_t *sc){
    for(int y=max(t,lo);y<min(b,hi);y++){
        uint8_t c;if(sample(a,(int64_t)offset+sc[y],&c))return -2;
        f->pixels[pixel(x,y)]=c;
    }
    return 0;
}
/* Offset table is pure numeric data, indexed by (scale >> 5), 72 entries per row.
 * sky is a caller-supplied visible 160x72 column-major sample array.
 * Assets provide a bounded byte view and a logical texture origin.
 */
int fr_wall(Frame *f,const WallJob *w,Asset upper,Asset lower,const int16_t *scalers,const uint8_t *sky){
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
    for(int j=0;j<n;j++){
        int x=w->x0+j,t=f->top[x],b=f->bottom[x];
        if(t>H||b>H)return -3;
        if(t==0&&b==0)continue;
        int r[4];for(int k=0;k<4;k++)r[k]=s16(sar((int64_t)e[k]+(int64_t)d[k]*j,8));
        uint16_t inv=(uint16_t)(w->inv0+w->scale_step*j);
        int low=(v==1||v==3)?r[1]:r[2],fs=(v==0||v==2)?r[1]:(l?r[3]:r[2]);
        if(c)fill(f,x,t,b,t,r[0],(uint8_t)w->ceiling,has(skies,v)?sky:NULL);
        if(w->textured&&(u||l)){
            uint32_t q=w->u0+w->du*(uint32_t)j;
            if(!w->linear&&!inv)return -4;
            int offset=(int)((w->linear?q:q/inv)&0x1f80u)+sar(w->z,1);
            const int16_t *sc=scalers+(inv>>5)*H;
            if(u&&tex(f,x,t,b,r[0],r[1],upper,offset,sc))return -2;
            if(l&&tex(f,x,t,b,low,r[3],lower,offset,sc))return -2;
        }
        if(fl){int color=((v==11||v==17)&&t>=r[2]&&b>=r[3])?0:w->floor;fill(f,x,t,b,fs,b,(uint8_t)color,NULL);}
        if(v<=3){f->top[x]=f->bottom[x]=0;f->depth[x]=inv;}
        else {
            int et=u?r[1]:(c?r[0]:t),eb=l?low:(fl?fs:b);
            f->top[x]=(uint16_t)min(b,max(t,et));f->bottom[x]=(uint16_t)max(t,min(b,eb));
            if((c&&b<et)||(fl&&t>=eb)){f->top[x]=f->bottom[x]=0;f->depth[x]=inv;}
        }
    }
    return 0;
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
    *tx=s16(sar((int64_t)dx*co-(int64_t)dy*si,14));
    *tz=s16(sar((int64_t)dx*si+(int64_t)dy*co,14));
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
    memset(j,0,sizeof(*j));
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
    memset(st,0,sizeof(*st));
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
    memset(st,0,sizeof(*st));if(n>256||(!parts&&n))return -1;
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
