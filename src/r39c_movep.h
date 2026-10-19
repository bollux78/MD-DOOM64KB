/* R39c: MC68000 MOVEP accesses for 8-bit cartridge SRAM on odd byte lanes.
 * MOVEP uses address A+0,A+2,A+4,A+6, preserving big-endian byte order.
 * Callers must enable SRAM through R25_SRAM_BEGIN and restore afterwards.
 * These are experimental routines; never use for contiguous work RAM. */
#ifndef R39C_MOVEP_H
#define R39C_MOVEP_H
#include <stdint.h>
static inline uint32_t R39C_MovepRead32(uint32_t address)
{
    const volatile uint8_t *p=(const volatile uint8_t*)(uintptr_t)address;
    uint32_t value;
    __asm__ volatile("movep.l 0(%1),%0" : "=d"(value) : "a"(p) : "memory");
    return value;
}
static inline uint16_t R39C_MovepRead16(uint32_t address)
{
    const volatile uint8_t *p=(const volatile uint8_t*)(uintptr_t)address;
    uint16_t value;
    __asm__ volatile("movep.w 0(%1),%0" : "=d"(value) : "a"(p) : "memory");
    return value;
}
static inline void R39C_MovepWrite32(uint32_t address,uint32_t value)
{
    volatile uint8_t *p=(volatile uint8_t*)(uintptr_t)address;
    __asm__ volatile("movep.l %1,0(%0)" : : "a"(p), "d"(value) : "memory");
}
static inline void R39C_MovepWrite16(uint32_t address,uint16_t value)
{
    volatile uint8_t *p=(volatile uint8_t*)(uintptr_t)address;
    __asm__ volatile("movep.w %1,0(%0)" : : "a"(p), "d"(value) : "memory");
}
#endif
