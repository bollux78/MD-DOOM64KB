#!/usr/bin/env python3
"""Two isolated E1M4 weapon animation/bob diagnostic ROMs; private runner only."""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
TEMP = Path(os.environ["RUNNER_TEMP"]) / ("m14-weapon-" + os.environ["GITHUB_RUN_ID"])
OUT = Path("/home/dan/Projetos/manifold-doom/roms/M14/diagnostico-ARMA-20261114")
WAD = Path("/home/dan/Projetos/doom-md/assets/wads/doom1.wad")
GDK = Path(os.environ["GDK"])
TC = Path.home() / "mars/m68k-elf/bin/m68k-elf-"
PIN = "b6fe52a52344464de00bde4dc58a40f8b89cfc1a"
WAD_SHA = "1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771"
VARIANTS = (
    ("F-weapon-fixed-bob", {"MANIFOLD_NO_TEXT": "1", "MANIFOLD_WEAPON_FIX": "1", "MANIFOLD_INPUT_FIX": "1"}),
    ("G-weapon-fixed-no-bob", {"MANIFOLD_NO_TEXT": "1", "MANIFOLD_WEAPON_FIX": "1", "MANIFOLD_INPUT_FIX": "1", "MANIFOLD_NO_GUNBOB": "1"}),
)
BASE = {
    "MANIFOLD_MAP": "E1M4", "MANIFOLD_BSP": "0",
    "MANIFOLD_MAX_CELL_WALLS": "24",
    "MANIFOLD_RADIUS": "1", "MANIFOLD_STABLE_VIEW": "1",
    "MANIFOLD_H32": "1", "MANIFOLD_HUD": "doom",
    "MANIFOLD_HUD_TIMING": "1", "MANIFOLD_HUD_VRAM_REPAIR": "0",
    "MANIFOLD_VDP_ATOMIC": "0", "MANIFOLD_STATIC_REPAIR_ONCE": "1",
    "MANIFOLD_NEAR_SAFE": "1", "MANIFOLD_SKY_MERGE": "0",
    "MANIFOLD_OBJECTS": "1", "MANIFOLD_PICKUPS": "1",
    "MANIFOLD_DOORS": "2", "MANIFOLD_ALL_KEYS": "1",
    "MANIFOLD_LAT_CLIP": "1", "MANIFOLD_EYE": "48",
    "MANIFOLD_TEX_U": "1", "MANIFOLD_TEX_HSTRETCH": "1.0",
    "MANIFOLD_WEAPON": "pistol", "MANIFOLD_MUSIC": "1",
}
def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()

def run(args, log, *, cwd=None, env=None, timeout=1500):
    with log.open("a") as fp:
        try:
            subprocess.run(args, cwd=cwd, env=env, stdout=fp, stderr=subprocess.STDOUT,
                           timeout=timeout, check=True)
        except Exception:
            print("FAILED:", " ".join(map(str,args)), flush=True)
            print("".join(log.read_text(errors="replace").splitlines(keepends=True)[-70:]), flush=True)
            raise

