/* FRV2 zero-allocation reader, portable to 68000.
 * The input blob is immutable and validated once. Iterator keeps only a
 * bounded stack; leaf masks are read in place from ROM.
 */
#include <stdint.h>
#include <stddef.h>
#define FR_STACK 64
typedef struct { const uint8_t *blob,*cells,*masks,*nodes; uint16_t nc,ns,nm,nn,stride; } FRV;
typedef struct { const FRV *v; const int16_t *planes; const uint8_t *mask; int16_t x,y; uint16_t np,sp,stack[FR_STACK]; uint32_t tests,visits; } FRIter;
/* FRV2 masks have byte granularity; a DAG node can start at an odd address.
 * On 68000 explicitly preserve byte accesses: no compiler load combining.
 * This is not a format change and leaves host semantics identical. */
static uint16_t be16(const uint8_t *p){
#ifdef __m68k__
    if(!((uintptr_t)p&1u))return *(const volatile uint16_t *)(const volatile void *)p; /* even: one big-endian word read */
    const volatile uint8_t *q=p;                                                   /* odd: two byte reads (no address error) */
    uint16_t hi=q[0],lo=q[1];
    return (uint16_t)((hi<<8)|lo);
#else
    return (uint16_t)((uint16_t)p[0]<<8|p[1]);
#endif
}
static uint32_t be32(const uint8_t *p){return ((uint32_t)be16(p)<<16)|be16(p+2);}
static int valid_ref(uint16_t r,uint16_t nc,uint16_t nn){return r==65535u||(r&32768u?(r&32767u)<nc:r<nn);}
int frv_open(FRV *v,const uint8_t *b,size_t n){
    if(!v||!b||n<16||(b[0]!='F'||b[1]!='R'||b[2]!='V'||b[3]!='2'))return -1;
    uint16_t nc=be16(b+4),ns=be16(b+6),nm=be16(b+8),nn=be16(b+10);
    uint32_t mb=be32(b+12),stride=((uint32_t)ns+7)/8,cb=(uint32_t)nc*12,nb=(uint32_t)nn*8;
    if(!nc||nc>=32767||!ns||!nm||nn>=32767||mb!=stride*nm)return -2;
    if(cb>n-16||mb>n-16-cb||nb!=n-16-cb-mb)return -2;
    v->blob=b;v->cells=b+16;v->masks=v->cells+cb;v->nodes=v->masks+mb;
    v->nc=nc;v->ns=ns;v->nm=nm;v->nn=nn;v->stride=(uint16_t)stride;
    for(uint16_t i=0;i<nc;i++){
        const uint8_t *p=v->cells+12u*i;
        if(be16(p+8)>=nm||!valid_ref(be16(p+10),nc,nn))return -3;
    }
    for(uint16_t i=0;i<nn;i++){
        const uint8_t *p=v->nodes+8u*i;uint16_t op=be16(p);
        /* Interning emits children before parents; reject cycles. */
        if((op!=1&&op!=2)||!valid_ref(be16(p+4),nc,i)||!valid_ref(be16(p+6),nc,i))return -4;
    }
    return 0;
}
int frv_begin(FRIter *it,const FRV *v,uint16_t cell,int16_t x,int16_t y,const int16_t *planes,uint16_t np){
    if(!it||!v||cell>=v->nc||(!planes&&np))return -1;
    const uint8_t *p=v->cells+12u*cell;
    if(x<(int16_t)be16(p)||y<(int16_t)be16(p+2)||x>(int16_t)be16(p+4)||y>(int16_t)be16(p+6))return 0;
    it->v=v;it->planes=planes;it->np=np;it->x=x;it->y=y;it->sp=1;it->stack[0]=be16(p+10);
    it->mask=v->masks+(uint32_t)be16(p+8)*v->stride;it->tests=it->visits=0;return 1;
}
int frv_keep(const FRIter *it,uint16_t seg){return seg<it->v->ns&&((it->mask[seg>>3]>>(seg&7))&1);}
int frv_next(FRIter *it,uint16_t *leaf){
    while(it->sp){
        uint16_t ref=it->stack[--it->sp];
        if(ref==65535u)continue;
        if(ref&32768u){*leaf=ref&32767u;return 1;}
        if(++it->visits>2u*it->v->nc+it->v->nn)return -2;
        const uint8_t *p=it->v->nodes+8u*ref;
        uint16_t a=be16(p+4),b=be16(p+6);
        if(be16(p)==2){
            uint16_t i=be16(p+2);if(i>=it->np)return -3;
            const int16_t *q=it->planes+4u*i;
            /* 64-bit only for full coordinate range; replace with bounded
               32-bit target specialization after map range validation. */
            int32_t sa=(int32_t)q[2]*((int32_t)it->y-q[1]),sb=(int32_t)q[3]*((int32_t)it->x-q[0]); /* each < 2^31 */
            if(sa>=sb){uint16_t t=a;a=b;b=t;}it->tests++;
        }
        if(it->sp>FR_STACK-2)return -4;
        it->stack[it->sp++]=b;it->stack[it->sp++]=a;
    }
    return 0;
}
/* One-shot test adapter; runtime uses the iterator directly. */
int frv_collect(const uint8_t *blob,size_t size,uint16_t cell,int16_t x,int16_t y,const int16_t *planes,uint16_t np,uint16_t *leaves,uint16_t cap,uint8_t *keep,uint32_t *tests){
    FRV v;FRIter it;int rc=frv_open(&v,blob,size);if(rc)return rc;
    rc=frv_begin(&it,&v,cell,x,y,planes,np);if(rc!=1)return -10;
    for(uint16_t i=0;i<v.ns;i++)keep[i]=(uint8_t)frv_keep(&it,i);
    uint16_t n=0,l;
    while((rc=frv_next(&it,&l))>0){if(n>=cap)return -11;leaves[n++]=l;}
    *tests=it.tests;return rc<0?rc:n;
}
