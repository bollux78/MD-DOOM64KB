#!/usr/bin/env python3
"""R82 (Claudio): build-level experiments taken from Doom8088, on top of R81.

Runs in a disposable copy AFTER scripts/lab/apply_r81.py. No game source is edited:
each experiment changes how the same R81 sources are compiled.

  IVO   add -fno-ivopts.  In the R79/R81 ELF, GCC's induction-variable optimisation turns
        the 152-byte-stride column loops into end-pointer compares whose limit and
        post-loop pointer cost MULU.W #$98 (R_DrawColumnFlat, R_DrawColumnSprite, the
        wall fallback loops).  Hypothesis: one flag removes that pattern everywhere.
  D88   the loop/register flags Doom8088 builds with:
        -fira-loop-pressure -fno-tree-pre -fgcse-sm -fgcse-las -fipa-pta
  BSPR  recursive R_RenderBSPNode instead of DOOM_R20_BSP_ITERATIVE.  Same visit order;
        Doom8088 measured its non-recursive version as slower.  The iterative version was
        chosen in R20 to bound stack use, so this one needs a stack check before adoption.

Select with R82_EXPERIMENTS="IVO", "D88", "BSPR" or combinations joined by "+".
"""
from pathlib import Path
import os, sys
ROOT = Path(__file__).resolve().parents[2]

EXTRA_OLD = 'EXTRA_FLAGS="-Isrc -Icompat -std=gnu11 $render_flags"'
FLAGS = {
    "IVO": "-fno-ivopts",
    "D88": "-fira-loop-pressure -fno-tree-pre -fgcse-sm -fgcse-las -fipa-pta",
}
BSP_TOKEN = " '-DDOOM_R20_BSP_ITERATIVE'"
PIXEL_PREFIX = "set -l pixel "


def add_flags(s, flags):
    assert s.count(EXTRA_OLD) == 2, "build_silent.fish EXTRA_FLAGS lines changed"
    return s.replace(EXTRA_OLD, EXTRA_OLD[:-1] + " " + flags + '"')


def drop_bsp_iterative(s):
    lines = s.split("\n")
    hits = [i for i, l in enumerate(lines) if l.startswith(PIXEL_PREFIX)]
    assert len(hits) == 1, "pixel define list not unique"
    l = lines[hits[0]]
    assert l.count(BSP_TOKEN) == 1, "BSP_ITERATIVE not in pixel list"
    lines[hits[0]] = l.replace(BSP_TOKEN, "")
    return "\n".join(lines)


def main():
    chosen = [x for x in os.environ.get("R82_EXPERIMENTS", "").replace("+", " ").split() if x]
    assert chosen and len(set(chosen)) == len(chosen) and all(x in ("IVO", "D88", "BSPR") for x in chosen), chosen
    bs = ROOT / "scripts/build_silent.fish"
    s = bs.read_text()
    assert "R82" not in s, "R82 already applied"
    flags = " ".join(FLAGS[x] for x in chosen if x in FLAGS)
    if flags:
        s = add_flags(s, flags + " -DR82_BUILD_MARK")
        bs.write_text(s)
    if "BSPR" in chosen:
        lf = ROOT / "scripts/lab/build_r35_linear.fish"
        lf.write_text(drop_bsp_iterative(lf.read_text()))
    print("R82 applied:", "+".join(chosen), "| extra CFLAGS:", flags or "(none)")


if __name__ == "__main__":
    sys.exit(main())
