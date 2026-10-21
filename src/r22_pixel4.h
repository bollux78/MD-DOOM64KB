/* R22 own packed 4x4 framebuffer primitives. GPL-2.0-or-later. */
#ifndef R22_PIXEL4_H
#define R22_PIXEL4_H
#include <stdint.h>
#define R22_W 76
#define R22_H 44
#if defined(DOOM_R47_PLANE_PAIR)
/* R47B plane-pair: one VDP tilemap word per horizontal pair.
 * Big-endian 68000 memory is [attribute/index high byte][pair low byte],
 * so DMA can copy each 38-word sample row straight to a name table. */
#define R22_PITCH 76
#define R22_FB_BYTES (R22_PITCH * R22_H)
#define R22_PAIR_TILE_BASE 256
static inline uint8_t *R22_PixelByte(uint8_t *p,uint16_t x,uint16_t y) {
#if defined(DOOM_R48_PAIR_V)
    /* V: 22 physical rows, each [38 A words][38 B words].
     * High nibble = upper 4px; low nibble = lower 4px.
     * Plane selection is x parity. Same exact 3344-byte buffer. */
    return p+(uint16_t)(y>>1)*152u+(uint16_t)(x&1u)*76u+
           (uint16_t)(x>>1)*2u+1u;
#else
    return p+y*R22_PITCH+((x>>1)<<1)+1;
#endif
}
static inline const uint16_t *R22_PairRow(const uint8_t *p,uint16_t y) {
    return (const uint16_t *)(const void *)(p+y*R22_PITCH);
}
#else
#define R22_PITCH 38
#define R22_FB_BYTES (R22_PITCH * R22_H)
static inline uint8_t *R22_PixelByte(uint8_t *p,uint16_t x,uint16_t y) {
    return p+y*R22_PITCH+(x>>1);
}
#endif
/* R49: Four 256-pattern banks, all within 0x100..0x4ff.
 * Bank 0/1/2 = exact PAL0 solids; bank 3 = PAL1 tonal pair.
 * The two bits are per-vertical-sample eligibility, stored in the tile
 * INDEX, so neither a scratch bitmap nor a VBlank CPU conversion is needed.
 * Each write preserves the other sample's flag, including clipped spans. */
#if defined(DOOM_R49_COLORMIX)
#if !defined(DOOM_R48_PAIR_V)
#error R49 ColorMix requires Pair-V
#endif
static inline uint8_t R49_TileAttr(uint8_t flags) {
    return (uint8_t)(flags==3u ? 0x24u : 1u+flags);
}
static inline void R49_WriteMixFlag(uint8_t *dst,uint16_t y,uint8_t eligible) {
    uint8_t old=(uint8_t)((dst[-1]&7u)-1u);
    uint8_t flags=(y&1u)?(uint8_t)((old&1u)|(eligible?2u:0u))
                         :(uint8_t)((old&2u)|(eligible?1u:0u));
    dst[-1]=R49_TileAttr(flags);
}
#endif

#define R22_TILES 836
/* 2 independent horizontal samples per byte. */
static inline void R22_Put(uint8_t *p,uint16_t x,uint16_t y,uint8_t c) {
    uint8_t *d=R22_PixelByte(p,x,y); c&=15;
#if defined(DOOM_R48_PAIR_V)
    *d=(y&1u)?(uint8_t)((*d&240)|c):(uint8_t)((*d&15)|(c<<4));
#if defined(DOOM_R49_COLORMIX)
    /* Generic plotters have only a quantized color, not the source Doom
     * index required to pass the RGB fidelity gate: leave it solid. */
    R49_WriteMixFlag(d,y,0);
#endif
#else
    *d=(x&1u)?(uint8_t)((*d&240)|c):(uint8_t)((*d&15)|(c<<4));
#endif
}
static inline uint32_t R22_ExpandPair(uint8_t p) {
    return ((uint32_t)(p>>4)*0x11110000u)|((uint32_t)(p&15)*0x1111u);
}
/* Four equal samples share one immutable solid pattern in VRAM0..15. */
static inline uint16_t R22_TileIndex(uint8_t top,uint8_t bottom,uint16_t dynamic){
    return (top==bottom && (top>>4)==(top&15))?(uint16_t)(top&15):dynamic;
}
#endif
