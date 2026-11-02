#!/usr/bin/env python3
"""R114 diag (on the R113 chain, PERF only, never delivered): zone headroom of every E1 map.

Measures whether a second framebuffer (3,352 B) could come from the Doom zone. At each G_Ticker
in a level it records the minimum total-free and minimum largest-free-block of the zone.
After 140 tics on a map it starts the next one with G_InitNew(sk_hard, map+1) (UV: most things),
demo playback off, rendering skipped (zone use does not depend on rendering). After E1M9 it
calls R114_Done() (noipa; BlastEm breakpoint) and stops. BSS: 2*9*2+2 = 38 B (margin 44).
"""
from pathlib import Path


def rep(f, a, b, n=1):
    p = Path(f); s = p.read_text(); c = s.count(a); assert c == n, (f, a[:80], c); p.write_text(s.replace(a, b))


Z = 'src/z_zone.c'; s = Path(Z).read_text()
s += '''
void R114_ZoneStat(uint16_t *total, uint16_t *largest)
{
    uint32_t t = Z_GetTotalFreeMemory(), l = Z_GetLargestFreeBlockSize();
    *total = t > 65535u ? 65535u : (uint16_t)t; *largest = l > 65535u ? 65535u : (uint16_t)l;
}
'''
Path(Z).write_text(s)
G = 'src/g_game.c'
rep(G, '''void G_Ticker (void)
{
    static gamestate_t prevgamestate = 0;
''', '''uint16_t r114_min_total[9], r114_min_largest[9];
static uint16_t r114_tics;
extern void R114_ZoneStat(uint16_t *total, uint16_t *largest);
void __attribute__((noipa,noinline)) R114_Done(void){ __asm__ volatile("nop":::"memory"); for(;;){} }
void G_Ticker (void)
{
    static gamestate_t prevgamestate = 0;
    if (_g_gamestate == GS_LEVEL && _g_gamemap >= 1 && _g_gamemap <= 9) {
        uint16_t t, l; R114_ZoneStat(&t, &l);
        uint16_t m = (uint16_t)(_g_gamemap - 1);
        if (!r114_min_total[m] || t < r114_min_total[m]) r114_min_total[m] = t;
        if (!r114_min_largest[m] || l < r114_min_largest[m]) r114_min_largest[m] = l;
        if (++r114_tics >= 140) {
            r114_tics = 0;
            if (_g_gamemap >= 9) R114_Done();
            _g_demoplayback = 0;
            G_InitNew(sk_hard, (int16_t)(_g_gamemap + 1));
            return;
        }
    }
''')
D = 'src/d_main.c'
rep(D, '            if (viewactive)\n                R_RenderPlayerView (&_g_player);\n',
       '            if (0 && viewactive)\n                R_RenderPlayerView (&_g_player);\n')
p = Path('scripts/lab/build_r71a12mul_hud.py'); s = p.read_text()
assert "'r113-'" in s and "('hilut', 1)" in s
p.write_text(s.replace("'r113-'", "'r114-'").replace("('hilut', 1)", "('zone', 1)"))
print('R114 zone survey diag')
