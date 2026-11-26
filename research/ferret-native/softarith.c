/* Freestanding 68000-safe integer helpers (replaces libgcc: the distro libgcc for m68k-linux is built for 68020+
 * and contains 'bsr.l' (opcode 61FF), which raises an address error on a real 68000). Only shifts by 1 and
 * add/sub/compare are used so the compiler never calls a helper from inside a helper. */
#include <stdint.h>
/* 16x16 -> 32 products map to a single MULU.W each */
static inline uint32_t mulu16(uint16_t a,uint16_t b){uint32_t r=a;__asm__("mulu.w %1,%0":"+d"(r):"dmi"(b):"cc");return r;}
uint32_t __mulsi3(uint32_t a,uint32_t b){
    const uint16_t ah=(uint16_t)(a>>16),al=(uint16_t)a,bh=(uint16_t)(b>>16),bl=(uint16_t)b;
    return mulu16(al,bl)+((mulu16(ah,bl)+mulu16(al,bh))<<16);
}
/* n / d with d < 65536 using DIVU.W twice (68000: 32/16 -> 16:16, quotient must fit in 16 bits) */
static inline uint32_t divu_w(uint32_t n,uint16_t d){__asm__("divu.w %1,%0":"+d"(n):"dmi"(d):"cc");return n;}
static uint32_t udm32_small(uint32_t n,uint16_t d,uint32_t *rem){
    uint32_t t=divu_w(n>>16,d);               /* high half: quotient in low word, remainder in high word */
    uint32_t qh=t&0xffffu,r=t>>16;
    t=divu_w((r<<16)|(n&0xffffu),d);
    *rem=t>>16;return (qh<<16)|(t&0xffffu);
}
static uint32_t udm32(uint32_t n,uint32_t d,uint32_t *rem){
    if(!d){*rem=n;return 0xffffffffu;}
    if(d<0x10000u)return udm32_small(n,(uint16_t)d,rem);
    uint32_t q=0,r=0;
    for(int i=31;i>=0;i--){r=(r<<1)|((n>>i)&1u);q<<=1;if(r>=d){r-=d;q|=1u;}}
    *rem=r;return q;
}
uint32_t __udivsi3(uint32_t n,uint32_t d){uint32_t r;return udm32(n,d,&r);}
uint32_t __umodsi3(uint32_t n,uint32_t d){uint32_t r;udm32(n,d,&r);return r;}
int32_t __divsi3(int32_t n,int32_t d){uint32_t r;uint32_t un=n<0?0u-(uint32_t)n:(uint32_t)n,ud=d<0?0u-(uint32_t)d:(uint32_t)d;uint32_t q=udm32(un,ud,&r);return ((n<0)!=(d<0))?(int32_t)(0u-q):(int32_t)q;}
int32_t __modsi3(int32_t n,int32_t d){uint32_t r;uint32_t un=n<0?0u-(uint32_t)n:(uint32_t)n,ud=d<0?0u-(uint32_t)d:(uint32_t)d;udm32(un,ud,&r);return n<0?(int32_t)(0u-r):(int32_t)r;}
/* 64-bit helpers. Fast paths avoid the bit loops: a 32x32->64 product is four MULU.W. */
static uint64_t mul32x32(uint32_t a,uint32_t b){
    const uint16_t ah=(uint16_t)(a>>16),al=(uint16_t)a,bh=(uint16_t)(b>>16),bl=(uint16_t)b;
    const uint32_t p0=mulu16(al,bl),p1=mulu16(al,bh),p2=mulu16(ah,bl),p3=mulu16(ah,bh);
    uint32_t mid=p1+p2,carry=(mid<p1)?1u:0u;                 /* mid may wrap: keep the carry (worth 2^48) */
    uint32_t lo=p0+(mid<<16),hi=p3+(mid>>16)+(carry<<16)+((lo<p0)?1u:0u);
    return ((uint64_t)hi<<32)|lo;
}
uint64_t __muldi3(uint64_t a,uint64_t b){
    const uint32_t ah=(uint32_t)(a>>32),al=(uint32_t)a,bh=(uint32_t)(b>>32),bl=(uint32_t)b;
    uint64_t r=mul32x32(al,bl);
    const uint32_t cross=__mulsi3(ah,bl)+__mulsi3(al,bh);   /* only the low 32 bits matter: they land in the high word */
    return r+((uint64_t)cross<<32);
}
static uint64_t udm64(uint64_t n,uint64_t d,uint64_t *rem){
    if(!d){*rem=n;return ~0ull;}
    if(!(n>>32)&&!(d>>32)){uint32_t r32;uint32_t q=udm32((uint32_t)n,(uint32_t)d,&r32);*rem=r32;return q;}
    uint32_t nh=(uint32_t)(n>>32),nl=(uint32_t)n;
    uint64_t q=0,r=0;
    for(int i=0;i<64;i++){
        const uint32_t top=nh>>31;                           /* shift the dividend left by 1 through both halves */
        nh=(nh<<1)|(nl>>31);nl<<=1;
        r=(r<<1)|top;q<<=1;if(r>=d){r-=d;q|=1u;}
    }
    *rem=r;return q;
}
uint64_t __udivdi3(uint64_t n,uint64_t d){uint64_t r;return udm64(n,d,&r);}
uint64_t __umoddi3(uint64_t n,uint64_t d){uint64_t r;udm64(n,d,&r);return r;}
int64_t __divdi3(int64_t n,int64_t d){uint64_t r;uint64_t un=n<0?0ull-(uint64_t)n:(uint64_t)n,ud=d<0?0ull-(uint64_t)d:(uint64_t)d;uint64_t q=udm64(un,ud,&r);return ((n<0)!=(d<0))?(int64_t)(0ull-q):(int64_t)q;}
int64_t __moddi3(int64_t n,int64_t d){uint64_t r;uint64_t un=n<0?0ull-(uint64_t)n:(uint64_t)n,ud=d<0?0ull-(uint64_t)d:(uint64_t)d;udm64(un,ud,&r);return n<0?(int64_t)(0ull-r):(int64_t)r;}
