#!/usr/bin/env python3
"""R71: join the real compiler output (objdump of the final ELF) with a PC sample histogram (r71_pcsample.py).

Writes OUT/REPORT.md (+ report.json): share of samples per function and per function group, the hottest basic blocks as
annotated listings (heat = samples), and a census of what kind of instruction the CPU spends its samples on
(absolute-long data access, stack access, MUL/DIV, calls, MOVEM, branches). Sampled PCs are the next instruction to run,
so heat can be one instruction late; basic-block totals are the reliable unit.
Usage: r71_asm_report.py --objdump PATH --elf ELF --samples samples.json --out DIR [--label L] [--top-funcs 30] [--top-blocks 24]
"""
import argparse, collections, json, pathlib, re, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from r70_disasm_compare import parse, classify, BRANCH, CALLS, stats  # noqa: E402

GROUPS = [
    ("wall kernel (ASM)", r"^R60_WallColumn"),
    ("wall column C glue", r"^(R_RenderSegLoop|R42_DrawPackedWall|R_DrawSegTextureColumn|R_GetColumn|R_DrawColumnWall|R20_|R64A_|W_GetLumpByNum|R_ComposeColumn)"),
    ("flat span/column", r"^(R_DrawColumnFlat|R_DrawSpan|R_MapPlane|R_MakeSpans|R_DoDrawPlane|R_DrawPlanes|R_DrawSky)"),
    ("sprite/masked draw", r"^(R_DrawColumnSprite|R_DrawMaskedColumn|R_DrawVisSprite|R_DrawMasked|R_DrawPlayerSprites|R46_|R47_)"),
    ("segment setup + geometry", r"^(R_StoreWallRange|R_PointToAngle|R_ScaleFromGlobalAngle|__mulsi3|__udivsi3|__divsi3|__umodsi3|FixedReciprocal|FixedDiv|FixedMul|R_PointToDist)"),
    ("BSP traversal / subsector (incl. inlined seg loop)", r"^(R_AddLine|R_CheckBBox|R_RenderBSPNode|R_RenderBspSubsector|R_ClipWallSegment|R_Subsector|R_CheckOpenings|R_PointOnSide)"),
    ("sprite project/sort", r"^(R_ProjectSprite|R_AddSprites)"),
    ("game logic", r"^(P_|G_|A_|T_|M_Random|D_Think|S_)"),
    ("map streaming", r"^(R23_|R27_|node_read)"),
]


def group_of(name):
    for g, rx in GROUPS:
        if re.search(rx, name):
            return g
    return "other"


def target_of(ins):
    if not BRANCH.match(ins["mn"]) or not ins["ops"]:
        return None
    m = re.match(r"^(?:0x)?([0-9a-f]+)\b", ins["ops"][-1])
    return int(m.group(1), 16) if m and not ins["ops"][-1].startswith("%") else None


def blocks_of(insns):
    """split at branch targets and after branches/rts/jmp; returns list of lists"""
    leaders = {insns[0]["addr"]} if insns else set()
    for k, ins in enumerate(insns):
        t = target_of(ins)
        if t is not None: leaders.add(t)
        if (BRANCH.match(ins["mn"]) or ins["mn"] in ("rts", "rte", "jmp")) and k + 1 < len(insns):
            leaders.add(insns[k + 1]["addr"])
    out, cur = [], []
    for ins in insns:
        if ins["addr"] in leaders and cur:
            out.append(cur); cur = []
        cur.append(ins)
    if cur: out.append(cur)
    return out


def kind(ins):
    mn = ins["mn"]
    if mn.startswith("movem"): return "movem"
    if re.match(r"^(mul|div)[su]", mn): return "mul/div"
    if mn in CALLS or mn in ("rts", "jmp"): return "call/return"
    if BRANCH.match(mn): return "branch"
    ops = [classify(o) for o in ins["ops"]]
    if "abs" in ops: return "absolute-address data access"
    if "stack" in ops: return "stack/frame access"
    if "indirect" in ops or "pcrel" in ops: return "register-indirect / pc-relative access"
    return "register / immediate"


