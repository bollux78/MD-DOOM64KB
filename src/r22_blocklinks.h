#ifndef R22_BLOCKLINKS_H
#define R22_BLOCKLINKS_H
#if defined(DOOM_R22_SRAM_BLOCKLINKS)
#include <stdint.h>
#include "globdata.h"
#if defined(DOOM_SRAM_CACHE16)
#error SRAM blocklinks and legacy SRAM texture cache share cartridge storage
#endif
#define R22_SRAM_BASE 0x00200000UL
#define R22_SRAM_CAPACITY 16384u
#ifndef R22_SRAM_BYTE
#define R22_SRAM_BYTE(address) (*(volatile uint8_t*)(uintptr_t)(address))
#endif
#ifndef R22_SRAM_ENABLE
#define R22_SRAM_ENABLE() (*(volatile uint8_t*)0x00A130F1UL=1)
#endif
#if defined(DOOM_R25_MUSIC)
#ifndef R22_SRAM_DISABLE
#define R22_SRAM_DISABLE() (*(volatile uint8_t*)0x00A130F1UL=0)
#endif
#define R25_SRAM_BEGIN() do { __asm__ volatile("" ::: "memory"); R22_SRAM_ENABLE(); __asm__ volatile("" ::: "memory"); } while(0)
#define R25_SRAM_END() do { __asm__ volatile("" ::: "memory"); R22_SRAM_DISABLE(); __asm__ volatile("" ::: "memory"); } while(0)
#else
#define R25_SRAM_BEGIN() ((void)0)
#define R25_SRAM_END() ((void)0)
#endif
extern uint16_t r22_block_cells;
void R22_BlockInit(uint16_t w,uint16_t h);
/* Aligned tokens identify SRAM head slots. Never dereference these tokens
   as C pointers: each32-bit value lives on four odd-lane byte addresses. */
static inline mobj_t **R22_BlockSlot(uint16_t index){
    return (mobj_t**)(uintptr_t)(R22_SRAM_BASE+((uint32_t)index<<3));
}
static inline uint32_t R22_SramRead32(uint32_t a){
    R25_SRAM_BEGIN();
    uint32_t value=((uint32_t)R22_SRAM_BYTE(a+1)<<24)|((uint32_t)R22_SRAM_BYTE(a+3)<<16)|
           ((uint32_t)R22_SRAM_BYTE(a+5)<<8)|R22_SRAM_BYTE(a+7);
    R25_SRAM_END();return value;
}
static inline void R22_SramWrite32(uint32_t a,uint32_t v){
    R25_SRAM_BEGIN();
    R22_SRAM_BYTE(a+1)=v>>24;R22_SRAM_BYTE(a+3)=v>>16;
    R22_SRAM_BYTE(a+5)=v>>8;R22_SRAM_BYTE(a+7)=v;
    R25_SRAM_END();
}
static inline int R22_IsSramLink(mobj_t **p){
    return (uintptr_t)p>=R22_SRAM_BASE && (uintptr_t)p<R22_SRAM_BASE+R22_SRAM_CAPACITY*2u;
}
static inline mobj_t *R22_LinkLoad(mobj_t **p){
    return R22_IsSramLink(p)?(mobj_t*)(uintptr_t)R22_SramRead32((uint32_t)(uintptr_t)p):*p;
}
static inline void R22_LinkStore(mobj_t **p,mobj_t *v){
    if(R22_IsSramLink(p))R22_SramWrite32((uint32_t)(uintptr_t)p,(uint32_t)(uintptr_t)v);
    else *p=v;
}
static inline mobj_t *R22_BlockHead(uint16_t i){return R22_LinkLoad(R22_BlockSlot(i));}
#endif
#endif
