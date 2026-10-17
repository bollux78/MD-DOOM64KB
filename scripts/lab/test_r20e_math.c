#include <stdint.h>
#include "r20_scale_math.h"
static uint32_t state = 20261017u;
static uint32_t rnd(void) { state ^= state<<13; state ^= state>>17; state ^= state<<5; return state; }
int main(void)
{
    static const int32_t sine_edges[] = {-65536,-65535,-32769,-32768,-32767,-1,0,1,32767,32768,32769,65534,65535};
    static const int16_t a_edges[] = {-32768,-32767,-16384,-1,0,1,22,16384,32766,32767};
    for (int32_t a=-32768; a<32768; a++)
      for (unsigned j=0;j<sizeof(sine_edges)/sizeof(*sine_edges);j++)
        if ((uint32_t)R20_ScaleProduct((int16_t)a,sine_edges[j]) != (uint32_t)((int64_t)a*sine_edges[j])) return 1;
    for (int32_t b=-65536; b<65536; b++)
      for (unsigned j=0;j<sizeof(a_edges)/sizeof(*a_edges);j++)
        if ((uint32_t)R20_ScaleProduct(a_edges[j],b) != (uint32_t)((int64_t)a_edges[j]*b)) return 2;
    for (uint32_t d=1; d<0x1000000u; d++)
        if (R20_ScaleReciprocal(d) != 0xffffffffu/d) return 3;
    for (unsigned k=0;k<32;k++) {
      uint32_t p=1u<<k;
      for (uint32_t delta=0;delta<512;delta++) {
        uint32_t a=p+delta,b=p-delta;
        if (a && R20_ScaleReciprocal(a)!=0xffffffffu/a) return 4;
        if (b && R20_ScaleReciprocal(b)!=0xffffffffu/b) return 5;
      }
    }
    for (uint32_t i=0;i<2000000;i++) {
      uint32_t d=rnd(); if (!d) d=1;
      if (R20_ScaleReciprocal(d)!=0xffffffffu/d) return 6;
    }
    return 0;
}
