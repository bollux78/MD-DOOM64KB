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
uint64_t __muldi3(uint64_t a,uint64_t b){
    uint32_t al=(uint32_t)a,bl=(uint32_t)b,ah=(uint32_t)(a>>32),bh=(uint32_t)(b>>32);
    uint32_t p00=mulu16((uint16_t)al,(uint16_t)bl);
    uint32_t p01=mulu16((uint16_t)al,(uint16_t)(bl>>16));
    uint32_t p10=mulu16((uint16_t)(al>>16),(uint16_t)bl);
    uint32_t hi=mulu16((uint16_t)(al>>16),(uint16_t)(bl>>16))+(p01>>16)+(p10>>16);
    uint32_t lo=p00,t=lo+(p01<<16);hi+=(t<lo);lo=t;
    t=lo+(p10<<16);hi+=(t<lo);lo=t;
    hi+=__mulsi3(ah,bl)+__mulsi3(al,bh);
    return ((uint64_t)hi<<32)|lo;
}
static uint64_t udm64(uint64_t n,uint64_t d,uint64_t *rem){
    if(!d){*rem=n;return ~0ull;}
    uint64_t q=0,r=0;
    if((n>>32)==0 && (d>>32)==0){
        uint32_t rem32,q32=udm32((uint32_t)n,(uint32_t)d,&rem32);
        *rem=rem32;return q32;
    }
    /* Restoring division: stream the dividend bits in 64 steps, rather
       than recomputing each bit by up to 63 single shifts. */
    for(unsigned i=0;i<64;i++){
        uint64_t carry=r>>63;
        r=(r<<1)|(n>>63);n<<=1;q<<=1;
        if(carry||r>=d){r-=d;q|=1u;}
    }
    *rem=r;return q;
}
uint64_t __udivdi3(uint64_t n,uint64_t d){uint64_t r;return udm64(n,d,&r);}
uint64_t __umoddi3(uint64_t n,uint64_t d){uint64_t r;udm64(n,d,&r);return r;}
int64_t __divdi3(int64_t n,int64_t d){uint64_t r;uint64_t un=n<0?0ull-(uint64_t)n:(uint64_t)n,ud=d<0?0ull-(uint64_t)d:(uint64_t)d;uint64_t q=udm64(un,ud,&r);return ((n<0)!=(d<0))?(int64_t)(0ull-q):(int64_t)q;}
int64_t __moddi3(int64_t n,int64_t d){uint64_t r;uint64_t un=n<0?0ull-(uint64_t)n:(uint64_t)n,ud=d<0?0ull-(uint64_t)d:(uint64_t)d;udm64(un,ud,&r);return n<0?(int64_t)(0ull-r):(int64_t)r;}
