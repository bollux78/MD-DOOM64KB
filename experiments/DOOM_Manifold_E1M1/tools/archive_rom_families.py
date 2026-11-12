#!/usr/bin/env python3
"""Archive reproducible Manifold ROM families to the self-hosted runner ONLY.

Only .bin and README.md are written under /home/dan/Projetos/manifold-doom/roms/MNN.
Build logs, staging and ELF remain under RUNNER_TEMP. No uploads/releases.
"""
from __future__ import annotations
import datetime as dt
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

DEST = Path("/home/dan/Projetos/manifold-doom/roms")
ROOT = Path(os.environ["GITHUB_WORKSPACE"])
TEMP = Path(os.environ["RUNNER_TEMP"]) / ("manifold-archive-" + os.environ.get("GITHUB_RUN_ID", "local"))
WAD = Path("/home/dan/Projetos/doom-md/assets/wads/doom1.wad")
SGDK = Path(os.environ["GDK"])
TC = Path.home() / "mars/m68k-elf/bin/m68k-elf-"
BLASTEM = Path.home() / "Projetos/blastem64-1.0.0/blastem"
UPSTREAM_COMMIT = "b6fe52a52344464de00bde4dc58a40f8b89cfc1a"
FAMILIES = [
    ("M00", None, "Manifold original (sem DOOM)", {}, "Sem receita fiel do binario upstream nesta linha: nao substituir por ROM E1M1."),
    ("M01", None, "Conversor e geometria E1M1 inicial", {}, "Marco estrutural; primeira ROM documentada falhou. Nao atribuir ROM M02 a M01."),
    ("M02", "79bc0ca", "Primeira E1M1 jogavel; corrigido ADDRESS ERROR", {}),
    ("M03", "3f1f648", "Celulas convexas e portais; tour do mapa", {}),
    ("M04", "28ae618", "Texturas/paleta do DOOM e correcoes de colisao", {}),
    ("M05", "59e0c21", "VRAM, ceu SKY1 e degraus texturizados", {}),
    ("M06", "0cf6b10", "Ceu/fog; buffers de arma e geometrias", {}),
    ("M07", "91551fc", "Altura da camera reduzida de 82 para 64", {}),
    ("M08", "f437653", "Portas provisoriamente abertas; camera e escadas", {}),
    ("M09", None, "LOD experimental de cor para paredes distantes", {}, "Existe experimento historico no run 42822447632; falta commit exato para reproduzir sem adulterar a familia."),
    ("M10", "5bde241", "HUD classico DOOM", {"MANIFOLD_HUD": "doom"}),
    ("M11", "2920280", "Near clipping e HUD/arma; renderer E1M1", {"MANIFOLD_H32": "1", "MANIFOLD_HUD": "doom"}),
    ("M12", "0dc3e92", "BSP + raio de colisao + vista estavel", {"MANIFOLD_BSP": "1", "MANIFOLD_RADIUS": "1", "MANIFOLD_STABLE_VIEW": "1", "MANIFOLD_H32": "0"}),
    ("M13", "e99f64c", "BSP com geometria/ceu corrigidos (controle, sem all-leaves)", {"MANIFOLD_BSP": "1", "MANIFOLD_RADIUS": "1", "MANIFOLD_STABLE_VIEW": "1", "MANIFOLD_H32": "0", "MANIFOLD_NEAR_SAFE": "1", "MANIFOLD_BSP_PRECISION": "1", "MANIFOLD_SKY_MERGE": "1", "MANIFOLD_BSP_ALL_LEAVES": "0"}),
    ("M14", "e324839", "Objetos, portas, pickups, pistola, grades e identidade", {"MANIFOLD_BSP": "0", "MANIFOLD_RADIUS": "1", "MANIFOLD_STABLE_VIEW": "1", "MANIFOLD_H32": "0", "MANIFOLD_HUD_TIMING": "1", "MANIFOLD_STATIC_REPAIR_ONCE": "1", "MANIFOLD_NEAR_SAFE": "1", "MANIFOLD_SKY_MERGE": "1", "MANIFOLD_OBJECTS": "1", "MANIFOLD_PICKUPS": "1", "MANIFOLD_DOORS": "1", "MANIFOLD_EYE": "48", "MANIFOLD_TEX_U": "1", "MANIFOLD_TEX_HSTRETCH": "1.0", "MANIFOLD_WEAPON": "pistol", "MANIFOLD_ROM_NAME": "MANIFOLD M14", "MANIFOLD_ROM_TEST": "E1M1 OBJECTS DOORS PICKUPS"}),
]

