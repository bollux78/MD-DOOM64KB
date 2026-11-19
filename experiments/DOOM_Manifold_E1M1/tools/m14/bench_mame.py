#!/usr/bin/env python3
"""Automated benchmark in MAME for a ROM built with MANIFOLD_BENCH=1.

  python3 bench_mame.py ROM.bin --out /tmp/bench_x [--maps E1M1,E1M2] [--base /tmp/bench_y] [--jobs 3]

Per map: extracts the map image (flat_map.py), runs the ROM headless, collects ticks/frame per point (the same
numbers the on-screen table shows) and one snapshot per point.  With --base DIR (a previous run) prints the ratio
against it and counts differing pixels per point (the FPS counter strip is ignored), so an optimisation that
changes the picture is caught.  Needs monsters inactive in the build (repeatable numbers)."""
import argparse, os, subprocess, sys, glob, json, concurrent.futures as cf
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "m01"))
from m14_bench import BENCH_POINTS
NM = "/home/claude/mars/m68k-elf/bin/m68k-elf-nm"
DEFAULT_ADDR = "e0ff261c"      # manifold_dbg; same in every map image so far

def addr_for(m):
    rom = Path(f"/tmp/m12/mm_{m}/out/release/rom.out")
    if rom.exists():
        for ln in subprocess.run([NM, str(rom)], capture_output=True, text=True).stdout.splitlines():
            p = ln.split()
            if len(p) == 3 and p[2] == "manifold_dbg": return p[0][-8:]
    return DEFAULT_ADDR

def run_map(rom, out, m, k):
    d = out / m; d.mkdir(parents=True, exist_ok=True)
    flat = d / "flat.bin"
    subprocess.run([sys.executable, str(HERE / "flat_map.py"), rom, str(k), str(flat)], check=True, capture_output=True)
    np_ = 4 + len(BENCH_POINTS.get(m, []))
    env = dict(os.environ, BADDR=addr_for(m), BNP=str(np_), BOUT=str(d / "ticks.txt"),
               SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy")
    snap = d / "snap"; subprocess.run(["rm", "-rf", str(snap)])
    subprocess.run(["timeout", "1500", "/usr/games/mame", "genesis", "-cart", str(flat), "-autoboot_script", str(HERE / "bench_auto.lua"),
                    "-video", "none", "-sound", "none", "-nothrottle", "-seconds_to_run", "900", "-skip_gameinfo",
                    "-snapshot_directory", str(snap)], env=env, capture_output=True)
    flat.unlink(missing_ok=True)
    t = (d / "ticks.txt").read_text().split() if (d / "ticks.txt").exists() else []
    return m, [int(x) for x in t]

def labels(m):
    return ["SPAWN 0", "SPAWN 90", "SPAWN 180", "SPAWN 270"] + [f"PONTO {i+1} {e[0]}" for i, e in enumerate(BENCH_POINTS.get(m, []))]

def pixdiff(a, b):
    from PIL import Image, ImageChops
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    d = ImageChops.difference(A, B)
    w, h = d.size
    d.paste((0, 0, 0), (0, h - 24, 80, h))                  # FPS counter strip
    return sum(1 for p in d.getdata() if p != (0, 0, 0))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom"); ap.add_argument("--out", required=True)
    ap.add_argument("--maps", default="E1M1,E1M2,E1M3,E1M4,E1M5,E1M6,E1M7,E1M8,E1M9")
    ap.add_argument("--base"); ap.add_argument("--jobs", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    maps = a.maps.split(",")
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        res = dict(ex.map(lambda m: run_map(a.rom, out, m, int(m[3:]) - 1), maps))
    summary = {}
    for m in maps:
        base = None
        if a.base and (Path(a.base) / m / "ticks.txt").exists():
            base = [int(x) for x in (Path(a.base) / m / "ticks.txt").read_text().split()]
        print(f"== {m}")
        tot = tb = 0
        for i, (lab, t) in enumerate(zip(labels(m), res[m])):
            line = f"  {lab:<14}{t:>5}  {3000 // t / 10 if t else 0:>5.1f} FPS"
            if base and i < len(base) and base[i]:
                line += f"   x{t / base[i]:.2f} vs base"
                sa = sorted(glob.glob(str(out / m / "snap/**/*.png"), recursive=True)); sb = sorted(glob.glob(str(Path(a.base) / m / "snap/**/*.png"), recursive=True))
                if i < len(sa) and i < len(sb):
                    px = pixdiff(sa[i], sb[i]); line += f"   pixels diff {px}"
                tb += base[i]
            tot += t; print(line)
        print(f"  {'TOTAL':<14}{tot:>5}" + (f"   x{tot / tb:.2f} vs base" if tb else ""))
        summary[m] = res[m]
    (out / "summary.json").write_text(json.dumps(summary))
main()
