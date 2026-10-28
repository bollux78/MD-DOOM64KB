#!/usr/bin/env python3
"""Equivalence test for R80-P1 (Pair-V offset tables).

1. The hook applies exactly once to the R79-prepared r22_video.inc snapshot and only
   touches the wall and flat destination lines (diff check).
2. Host C: the real R22_PixelByte from the R79-prepared r22_pixel4.h and the
   R80_PIXEL_BYTE macro emitted by the hook are compiled together and compared for
   every 0<=x<76, 0<=y<44, with x/y passed as int16_t like at the call sites.
   Both the Pair-V branch and the fallback branch of the macro are tested.
usage: test_r80_pixofs.py [--src DIR]   (default: docs/performance-r80/reference-prepared/src)
"""
import argparse, difflib, importlib.util, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_hook():
    spec = importlib.util.spec_from_file_location("r80hook", ROOT / "scripts/lab/apply_r80_performance.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


C = r'''
#include <stdio.h>
#include <stdint.h>
#include "r22_pixel4.h"
%s
static uint8_t fb[3344];
int main(void){
    long bad=0, n=0;
    for(int16_t y=0;y<R22_H;y++) for(int16_t x=0;x<R22_W;x++){
        uint8_t *a=R22_PixelByte(fb,(uint16_t)x,(uint16_t)y);
        uint8_t *b=R80_PIXEL_BYTE(fb,x,y);
        n++;
        if(a!=b || b<fb || b>=fb+3344){ if(bad<5) printf("MISMATCH x=%%d y=%%d ref=%%ld r80=%%ld\n",x,y,(long)(a-fb),(long)(b-fb)); bad++; }
    }
    printf("checked=%%ld mismatches=%%ld\n",n,bad);
    return bad!=0;
}
'''


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--src", default=str(ROOT / "docs/performance-r80/reference-prepared/src"))
    a = ap.parse_args(); src = pathlib.Path(a.src)
    hook = load_hook()
    before = (src / "r22_video.inc").read_text()
    after = hook.apply_text(before)
    changed = [l for l in difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=0)
               if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    removed = [l for l in changed if l.startswith("-")]
    assert len(removed) == 2 and all("R22_PixelByte(r22_fb.pixels" in l for l in removed), removed
    assert sum(1 for l in changed if l.startswith("+") and "R80_PIXEL_BYTE(r22_fb.pixels" in l) == 2
    assert after.count("R22_PixelByte(r22_fb.pixels") == before.count("R22_PixelByte(r22_fb.pixels") - 2  # sprite untouched
    try:
        hook.apply_text(after); raise SystemExit("hook applied twice")
    except AssertionError:
        pass
    print("diff check: 2 call sites replaced (wall, flat); sprite site untouched; double apply refused")
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "host C compiler required"
    with tempfile.TemporaryDirectory() as t:
        t = pathlib.Path(t)
        shutil.copy2(src / "r22_pixel4.h", t / "r22_pixel4.h")
        (t / "t.c").write_text(C % hook.block())
        for label, defs in (("pair-v", ["-DDOOM_R47_PLANE_PAIR", "-DDOOM_R48_PAIR_V"]), ("fallback", [])):
            exe = t / ("t-" + label)
            subprocess.run([cc, "-std=c11", "-O2", "-Wall", "-Werror", "-I", str(t), *defs, str(t / "t.c"), "-o", str(exe)], check=True)
            r = subprocess.run([str(exe)], capture_output=True, text=True)
            print(label, r.stdout.strip())
            assert r.returncode == 0 and "checked=3344 mismatches=0" in r.stdout, r.stdout
    print("PASS R80-P1 pixel offset equivalence")
    # R80-F1: anchors in both orders, and a model of the DBRA loop against the C loop.
    for order in (("P1", "F1"), ("F1", "P1")):
        t = before
        for x in order:
            t = hook.EXPERIMENTS[x](t)
        assert "R80-F1" in t and "DOOM_R80_PIXOFS" in t, order
        # the inline asm must keep C escapes (a real newline inside a C string literal is a compile error)
        blk = t[t.index("R80-F1 (Claudio)"):t.index("dbra %[n],1b")]
        assert '"1:\\n\\t"' in blk and '"move.b %[v],(%[d])\\n\\t"' in blk, blk
        try:
            hook.apply_f1(t); raise SystemExit("F1 applied twice")
        except AssertionError:
            pass
    for count in range(0, 45):
        for start in (0, 7):
            # C loop (control)
            d, c, wc = start, count, []
            while c >= 2:
                wc.append(d); d += 152; c -= 2
            # DBRA model: dbra decrements the 16-bit counter and branches while it is not -1
            d2, c2, w2 = start, count, []
            pairs = c2 >> 1
            if pairs:
                n = pairs - 1
                while True:
                    w2.append(d2); d2 += 152
                    n = (n - 1) & 0xffff
                    if n == 0xffff: break
            c2 &= 1
            assert (wc, d, c) == (w2, d2, c2), (count, start)
    # host C front-end parse of the generated F1 block (asm text is not assembled on the host)
    f1 = hook.apply_f1(before)
    i = f1.index("#if !defined(DOOM_R49_COLORMIX)\n    /* R80-F1")
    k = f1.index(hook.FLAT_LOOP_OLD, i) + len(hook.FLAT_LOOP_OLD)
    assert f1.startswith("#endif\n", k); j = k + len("#endif\n")
    code = "#include <stdint.h>\nvoid f(uint8_t *dst,uint16_t count,const uint8_t pair){\n" + f1[i:j] + "(void)dst;(void)count;}\n"
    with tempfile.TemporaryDirectory() as td:
        c = pathlib.Path(td) / "f1.c"; c.write_text(code)
        subprocess.run([cc, "-std=c11", "-fsyntax-only", "-Wall", "-Werror", str(c)], check=True)
    print("PASS R80-F1 anchor checks, host C parse and DBRA loop model (count 0..44)")


if __name__ == "__main__":
    main()