def main():
    if not WAD.is_file() or sha(WAD) != WAD_SHA:
        raise SystemExit("Private DOOM shareware WAD missing or wrong SHA256")
    if not (GDK/"makefile.gen").is_file() or not Path(str(TC)+"gcc").is_file():
        raise SystemExit("SGDK or 68000 compiler missing")
    if not OUT.parent.is_dir():
        raise SystemExit("M14 ROM archive directory missing")
    TEMP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    log = TEMP/"build.log"
    makefile = TEMP/"makefile-no-lto.gen"
    flags = (GDK/"makefile.gen").read_text()
    pattern = "-flto -flto=auto -ffat-lto-objects"
    if flags.count(pattern) < 2:
        raise SystemExit("Unexpected SGDK makefile LTO flags")
    makefile.write_text(flags.replace(pattern, "-fno-lto"))
    native_xgm = Path.home()/"mars/m68k-elf/bin/xgmtool"
    xgm = GDK/"bin/xgmtool"
    if not xgm.exists() and native_xgm.is_file():
        xgm.symlink_to(native_xgm)
    upstream = TEMP/"upstream"
    run(["git","clone","--quiet","https://github.com/ehaliewicz/Manifold.git",str(upstream)],log,timeout=240)
    run(["git","checkout","--quiet","--detach",PIN],log,cwd=upstream)
    env0 = os.environ.copy()
    env0.update(BASE)
    env0["GDK"] = str(GDK)
    env0["DOOM_R25_MUSIC"] = "1"
    env0["PATH"] = f"{TC.parent}:{GDK}/bin:" + env0.get("PATH","")
    run([sys.executable,"scripts/lab/prepare_r25_music.py"],log,cwd=ROOT,env=env0)
    vgm = ROOT/"res/r25-e1m1.vgm"
    if not vgm.is_file() or vgm.stat().st_size < 100:
        raise SystemExit("VGM not generated")
    env0["MANIFOLD_MUSIC_VGM"] = str(vgm)
    stage_script = ROOT/"experiments/DOOM_Manifold_E1M1/m01/stage_rom.py"
    records = []
    for name, extra in VARIANTS:
        staged = TEMP/name
        env = env0.copy()
        env.update(extra)
        env["MANIFOLD_BUILD_TAG"] = ("WERK M14 WPN " + name.upper())[:28]
        env["MANIFOLD_ROM_NAME"] = "WERK M14 HINT " + name.upper()
        print("BUILD", name, "flags", extra, flush=True)
        run([sys.executable,str(stage_script),"--source",str(upstream),
             "--wad",str(WAD),"--out",str(staged)],log,cwd=ROOT,env=env)
        lower = staged/"src/math3d.h"
        upper = staged/"src/math3D.h"
        if lower.is_file() and not upper.exists():
            upper.symlink_to("math3d.h")
        run(["make","-C",str(staged),"-f",str(makefile),"-j2","release",
             "OS=Linux",f"GDK={GDK}",f"PREFIX={TC}",
             f"CC={TC}gcc",f"LD={TC}ld",f"AR={TC}ar",
             f"NM={TC}nm",f"OBJCPY={TC}objcopy"],log,env=env)
        rom = staged/"out/release/rom.bin"
        if not rom.is_file() or rom.stat().st_size < 65536:
            raise SystemExit("Missing ROM for "+name)
        destination = OUT/("werk-m14-e1m4-WEAPON-"+name+".bin")
        digest = sha(rom)
        if destination.exists() and sha(destination) != digest:
            raise SystemExit("Existing ROM has different hash, refusing overwrite: "+str(destination))
        if not destination.exists():
            shutil.copy2(rom,destination)
        print("OK",destination.name,rom.stat().st_size,digest,flush=True)
        records.append((name,extra,destination.name,rom.stat().st_size,digest))
    readme = [
        "# M14 E1M4 — dois testes de arma e gun bob (WERK)",
        "",
        "Todas as ROMs foram compiladas da mesma fonte (branch experimental, commit indicado abaixo),",
        "com WAD shareware privado do runner. Sem uploads de ROMs ao GitHub.",
        "Nenhum teste visual em hardware foi executado pelo workflow.",
        "",
        f"- Fonte do experimento: {os.environ.get('GITHUB_SHA','unknown')}",
        f"- Upstream Manifold: {PIN}",
        "- Mapa: E1M4, H32, HUD DOOM, música ligada, clipping lateral ligado.",
        "- F: sem texto + correção de sprites/animação + entrada A/C + bob ligado.",
        "- G: mesma configuração F, mas sem atualizações de posição da arma.",
        "- Comparar F/G no mesmo local para identificar custo do gun bob.",
        "",
    ]
    for name,extra,filename,size,digest in records:
        readme += [f"## {name}",f"- Arquivo: {filename}",f"- Bytes: {size}",
                   f"- SHA-256: {digest}",f"- Flags: {extra or '{}'}",""]
    (OUT/"README.md").write_text("\n".join(readme)+"\n")
    print("SUCCESS: 2/2 ROMs at",OUT,flush=True)

if __name__ == "__main__":
    main()
