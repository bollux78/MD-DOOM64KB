#!/usr/bin/env python3
"""R117 (Claudio): per-map statistical profile of the R116 demos in BlastEm (PERF demotest ROM).

One BlastEm process per call, <= 10,000 emulated frames (AGENTS.md). Emulator measurement: relative
shares and VBlank costs, not console cycles.
  1. At the first G_Ticker: r116_sel=--demo, r116_norender=1 (logic only) for --skip tics.
  2. Then r116_norender=--norender and sampling until the frame budget ends:
     - one PC sample per VBlank (level-6 handler breakpoint; exception frame PC, caller hint as in r94);
     - with rendering, one record per presented frame (I_FinishUpdate entry: VBlank count, tic).
  Stops early at R116_End (demo data ended) or I_Error.
Outputs OUT/samples.tsv, OUT/frames.tsv, OUT/PROFILE.json (functions, categories, VBlanks per tic,
VBlanks per frame, worst 1 s windows inside the sampled range).
Categories come from function names; helpers (__mulsi3, __udivsi3, L4, memcpy, R23_MapRead*) are
charged to the caller's category. A run of >= 90 samples (1.5 s) on the same tic is LOAD (level setup).
"""
import argparse, bisect, collections, importlib.util, json, os, pathlib, subprocess, sys


