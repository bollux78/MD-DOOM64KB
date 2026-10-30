/* R99: exact 0xffffffffu / v. v < 65536: unchanged C division. v >= 65536: the libgcc
 * __udivsi3 big-divisor algorithm with its shift loop replaced by a computed shift
 * (same normalisation, one DIVU, same single correction), so identical results. */
static const uint8_t r99_bitlen8[256]={0,1,2,2,3,3,3,3,4,4,4,4,4,4,4,4,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,
6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,
8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8,8};
static inline uint32_t R99_Recip(uint32_t v)
{
    if (v < 0x10000u) return 0xffffffffu / v;
    const uint16_t hi = (uint16_t)(v >> 16);
    const uint8_t s = (hi >> 8) ? (uint8_t)(8 + r99_bitlen8[hi >> 8]) : r99_bitlen8[hi];
    const uint16_t d = (uint16_t)(v >> s);
    uint32_t q = (uint16_t)((0xffffffffu >> s) / d);           /* one DIVU.W, quotient < 65536 */
    const uint32_t lo = (uint32_t)(uint16_t)v * (uint16_t)q;    /* MULU.W */
    const uint32_t hp = (uint32_t)hi * (uint16_t)q;             /* MULU.W */
    if (hp > 0xffffu) q--;
    else { const uint32_t p = lo + (hp << 16); if (p < lo) q--; }  /* p <= 0xffffffff always: no > check needed */
    return q;
}
