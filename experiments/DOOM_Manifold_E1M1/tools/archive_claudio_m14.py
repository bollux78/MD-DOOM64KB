#!/usr/bin/env python3
"""Rebuild six Claudio M14 variants privately on self-hosted runner.
Only .bin files and README.md are copied to the existing M14 directory.
Historical commit + flags are recorded in README; no claim of byte-identical
reproduction until full checksums match the original supplied hashes.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(os.environ["GITHUB_WORKSPACE"])
TEMP = Path(os.environ["RUNNER_TEMP"]) / ("manifold-claudio-m14-" + os.environ.get("GITHUB_RUN_ID", "local"))
TARGET = Path("/home/dan/Projetos/manifold-doom/roms/M14")
WAD = Path("/home/dan/Projetos/doom-md/assets/wads/doom1.wad")
GDK = Path(os.environ["GDK"])
TC = Path.home() / "mars/m68k-elf/bin/m68k-elf-"
BLASTEM = Path.home() / "Projetos/blastem64-1.0.0/blastem"
UPSTREAM = "b6fe52a52344464de00bde4dc58a40f8b89cfc1a"

# Commit anchors capture the introduction of each historical feature.
# Do not silently compile all six using the same current M14 HEAD.
BASE = {
 "MANIFOLD_BSP": "0", "MANIFOLD_RADIUS": "1",
 "MANIFOLD_STABLE_VIEW": "1", "MANIFOLD_H32": "0",
 "MANIFOLD_HUD_TIMING": "1", "MANIFOLD_HUD_VRAM_REPAIR": "0",
 "MANIFOLD_VDP_ATOMIC": "0", "MANIFOLD_STATIC_REPAIR_ONCE": "1",
 "MANIFOLD_NEAR_SAFE": "1", "MANIFOLD_SKY_MERGE": "1",
 "MANIFOLD_SKY_CEIL_UNIFORM": "0", "MANIFOLD_OBJECTS": "1",
 "MANIFOLD_PICKUPS": "1", "MANIFOLD_DOORS": "1",
 "MANIFOLD_EYE": "48", "MANIFOLD_TEX_U": "1",
 "MANIFOLD_TEX_HSTRETCH": "1.0", "MANIFOLD_WEAPON": "pistol",
}
VARIANTS = [
 ("claudio-m14-e1m1-pistol-allobj-eye48-u1-h40.bin", "a6521b5", "Pistola e todos os objetos", {}),
 ("claudio-m14-e1m1-pistol-swfix-eye48-u1-h40.bin", "928cac1", "Botao de saida com divisao de paredes", {}),
 ("claudio-m14-e1m1-grates-eye48-u1-h40.bin", "f5f1997", "Grades de sprites e colisao varrida", {}),
 ("claudio-m14-e1m1-full-vdpsafe-monsters-h40.bin", "a721a93", "Monstros estaticos e modo VDP-safe", {"MANIFOLD_VDP_SAFE":"1"}),
 ("claudio-m14-NOHUD-A-sem-vdpsafe.bin", "dbe6d9f", "Sem HUD, controle sem VDP-safe", {"MANIFOLD_NOHUD":"1", "MANIFOLD_VDP_SAFE":"0"}),
 ("claudio-m14-NOHUD-B-vdpsafe-ceu.bin", "dbe6d9f", "Sem HUD, com VDP-safe e ceu", {"MANIFOLD_NOHUD":"1", "MANIFOLD_VDP_SAFE":"1"}),
]
# Original SHA-256 prefixes supplied in the Claudio M14 report. Compare but
# DO NOT fail the build if a historical build used differing unrecorded inputs.
ORIGINAL_PREFIX = {
 VARIANTS[0][0]:"3b9a9da7a2b9a0fe",
 VARIANTS[1][0]:"3af987e97f0ef5bc",
 VARIANTS[2][0]:"f823522153f87a18",
 VARIANTS[3][0]:"9569feaf7fd062ea",
 VARIANTS[4][0]:"0d43c324384f4f7e",
 VARIANTS[5][0]:"281c517739d940c5",
}

def cmd(args, log, cwd=None, env=None, timeout=1800):
    with open(log, "a") as fp:
        subprocess.run(args, cwd=cwd, env=env, stdout=fp, stderr=subprocess.STDOUT,
                       timeout=timeout, check=True)

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1048576),b""):h.update(chunk)
    return h.hexdigest()

def main():
    if not TARGET.parent.is_dir(): raise SystemExit("Missing local ROM directory")
    if not WAD.is_file() or sha(WAD)!="1d7d43be501e67d927e415e0b8f3e29c3bf33075e859721816f652a526cac771":
        raise SystemExit("Private shareware WAD mismatch")
    if not (GDK/"makefile.gen").is_file() or not Path(f"{TC}gcc").is_file():
        raise SystemExit("Cross compiler/SGDK unavailable")
    if not BLASTEM.is_file():raise SystemExit("BlastEm not installed")
    TARGET.mkdir(exist_ok=True)
    TEMP.mkdir(parents=True, exist_ok=True)
    text=(GDK/"makefile.gen").read_text()
    pat="-flto -flto=auto -ffat-lto-objects"
    if text.count(pat)<2:raise SystemExit("Unexpected SGDK makefile")
    makefile=TEMP/"makefile-no-lto.gen"
    makefile.write_text(text.replace(pat,"-fno-lto"))
    xgm=GDK/"bin/xgmtool"
    native=Path.home()/"mars/m68k-elf/bin/xgmtool"
    if not xgm.exists() and native.is_file():xgm.symlink_to(native)
    upstream=TEMP/"upstream"
    cmd(["git","clone","--quiet","https://github.com/ehaliewicz/Manifold.git",str(upstream)], TEMP/"git.log",timeout=240)
    cmd(["git","checkout","--quiet","--detach",UPSTREAM],TEMP/"git.log",cwd=upstream)
    result=[]
    for name,ref,description,extras in VARIANTS:
        job=TEMP/name.removesuffix(".bin")
        job.mkdir()
        log=job/"build.log"
        try:
            # Read exact historical source in isolated checkout with full history.
            archive=job/"snapshot.tar"
            with archive.open("wb") as fd:
                subprocess.run(["git","-C",str(ROOT),"archive",ref],stdout=fd,stderr=subprocess.PIPE,check=True,timeout=90)
            src=job/"repo";src.mkdir()
            with tarfile.open(archive) as tf:tf.extractall(src,filter="data")
            stage=src/"experiments/DOOM_Manifold_E1M1/m01/stage_rom.py"
            if not stage.is_file():raise RuntimeError("historical stage script unavailable")
            env=os.environ.copy();env.update(BASE);env.update(extras)
            env["GDK"]=str(GDK)
            env["PATH"]=f"{TC.parent}:{GDK}/bin:"+env.get("PATH","")
            # Original variants have M14 identity only when their commit included it.
            if ref=="dbe6d9f":
                env["MANIFOLD_ROM_NAME"]="CLAUDIO M14 "+("NOHUD A" if extras.get("MANIFOLD_VDP_SAFE")=="0" else "NOHUD B")
                env["MANIFOLD_ROM_TEST"]=description.upper()
            out=job/"stage"
            cmd([sys.executable,str(stage),"--source",str(upstream),"--wad",str(WAD),"--out",str(out)],log,cwd=src,env=env)
            if (out/"src/math3d.h").is_file() and not (out/"src/math3D.h").exists():
                (out/"src/math3D.h").symlink_to("math3d.h")
            cmd(["make","-C",str(out),"-f",str(makefile),"-j2","release",
                 "OS=Linux",f"GDK={GDK}",f"PREFIX={TC}",
                 f"CC={TC}gcc",f"LD={TC}ld",f"AR={TC}ar",
                 f"NM={TC}nm",f"OBJCPY={TC}objcopy"],log,env=env)
            rom=next((p for p in (out/"out/release/rom.bin",out/"out/rom.bin") if p.is_file() and p.stat().st_size>1024),None)
            if rom is None:raise RuntimeError("No ROM output")
            bootenv=env.copy();bootenv.update({"SDL_VIDEODRIVER":"dummy","SDL_AUDIODRIVER":"dummy"})
            fake=job/"fake";fake.mkdir()
            term=fake/"x-terminal-emulator";term.write_text("#!/bin/sh\nexit 99\n");term.chmod(0o755)
            bootenv["PATH"]=f"{fake}:"+bootenv["PATH"]
            cmd(["timeout","120s",str(BLASTEM),"-b","90",str(rom)],log,env=bootenv,timeout=145)
            tail=log.read_text(errors="replace").lower()[-30000:]
            if any(x in tail for x in ("unmapped","fatal exception","lock up","debugger_invoked")):
                raise RuntimeError("BlastEm boot log reported fatal errors")
            digest=sha(rom);match=digest.startswith(ORIGINAL_PREFIX[name])
            target=TARGET/name
            if target.exists():
                if sha(target)!=digest:raise RuntimeError("File with different contents already exists; preserved")
            else:shutil.copy2(rom,target)
            result.append((name,ref,description,extras,"OK",digest,match))
            print(f"OK {name} sha256={digest} original_prefix_match={match}",flush=True)
        except Exception as exc:
            result.append((name,ref,description,extras,f"NAO REPRODUZIDA: {exc}","",False))
            print(f"::warning::{name}: {exc}",flush=True)
    readme=["# M14 — ROMs do Claudio","",
            "Variantes historicas compiladas no runner a partir dos commits que introduziram suas funcoes.",
            "A comparacao de hash com os arquivos originalmente entregues pelo Claudio e informativa;",
            "divergencia nao significa necessariamente falha funcional. Boot headless nao valida video no console.",""]
    for name,ref,description,extras,status,digest,match in result:
        readme.extend([f"## {name}",f"- Finalidade: {description}",f"- Commit de referencia: \`{ref}\`",
                       f"- Estado: {status}"])
        if digest:readme.extend([f"- SHA-256: \`{digest}\`",
                                f"- Hash igual ao prefixo da ROM original: {'SIM' if match else 'NAO (rebuild, nao bit-identico)'}"])
        if extras:readme.append(f"- Flags adicionais: \`{extras}\`")
        readme.append("")
    # Existing Werk ROMs are not changed.
    (TARGET/"README.md").write_text("\n".join(readme)+"\n")
    print("RESULTADO: "+str([(a,e) for a,_,_,_,e,_,_ in result]))

if __name__=="__main__":main()
