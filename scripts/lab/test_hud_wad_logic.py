#!/usr/bin/env python3
"""Differential host test of src/hud_wad_logic.h (C) against the Python reference model in gen_hud_wad.py, plus face-widget scenarios.
Uses a synthetic IWAD; compiles with the host gcc."""
import os, random, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_hud_wad as G
import test_gen_hud_wad as T

SRC = os.path.join(HERE, "..", "..", "src")

C_MAIN = r'''
#include <stdio.h>
#include <stdlib.h>
#include "hud_wad_assets.h"
#include "hud_wad_logic.h"
typedef struct { HudState s; uint16_t exp[4][32]; } Case;
#include "cases.inc"
static int fails;
#define CHECK(c, m) do { if (!(c)) { printf("FAIL %s (line %d)\n", m, __LINE__); fails++; } } while (0)
int main(void) {
    for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); i++)
        for (int r = 0; r < 4; r++) {
            uint16_t out[32];
            HUDW_ComposeRow(&cases[i].s, (uint8_t)r, out);
            for (int c = 0; c < 32; c++)
                if (out[c] != (uint16_t)(0xE000u | (HUDW_VRAM_BASE + cases[i].exp[r][c]))) { printf("FAIL case %u row %d col %d: %u vs %u\n", i, r, c, out[c], cases[i].exp[r][c]); fails++; }
        }
    /* hash changes with every displayed field */
    HudState a = {0}; HudState b = a; uint16_t h0 = HUDW_Hash(&a);
    b.health = 1; CHECK(HUDW_Hash(&b) != h0, "hash health"); b = a; b.arms = 4; CHECK(HUDW_Hash(&b) != h0, "hash arms");
    b = a; b.keys = 2; CHECK(HUDW_Hash(&b) != h0, "hash keys"); b = a; b.maxammo[3] = 9; CHECK(HUDW_Hash(&b) != h0, "hash max");
    /* face widget */
    CHECK(hudw_pain_offset(100) == 0 && hudw_pain_offset(101) == 0 && hudw_pain_offset(50) == 16 && hudw_pain_offset(1) == 32 && hudw_pain_offset(0) == 32 + 0, "pain offset");
    HudFace f; HudFaceIn p = {100, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    HUDW_FaceInit(&f, 100, 0);
    HUDW_FaceTick(&f, &p); CHECK(f.index <= 2 && f.count == 16 && f.priority == 0, "straight");
    p.random = 2; for (int i = 0; i < 20; i++) { HUDW_FaceTick(&f, &p); }
    CHECK(f.index <= 2, "straight stays");
    p.health = 0; HUDW_FaceTick(&f, &p); CHECK(f.index == HUDW_DEADFACE && f.priority == 9, "dead");
    HUDW_FaceInit(&f, 100, 0); p.health = 100; p.god = 1; HUDW_FaceTick(&f, &p); CHECK(f.index == HUDW_GODFACE, "god");
    HUDW_FaceInit(&f, 100, 0); p.god = 0; p.bonuscount = 6; p.weapons = 4; HUDW_FaceTick(&f, &p); CHECK(f.index == HUDW_EVIL && f.count == 69, "evil grin");
    p.weapons = 4; p.bonuscount = 0;
    HUDW_FaceInit(&f, 100, 4); p.health = 90; p.damagecount = 10; p.has_attacker = 1; p.angle_to_attacker = 0x10000000u; p.mo_angle = 0;
    HUDW_FaceTick(&f, &p); CHECK(f.index == hudw_pain_offset(90) + HUDW_RAGE, "attacker ahead -> rage face");
    HUDW_FaceInit(&f, 100, 4); p.angle_to_attacker = 0x60000000u; HUDW_FaceTick(&f, &p); CHECK(f.index == hudw_pain_offset(90) + HUDW_TURNOFF + 1, "attacker 135deg counter-clockwise -> TURNOFF+1 (as the original)");
    HUDW_FaceInit(&f, 100, 4); p.angle_to_attacker = 0xA0000000u; HUDW_FaceTick(&f, &p); CHECK(f.index == hudw_pain_offset(90) + HUDW_TURNOFF, "attacker other side -> TURNOFF");
    HUDW_FaceInit(&f, 100, 4); p.health = 50; p.has_attacker = 1; HUDW_FaceTick(&f, &p); CHECK(f.index == hudw_pain_offset(50) + HUDW_OUCH, "big hit -> ouch");
    HUDW_FaceInit(&f, 100, 4); p.damagecount = 0; p.has_attacker = 0; p.health = 100; p.attackdown = 1;
    for (int i = 0; i < 80; i++) { HUDW_FaceTick(&f, &p); }
    CHECK(f.priority == 5, "rage after sustained fire");
    printf(fails ? "FAILED %d\n" : "OK\n", fails);
    return fails != 0;
}
'''


def c_cases(a, n=60, seed=3):
    rnd = random.Random(seed)
    out = ["static const Case cases[] = {"]
    for k in range(n):
        st = dict(health=rnd.choice([0, 7, 55, 100, 199, 999, -5]), armor=rnd.choice([0, 1, 100, 200, 999]),
                  ammo_r=rnd.choice([-1, 0, 9, 50, 999]), ammo=[rnd.choice([0, 3, 50, 400]) for _ in range(4)],
                  maxammo=[rnd.choice([50, 200, 300, 600]) for _ in range(4)], arms=rnd.randrange(64), keys=rnd.randrange(8), face=0)
        rows = G.model_rows(a, st)
        out.append(" {{%d,%d,%d,{%s},{%s},%d,%d,0},{%s}}," % (
            st["health"], st["armor"], st["ammo_r"], ",".join(map(str, st["ammo"])), ",".join(map(str, st["maxammo"])), st["arms"], st["keys"],
            ",".join("{" + ",".join(map(str, r)) + "}" for r in rows)))
    out.append("};")
    return "\n".join(out) + "\n"


def main():
    a = G.build_assets(G.read_iwad(G.make_iwad(T.synthetic_lumps())))
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "hud_wad_assets.h"), "w").write(G.emit_header(a))
        open(os.path.join(d, "cases.inc"), "w").write(c_cases(a))
        open(os.path.join(d, "t.c"), "w").write(C_MAIN)
        exe = os.path.join(d, "t")
        r = subprocess.run(["gcc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-O1", "-I", d, "-I", SRC, "-o", exe, os.path.join(d, "t.c")],
                           capture_output=True, text=True)
        if r.returncode:
            sys.exit("compile failed:\n" + r.stderr)
        r = subprocess.run([exe], capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode:
            sys.exit(1)
    print("PASS test_hud_wad_logic")


if __name__ == "__main__":
    main()
