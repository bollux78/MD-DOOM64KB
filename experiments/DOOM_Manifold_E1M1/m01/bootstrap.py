#!/usr/bin/env python3
"""Prepare a pinned, isolated Manifold source tree and audit E1M1 readiness.

No modification of Doom R128, M1.5, user WAD, or the source checkout.
Run: python3 experiments/DOOM_Manifold_E1M1/m01/bootstrap.py --out /tmp/manifold-e1m1
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess

UPSTREAM = "https://github.com/ehaliewicz/Manifold.git"
PIN = "b6fe52a52344464de00bde4dc58a40f8b89cfc1a"

def run(*args, cwd=None):
    subprocess.run(args, cwd=cwd, check=True)

def inspect(root):
    src = root / "src"
    required = ["portal.c", "draw.c", "bunch_render.c", "my_bmp.c",
                "map_table.c", "maps.h", "python/e1m1.c"]
    missing = [name for name in required if not (src / name).is_file()]
    if missing:
        raise RuntimeError("Manifold missing required source: " + ", ".join(missing))
    table = (src / "map_table.c").read_text()
    maps = (src / "maps.h").read_text()
    e1 = (src / "python/e1m1.c").read_text()
    included = bool(re.search(r'[#]include\s+["<]e1m1\.h', maps))
    table_used = bool(re.search(r'&(?:e1m1|e1m1_map)\b', table))
    # The upstream E1M1 data is a separate Doom-oriented generated structure.
    # Its presence does NOT imply a portal_map instance that the runtime can load.
    result = {
        "upstream": UPSTREAM, "pin": PIN,
        "e1m1_source_bytes": (src / "python/e1m1.c").stat().st_size,
        "e1m1_has_things": bool(re.search(r'static\s+const\s+thing\s+things\s*\[', e1)),
        "registered_in_map_table": table_used,
        "declared_in_maps_header": included,
        "requires_doom_to_portal_map_conversion": not (included and table_used),
        "build_available": bool(shutil.which("make")),
        "m68k_gcc_available": bool(shutil.which("m68k-elf-gcc")),
    }
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--source", type=pathlib.Path, help="existing Manifold tree; do not clone")
    args = parser.parse_args()
    root = args.out.resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit("Refusing to overwrite nonempty destination: " + str(root))
    root.mkdir(parents=True, exist_ok=True)
    dest = root / "manifold"
    if args.source:
        shutil.copytree(args.source.resolve(), dest, ignore=shutil.ignore_patterns(".git", "out"))
        origin = "user supplied (unverified SHA)"
    else:
        run("git", "clone", "--no-checkout", UPSTREAM, str(dest))
        run("git", "checkout", "--detach", PIN, cwd=dest)
        origin = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dest, text=True).strip()
        if origin != PIN:
            raise RuntimeError("Unexpected upstream revision")
    report = inspect(dest)
    report["source_revision"] = origin
    (root / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["requires_doom_to_portal_map_conversion"]:
        print("GATE: E1M1 is NOT yet a selectable Manifold portal_map.")
    print("SOURCE AUDIT ONLY: no ROM built, no BlastEm test, no hardware PASS.")

if __name__ == "__main__":
    main()