EXPANDED_VARIANTS = [["M09","2ca6ad82","LOD distante rejeitado",{},"werk-m09-lod-rejeitado.bin"],["M11","7be9eef9","Camera fixa H32",{"MANIFOLD_CAMERAS":"fixed","MANIFOLD_H32":"1","MANIFOLD_HUD":"doom"},"werk-m11-camera-fixa-h32.bin"],["M11","7be9eef9","Cache de vertices fixo",{"MANIFOLD_CAMERAS":"fixed","MANIFOLD_VERT_CACHE":"1","MANIFOLD_H32":"1"},"werk-m11-cache-fixo-h32.bin"],["M11","7be9eef9","Cache de vertices jogavel",{"MANIFOLD_VERT_CACHE":"1","MANIFOLD_H32":"1"},"werk-m11-cache-play-h32.bin"],["M11","7be9eef9","Fog desligado",{"MANIFOLD_SKIP":"far_portal_fog","MANIFOLD_CAMERAS":"fixed","MANIFOLD_H32":"1"},"werk-m11-fogoff-h32.bin"],["M11","7be9eef9","Musica H32",{"MANIFOLD_H32":"1"},"werk-m11-music-h32.bin"],["M11","90d53168","Near clipping seguro",{"MANIFOLD_H32":"0","MANIFOLD_NEAR_SAFE":"1"},"werk-m11-near-safe-h40.bin"],["M12","88c735c4","Controle H40 musical",{"MANIFOLD_H32":"0"},"werk-m12-control-h40.bin"],["M12","88c735c4","BSP estavel H40",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0"},"werk-m12-bsp-play-h40.bin"],["M12","74133dc0","BSP precisao H40",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_BSP_PRECISION":"1"},"werk-m12-bsp-precision-h40.bin"],["M13","2394a7bc","HUD timing",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_HUD_TIMING":"1"},"werk-m13-hud-timing-h40.bin"],["M13","9cb7c1a3","Near clipping geometrico",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_NEAR_SAFE":"1"},"werk-m13-near-safe-h40.bin"],["M13","ec7957a0","BSP precisao",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_NEAR_SAFE":"1","MANIFOLD_BSP_PRECISION":"1"},"werk-m13-bsp-precision-h40.bin"],["M13","abf0c1f2","Sky merge",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_NEAR_SAFE":"1","MANIFOLD_BSP_PRECISION":"1","MANIFOLD_SKY_MERGE":"1"},"werk-m13-sky-merge-h40.bin"],["M13","5bb039ed","Sky ceiling",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_NEAR_SAFE":"1","MANIFOLD_BSP_PRECISION":"1","MANIFOLD_SKY_MERGE":"1","MANIFOLD_SKY_CEIL_UNIFORM":"1"},"werk-m13-sky-ceiling-h40.bin"],["M13","e99f64c8","All leaves controle",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_NEAR_SAFE":"1","MANIFOLD_BSP_PRECISION":"1","MANIFOLD_SKY_MERGE":"1","MANIFOLD_BSP_ALL_LEAVES":"0"},"werk-m13-allleaves-control-h40.bin"],["M13","e99f64c8","All leaves experimental",{"MANIFOLD_BSP":"1","MANIFOLD_RADIUS":"1","MANIFOLD_STABLE_VIEW":"1","MANIFOLD_H32":"0","MANIFOLD_NEAR_SAFE":"1","MANIFOLD_BSP_PRECISION":"1","MANIFOLD_SKY_MERGE":"1","MANIFOLD_BSP_ALL_LEAVES":"1"},"werk-m13-allleaves-h40.bin"]]
if os.environ.get('MANIFOLD_ARCHIVE_EXPANDED') == '1':
    FAMILIES = EXPANDED_VARIANTS