def build(objdump_text, hist):
    funcs = {k: v for k, v in parse(objdump_text).items() if v}
    owner = {}
    ranges = []
    for name, insns in funcs.items():
        ranges.append((insns[0]["addr"], insns[-1]["addr"] + insns[-1]["size"], name))
    ranges.sort()
    starts = [r[0] for r in ranges]
    import bisect
    def fn_of(pc):
        i = bisect.bisect_right(starts, pc) - 1
        if i >= 0 and ranges[i][0] <= pc < ranges[i][1]: return ranges[i][2]
        return None
    heat = collections.Counter()            # instruction address -> samples
    per_fn = collections.Counter(); outside = 0; total = sum(hist.values())
    addr_of = {}
    for name, insns in funcs.items():
        for ins in insns: addr_of[ins["addr"]] = ins
    for pc, c in hist.items():
        fn = fn_of(pc)
        if fn is None:
            outside += c; continue
        per_fn[fn] += c
        ins = addr_of.get(pc)
        if ins is None:                     # PC inside a long instruction: attribute to its start
            for cand in funcs[fn]:
                if cand["addr"] <= pc < cand["addr"] + cand["size"]: ins = cand; break
        heat[ins["addr"] if ins else pc] += c
    return funcs, per_fn, heat, total, outside


def report(label, funcs, per_fn, heat, total, outside, top_funcs=30, top_blocks=24, full_blocks=10):
    L = ["# R71 real-assembly profile: %s" % label, "",
         "%d PC samples (HInt every N lines, VBlank lines not sampled); %d (%.1f%%) outside the linked text." % (
             total, outside, 100.0 * outside / max(1, total)), ""]
    grp = collections.Counter()
    for fn, c in per_fn.items(): grp[group_of(fn)] += c
    L += ["## Function groups", "", "| group | samples | share |", "|---|---:|---:|"]
    for g, c in grp.most_common(): L.append("| %s | %d | %.1f%% |" % (g, c, 100.0 * c / total))
    L += ["", "## Functions (as linked; LTO-inlined code is inside its caller)", "", "| function | samples | share | insns | bytes |", "|---|---:|---:|---:|---:|"]
    for fn, c in per_fn.most_common(top_funcs):
        st = stats(funcs[fn]); L.append("| %s | %d | %.2f%% | %d | %d |" % (fn, c, 100.0 * c / total, st["insns"], st["bytes"]))
    # instruction census (heat-weighted)
    cen = collections.Counter(); addr = {}
    for insns in funcs.values():
        for ins in insns: addr[ins["addr"]] = ins
    for a, c in heat.items():
        if a in addr: cen[kind(addr[a])] += c
    tot = sum(cen.values()) or 1
    L += ["", "## What the CPU is doing (heat-weighted instruction census; heat is skewed by at most one instruction)", "", "| instruction kind | share |", "|---|---:|"]
    for k, c in cen.most_common(): L.append("| %s | %.1f%% |" % (k, 100.0 * c / tot))
    # hottest basic blocks
    blocks = []
    for fn, insns in funcs.items():
        if not per_fn.get(fn): continue
        for b in blocks_of(insns):
            h = sum(heat.get(i["addr"], 0) for i in b)
            if h: blocks.append((h, fn, b))
    blocks.sort(key=lambda x: -x[0])
    L += ["", "## Hottest basic blocks (heat = samples; %% of all samples)", ""]
    for rank, (h, fn, b) in enumerate(blocks[:top_blocks]):
        st = stats(b)
        L.append("### #%d  %s @%x  %d samples (%.2f%%), %d insns, %d bytes, abs %d, stack %d, calls %d" % (
            rank + 1, fn, b[0]["addr"], h, 100.0 * h / total, st["insns"], st["bytes"], st["abs"], st["stack"], st["calls"]))
        if rank < full_blocks:
            L.append("```")
            for i in b: L.append("%x %5d  %s %s" % (i["addr"], heat.get(i["addr"], 0), i["mn"], ",".join(i["ops"])))
            L.append("```")
        L.append("")
    return "\n".join(L) + "\n", {"groups": dict(grp), "functions": dict(per_fn.most_common(top_funcs)), "census": dict(cen), "total": total}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--objdump", required=True); ap.add_argument("--elf", required=True); ap.add_argument("--samples", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--label", default="rom")
    ap.add_argument("--top-funcs", type=int, default=30); ap.add_argument("--top-blocks", type=int, default=24)
    a = ap.parse_args()
    r = subprocess.run([a.objdump, "-d", "-z", a.elf], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("objdump FAILED rc=%d\n%s\n" % (r.returncode, r.stderr)); return 3
    data = json.loads(pathlib.Path(a.samples).read_text())
    hist = {int(k, 16): v for k, v in data["hist"].items()}
    funcs, per_fn, heat, total, outside = build(r.stdout, hist)
    md, js = report(a.label, funcs, per_fn, heat, total, outside, a.top_funcs, a.top_blocks)
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "REPORT.md").write_text(md); (out / "report.json").write_text(json.dumps(js, indent=1))
    print(md[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