def load_mod(name):
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(name, here / (name + ".py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


HELPERS = ("__mulsi3", "__udivsi3", "__divsi3", "__modsi3", "__umodsi3", "L4", "memcpy", "memset", "R23_MapRead", "R23_MapWrite",
           "R22_BlockHead", "FixedMul", "FixedDiv")


def category(fn):
    f = fn.split(".")[0]
    if f.startswith(("P_Load", "P_SetupLevel", "P_GroupLines", "R22_BlockInit", "R23_MapMemoryInit", "R24_", "W_", "P_SpawnSpecials",
                     "P_InitThinkers", "P_RemoveSlimeTrails", "Z_FreeTags", "R84_", "P_FreeLevelData")):
        return "LOAD"
    if f.startswith(("R60_", "R113_", "R108_", "R_DrawSegTextureColumn", "R_DrawColumnWall", "R96_")): return "R_WALL_COLUMNS"
    if f.startswith(("R_DrawColumnSprite", "R_DrawVisSprite", "R_ProjectSprite", "R_DrawMasked", "R_DrawSprite", "R_RenderMaskedSegRange",
                     "R_DrawPSprite", "R_DrawMaskedColumn", "R_SortVisSprites", "make")): return "R_SPRITES_MASKED"
    if f.startswith(("R_Subsector", "R_RenderSegLoop", "R_StoreWallRange", "R_AddLine", "R_CheckBBox", "R_RenderBSPNode", "R_ClipSolid",
                     "R_ClipPass", "R_PointToAngle", "R_ScaleFromGlobalAngle", "R_PointOnSide", "R_ComposeColumn", "R95_", "R_LoadColorMap",
                     "R_GetColumn", "R_DrawPlanes", "R_FindPlane", "R_MapPlane")): return "R_BSP_SEGS_FLATS"
    if f.startswith(("R_SetupFrame", "R_Clear", "R_RenderPlayerView", "R64A")): return "R_SETUP"
    if f.startswith(("R92_", "R97_", "R91_", "R79_")): return "SHADOW"
    if f.startswith(("I_FinishUpdate", "R22_", "R20_", "R57_", "R35_", "I_Benchmark", "D_Display", "ST_", "HU_", "V_", "R51_", "R76_",
                     "VDP_", "DMA_", "R81_")): return "PRESENT_HUD_VDP"
    if f.startswith(("D_DoomLoop",)): return "MAINLOOP_WAIT"
    if f.startswith(("P_CheckSight", "P_CrossBSPNode", "P_CrossSubsector", "P_DivlineSide", "P_InterceptVector")): return "L_SIGHT"
    if f.startswith(("P_RecursiveSound", "P_NoiseAlert")): return "L_SOUND_ALERT"
    if f.startswith(("P_TryMove", "P_CheckPosition", "PIT_", "P_BlockLinesIterator", "P_BlockThingsIterator", "P_SetThingPosition",
                     "P_UnsetThingPosition", "P_LineOpening", "P_BoxOnLineSide", "P_PointOnLineSide", "P_SlideMove", "PTR_", "P_PathTraverse",
                     "P_AimLineAttack", "P_LineAttack", "P_XYMovement", "P_ZMovement", "P_ThingHeightClip", "P_ChangeSector",
                     "P_RadiusAttack", "P_UseLines", "P_HitSlideLine", "P_TeleportMove", "P_Move", "P_TryWalk", "P_NewChaseDir",
                     "P_CreateSecNodeList", "P_DelSeclist", "P_AddSecnode", "P_DelSecnode")): return "L_MOVE_COLLIDE"
    if f.startswith(("A_", "P_LookForPlayers", "P_LookForTargets", "P_CheckMeleeRange", "P_CheckMissileRange", "P_SetMobjState",
                     "P_MobjThinker", "P_SpawnMobj", "P_RemoveMobj", "P_DamageMobj", "P_KillMobj", "P_SpawnMissile", "P_Random",
                     "P_Ticker", "P_RunThinkers", "P_PlayerThink", "P_MovePsprites", "P_SetPsprite", "P_Thrust", "P_CalcHeight")): return "L_AI_THINKERS"
    if f.startswith(("T_", "EV_", "P_UpdateSpecials", "P_PlayerInSpecialSector", "P_CrossSpecialLine", "P_ShootSpecialLine",
                     "P_ChangeSwitchTexture", "P_FindSector", "P_FindNext", "P_FindLowest", "P_FindHighest", "getNext", "P_FindMin")): return "L_SPECIALS"
    if f.startswith(("G_", "M_", "P_", "D_AdvanceDemo", "R116_", "R117_")): return "L_OTHER"
    if f.startswith(("S_", "XGM", "Z80", "SND", "DMX", "R25_", "R29_", "R31_")): return "SOUND_MUSIC"
    if f.startswith(("Z_",)): return "ZONE"
    if f.startswith(("_V", "_I", "_vint", "SYS_", "I_VBlank", "_Vecteurs", "_start", "JOY_")): return "IRQ_SYS"
    return "OTHER"


def is_helper(fn):
    return fn.split(".")[0].startswith(HELPERS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--demo", type=int, required=True)
    ap.add_argument("--skip", type=int, default=0, help="logic-only tics before sampling")
    ap.add_argument("--norender", type=int, choices=(0, 1), default=0, help="render state while sampling")
    ap.add_argument("--max-emulated-frames", type=int, default=9800); ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args(); assert 1 <= a.max_emulated_frames <= 10000 and 1 <= a.demo <= 10
    rsp = load_mod("r64a_rsp_capture"); r94 = load_mod("r94_pcprofile")
    syms = rsp.symbols(a.elf)
    def sym(n):
        if n in syms: return syms[n] & 0xFFFFFF
        m = [v for k, v in syms.items() if k.startswith(n + ".")]; assert len(m) == 1, (n, m); return m[0] & 0xFFFFFF
    text = r94.text_symbols(a.elf); addrs = [s[0] for s in text]; retset = r94.return_sites(a.elf)
    fn = lambda pc: r94.find(text, addrs, pc)
    tic_a, lt_a, vb_a = sym("_g_gametic"), sym("_g_leveltime"), sym("_g_vblankCount")
    tk, fin, end, err = sym("G_Ticker"), sym("I_FinishUpdate"), sym("R116_End"), sym("I_Error")
    vint = int.from_bytes(open(a.rom, "rb").read()[0x78:0x7C], "big") & 0xFFFFFF
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=False)
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, a.timeout)
    samples, frames, status, tics, sampling = [], [], "frame_limit", 0, False
    be = lambda b: int.from_bytes(b, "big")
    try:
        g.req("qSupported")
        for bp in (tk, end, err): assert g.req("Z0,%x,2" % bp) == "OK"
        armed = False
        def start_sampling():
            assert g.req("M%x,1:%02x" % (sym("r116_norender"), a.norender)) == "OK"
            assert g.req("z0,%x,2" % tk) == "OK"
            assert g.req("Z0,%x,2" % vint) == "OK"
            if not a.norender: assert g.req("Z0,%x,2" % fin) == "OK"
        while True:
            try:
                g.cont()
            except TimeoutError:
                status = "timeout"; break
            except RuntimeError as e:
                status = "frame_limit" if ("EOF" in str(e) or "exited" in str(e)) else "error: %s" % e; break
            regs = g.req("g"); pc = int(regs[17 * 8:18 * 8], 16) & 0xFFFFFF; sp = int(regs[15 * 8:16 * 8], 16) & 0xFFFFFF
            if pc == tk:
                if not armed:
                    assert g.req("M%x,1:%02x" % (sym("r116_sel"), a.demo)) == "OK"
                    assert g.req("M%x,1:01" % sym("r116_norender")) == "OK"; armed = True
                tics += 1
                if tics > a.skip and not sampling:
                    sampling = True; start_sampling()
                continue
            if pc == end: status = "demo_end"; break
            if pc == err: status = "i_error"; break
            if pc == fin:
                frames.append((be(g.readmem(vb_a, 4)), be(g.readmem(tic_a, 4)), be(g.readmem(lt_a, 4)))); continue
            if pc == vint:
                fr = g.readmem(sp, 70)
                ipc = be(fr[2:6]) & 0xFFFFFF
                stack = [be(fr[i:i + 4]) & 0xFFFFFF for i in range(6, 70, 2)]
                ret = next((v for v in stack if v in retset), 0)
                samples.append((be(g.readmem(tic_a, 4)), be(g.readmem(lt_a, 4)), ipc, ret))
    except Exception as e:
        status = "probe_error: %s" % e
    finally:
        g.close()
    with open(out / "samples.tsv", "w") as f:
        for t, lt, p, r in samples: f.write("%d\t%d\t%06x\t%06x\n" % (t, lt, p, r))
    with open(out / "frames.tsv", "w") as f:
        for vb, t, lt in frames: f.write("%d\t%d\t%d\n" % (vb, t, lt))
    # LOAD detection: runs of >= 90 consecutive samples on one tic.
    load = [False] * len(samples); i = 0
    while i < len(samples):
        j = i
        while j < len(samples) and samples[j][0] == samples[i][0]: j += 1
        if j - i >= 90:
            for k in range(i, j): load[k] = True
        i = j
    byf, byc, byc_play = collections.Counter(), collections.Counter(), collections.Counter()
    for (t, lt, p, r), ld in zip(samples, load):
        f = fn(p); byf[f] += 1
        c = category(fn(r)) if is_helper(f) and r else category(f)
        if ld: c = "LOAD"
        byc[c] += 1
        if not ld: byc_play[c] += 1
    n = max(len(samples), 1); npl = max(sum(byc_play.values()), 1)
    play_tics = sorted({t for (t, lt, p, r), ld in zip(samples, load) if not ld})
    res = {"rom": a.rom, "demo": a.demo, "skip": a.skip, "norender": a.norender, "status": status, "samples": len(samples),
           "load_samples": sum(load), "tic_range": [samples[0][0], samples[-1][0]] if samples else None,
           "vblanks_per_tic_excl_load": round(npl / max(len(play_tics) - 1, 1), 3) if play_tics else None,
           "categories_excl_load": {k: round(v / npl, 4) for k, v in byc_play.most_common()},
           "categories_all": {k: round(v / n, 4) for k, v in byc.most_common()},
           "top_functions": [{"function": f, "samples": c, "share": round(c / n, 4)} for f, c in byf.most_common(40)]}
    if len(frames) > 2:
        cost = [frames[i][0] - frames[i - 1][0] for i in range(2, len(frames))]   # drop the first frame after the skip
        cost_ok = [c for c in cost if c < 60]                                    # a load inside a frame is not a frame cost
        res["frames"] = len(cost); res["vblanks_per_frame"] = round(sum(cost_ok) / max(len(cost_ok), 1), 3)
        res["frame_cost_p99"] = sorted(cost_ok)[int(0.99 * (len(cost_ok) - 1))] if cost_ok else None
        res["frame_cost_max"] = max(cost_ok) if cost_ok else None
        res["frames_over_60vb"] = len(cost) - len(cost_ok)
        # Slowest 1 s windows (>= 60 VBlanks of consecutive frames without a load).
        wins = []; i0 = 1
        for i in range(2, len(frames)):
            if frames[i][0] - frames[i - 1][0] >= 60: i0 = i; continue
            while frames[i][0] - frames[i0][0] >= 60:
                el = frames[i][0] - frames[i0][0]
                wins.append((round((i - i0) * 60 / el, 2), frames[i0][1], frames[i0][2], el)); i0 += 1
        wins.sort()
        res["worst_windows"] = [{"fps": w[0], "gametic": w[1], "leveltime": w[2], "vblanks": w[3]} for w in wins[:8]]
        if wins:
            # Category shares inside the worst window.
            w = wins[0]; t0 = w[1]; t1 = t0 + max(1, round(w[3] * w[0] / 60))
            cw = collections.Counter()
            for (t, lt, p, r), ld in zip(samples, load):
                if t0 <= t <= t1 and not ld:
                    f = fn(p); cw[category(fn(r)) if is_helper(f) and r else category(f)] += 1
            tot = max(sum(cw.values()), 1)
            res["worst_window_categories"] = {k: round(v / tot, 3) for k, v in cw.most_common()}
    (out / "PROFILE.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res.get(k) for k in ("demo", "skip", "norender", "status", "samples", "load_samples", "vblanks_per_tic_excl_load",
                                                "vblanks_per_frame", "frame_cost_p99", "categories_excl_load")}))
    if not samples: sys.exit("no samples: " + status)


if __name__ == "__main__":
    main()