def run(cmd, *, cwd=None, env=None, log=None, timeout=1800):
    with (open(log, "a") if log else open(os.devnull, "w")) as fd:
        return subprocess.run(cmd, cwd=cwd, env=env, stdout=fd, stderr=subprocess.STDOUT, timeout=timeout, check=True)

def write_readme(folder, code, title, message, ref=""):
    # README is permitted by user. No other sidecar files in destination.
    p = folder / "README.md"
    if os.environ.get("MANIFOLD_ARCHIVE_EXPANDED") == "1" and p.exists():
        p.write_text(p.read_text(encoding="utf-8") + "\n## " + title + "\n\n" + message + "\n", encoding="utf-8")
        return
    p.write_text(f"# {code} — {title}\n\n{message}\n" + (f"\nReferencia de codigo: \`{ref}\`\n" if ref else ""), encoding="utf-8")

def main():
    if not WAD.is_file() or WAD.stat().st_size != 4196020:
        raise SystemExit(f"WAD shareware esperado ausente/incorreto: {WAD}")
    if not (SGDK / "makefile.gen").is_file() or not Path(str(TC) + "gcc").is_file():
        raise SystemExit("Toolchain SGDK/M68K ausente; nenhuma ROM modificada.")
    if not DEST.parent.is_dir():
        raise SystemExit(f"Diretorio pai nao existe: {DEST.parent}")
    DEST.mkdir(exist_ok=True)
    test = DEST / ".write-check"
    test.write_text("ok")
    test.unlink()
    TEMP.mkdir(parents=True, exist_ok=True)

    # Work on disposable SDK makefile; do not touch the installed SDK.
    s = (SGDK / "makefile.gen").read_text()
    pat = "-flto -flto=auto -ffat-lto-objects"
    if s.count(pat) < 2:
        raise SystemExit("Unexpected SGDK makefile flags; refusing unverified toolchain modification.")
    makefile = TEMP / "makefile-no-lto.gen"
    makefile.write_text(s.replace(pat, "-fno-lto"))
    native_xgm = Path.home() / "mars/m68k-elf/bin/xgmtool"
    xgm = SGDK / "bin/xgmtool"
    if not xgm.exists() and native_xgm.is_file():
        xgm.symlink_to(native_xgm)

    upstream = TEMP / "upstream"
    run(["git", "clone", "--quiet", "https://github.com/ehaliewicz/Manifold.git", str(upstream)],
        log=TEMP / "clone.log", timeout=240)
    run(["git", "checkout", "--quiet", "--detach", UPSTREAM_COMMIT],
        cwd=upstream, log=TEMP / "clone.log", timeout=60)

    results = []
    for code, ref, title, flags, *rest in FAMILIES:
        folder = DEST / code
        folder.mkdir(exist_ok=True)
        if ref is None:
            msg = "NAO REPRODUZIDA. " + (rest[0] if rest else "Sem receita historica validada.")
            write_readme(folder, code, title, msg)
            results.append((code, "NAO REPRODUZIDA"))
            continue
        scratch = TEMP / (code + '-' + (rest[0].removesuffix('.bin') if rest else 'base'))
        src = scratch / "repo"
        staged = scratch / "stage"
        log = TEMP / f"{code}.log"
        scratch.mkdir(exist_ok=True)
        try:
            # git archive from the full-history checkout. Avoid checking out
            # historical revisions into the shared working directory.
            with open(scratch / "source.tar", "wb") as fd:
                subprocess.run(["git", "-C", str(ROOT), "archive", ref],
                               stdout=fd, stderr=subprocess.PIPE, check=True, timeout=90)
            src.mkdir()
            with tarfile.open(scratch / "source.tar") as archive:
                archive.extractall(src, filter="data")
            stage_script = src / "experiments/DOOM_Manifold_E1M1/m01/stage_rom.py"
            if not stage_script.exists():
                raise RuntimeError("stage_rom.py nao existia neste commit")

            env = os.environ.copy()
            env.update(flags)
            env.update({"GDK": str(SGDK), "PREFIX": str(TC),
                        "MANIFOLD_MUSIC_VGM": str(src / "res/r25-e1m1.vgm"),
                        "PATH": f"{TC.parent}:{SGDK}/bin:" + env.get("PATH", "")})
            # M11+ uses embedded XGM. Older stages may ignore this flag.
            if code in {"M11", "M12", "M13", "M14"}:
                prep = src / "scripts/lab/prepare_r25_music.py"
                if prep.exists():
                    env["DOOM_R25_MUSIC"] = "1"
                    run([sys.executable, str(prep)], cwd=src, env=env, log=log, timeout=120)
                env["MANIFOLD_MUSIC"] = "1"
                if not (src / "res/r25-e1m1.vgm").exists():
                    raise RuntimeError("VGM necessario nao encontrado na revisao")
            run([sys.executable, str(stage_script), "--source", str(upstream),
                 "--wad", str(WAD), "--out", str(staged)], cwd=src, env=env, log=log)
            old = staged / "src/math3d.h"
            link = staged / "src/math3D.h"
            if old.exists() and not link.exists():
                link.symlink_to("math3d.h")
            cmd = ["make", "-C", str(staged), "-f", str(makefile), "-j2", "release",
                   "OS=Linux", f"GDK={SGDK}", f"PREFIX={TC}",
                   f"CC={TC}gcc", f"LD={TC}ld", f"AR={TC}ar",
                   f"NM={TC}nm", f"OBJCPY={TC}objcopy"]
            run(cmd, env=env, log=log)
            rom = next((p for p in (staged / "out/release/rom.bin",
                                    staged / "out/rom.bin") if p.is_file() and p.stat().st_size > 1024), None)
            if rom is None:
                raise RuntimeError("Build terminou sem rom.bin valido")
            # Validate boot before publishing, with no persistent debug files.
            if not BLASTEM.is_file():
                raise RuntimeError("BlastEm local nao encontrado para validar boot")
            debug = TEMP / "no-debug"
            debug.mkdir(exist_ok=True)
            term = debug / "x-terminal-emulator"
            term.write_text("#!/bin/sh\nexit 99\n")
            term.chmod(0o755)
            bootenv = env.copy()
            bootenv.update({"SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy",
                            "PATH": f"{debug}:" + env["PATH"]})
            run(["timeout", "120s", str(BLASTEM), "-b", "90", str(rom)],
                env=bootenv, log=log, timeout=145)
            data = log.read_text(errors="replace").lower()
            if any(k in data[-25000:] for k in ("unmapped", "fatal exception", "lock up")):
                raise RuntimeError("BlastEm indicou erro de boot")
            mode = "h32" if flags.get("MANIFOLD_H32") == "1" else "h40"
            if code in {"M02","M03","M04","M05","M06","M07","M08","M10"}:
                mode = "legacy"  # early stages did not universally use H40
            name = rest[0] if rest else f"werk-{code.lower()}-historico-{mode}.bin"
            target = folder / name
            if target.exists():
                import hashlib
                def sha(p):
                    h = hashlib.sha256()
                    with p.open("rb") as f:
                        for chunk in iter(lambda: f.read(1 << 20), b""):
                            h.update(chunk)
                    return h.digest()
                if sha(target) != sha(rom):
                    raise RuntimeError(f"{name} ja existe com hash distinto; nada sobrescrito")
            else:
                shutil.copy2(rom, target)
            write_readme(folder, code, title,
                         f"ROM: \`{name}\`\n\nCompilacao e boot headless (90 quadros): OK. "
                         "Isso nao certifica a imagem nem a jogabilidade em hardware. "
                         f"\n\nFlags: \`{flags}\`", ref)
            results.append((code, "OK"))
        except Exception as exc:
            msg = f"NAO REPRODUZIDA nesta execucao: {type(exc).__name__}: {exc}. "
            msg += "Consultar o log temporario do job do GitHub Actions. "
            msg += "Se ja havia ROM antiga nesta pasta, ela foi preservada."
            write_readme(folder, code, title, msg, ref)
            results.append((code, "NAO REPRODUZIDA"))
            print(f"::warning::{code}: {exc}", flush=True)
        print(f"{code}: {results[-1][1]}", flush=True)
    print("\nRESULTADO FINAL")
    for code, state in results:
        print(f"{code}: {state}")

if __name__ == "__main__":
    main()
