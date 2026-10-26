#!/usr/bin/env python3
"""R70 comparative disassembly: static instruction, size and memory-operand counts of selected routines for several ELFs.

Usage: r70_disasm_compare.py --objdump PATH --func NAME[,NAME..] OUT_DIR label=elf [label=elf ...]
Writes OUT_DIR/disasm-<label>-<func>.txt (full listing of each routine), DISASM-COMPARE.md and disasm.json.
Static counts, not dynamic: a loop body is counted once. The dynamic result is the timedemo timing.
A routine that LTO inlined into another one is reported as missing; compare the caller (e.g. R_StoreWallRange).
"""
import sys, argparse, json, pathlib, re, subprocess, sys

BRANCH = re.compile(r"^(bra|bsr|b(hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le))[sw]?$|^db[a-z]{1,2}$|^(jmp|jsr)$")
HEXWORD = re.compile(r"^[0-9a-f]{4}$")
CALLS = ("jsr", "bsr", "bsrs", "bsrw")


def split_operands(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(": depth += 1
        elif ch == ")": depth -= 1
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    if cur: out.append(cur)
    return [o.strip() for o in out]


def classify(op):
    """-> one of imm, reg, abs, stack, indirect, pcrel, other"""
    op = op.split(";")[0].strip()
    if op.startswith("#"): return "imm"
    if re.fullmatch(r"%[a-z0-9]+(-%[a-z0-9]+)?(/%[a-z0-9]+)*", op) and "@" not in op: return "reg"
    if op.startswith("%pc@"): return "pcrel"
    if re.match(r"%(sp|fp|a7|a6)@", op): return "stack"
    if "@" in op: return "indirect"
    if re.match(r"^(0x)?[0-9a-f]+(\s*<.*>)?$", op): return "abs"
    return "other"


def parse(text):
    """objdump -d (raw bytes shown) -> {symbol: [ {addr, size, mn, ops} ]}"""
    funcs, cur, last = {}, None, None
    for line in text.splitlines():
        m = re.match(r"^[0-9a-f]+ <(.+)>:$", line)
        if m:
            cur = m.group(1); funcs[cur] = []; last = None; continue
        if cur is None: continue
        m = re.match(r"^\s*([0-9a-f]+):\t([0-9a-f ]+?)\s*(?:\t(.*))?$", line)
        if not m: continue
        words = [w for w in m.group(2).split() if HEXWORD.match(w)]
        body = (m.group(3) or "").strip()
        if not body and last is not None:      # continuation of a long instruction
            last["size"] += 2 * len(words); continue
        if not body: continue
        body = body.split("|")[0].strip()
        mn, _, rest = body.partition(" ")
        last = {"addr": int(m.group(1), 16), "size": 2 * len(words), "mn": mn, "ops": split_operands(rest.strip())}
        funcs[cur].append(last)
    return funcs


def stats(insns):
    s = {"insns": len(insns), "bytes": sum(i["size"] for i in insns), "abs": 0, "stack": 0, "indirect": 0, "pcrel": 0,
         "mem_total": 0, "calls": 0, "branches": 0, "movem": 0, "mul_div": 0}
    for i in insns:
        mn = i["mn"]
        if mn in CALLS: s["calls"] += 1
        if BRANCH.match(mn): s["branches"] += 1
        if mn.startswith("movem"): s["movem"] += 1
        if re.match(r"^(mul|div)[su]", mn): s["mul_div"] += 1
        if BRANCH.match(mn):
            continue                            # branch targets are code, not data accesses
        for op in i["ops"]:
            c = classify(op)
            if c in ("abs", "stack", "indirect", "pcrel"):
                s[c] += 1; s["mem_total"] += 1
    return s


def pick(funcs, name):
    """exact symbol or LTO/ISRA/PART variants; returns {symbol: insns}"""
    return {k: v for k, v in funcs.items() if k == name or re.match(re.escape(name) + r"\.(lto_priv|isra|part|constprop|cold)", k)}


def report(results, labels, funcnames):
    L = ["# R70 comparative disassembly (static counts)", "",
         "Counts are per routine as linked, loop bodies counted once. `mem` = data memory operands (abs + stack/frame + other An-indirect + pc-relative);",
         "`abs` are the 20-cycle absolute-long style accesses the R70-A locals aim to replace by cheaper frame/register accesses.", ""]
    for fn in funcnames:
        L += ["## " + fn, "", "| variant | symbol | insns | bytes | mem | abs | stack/fp | indirect | calls | mul/div | movem |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        base = None
        for lab in labels:
            found = results[lab].get(fn)
            if not found:
                L.append("| %s | (not a symbol: inlined into its caller) | | | | | | | | | |" % lab); continue
            for sym, st in found.items():
                if base is None: base = st
                L.append("| %s | %s | %d | %d | %d | %d | %d | %d | %d | %d | %d |" % (
                    lab, sym, st["insns"], st["bytes"], st["mem_total"], st["abs"], st["stack"], st["indirect"], st["calls"], st["mul_div"], st["movem"]))
        if base:
            L += ["", "Delta vs first variant listed (same symbol order):", ""]
            for lab in labels[1:]:
                f0 = next(iter(results[labels[0]].get(fn, {}).values()), None); f1 = next(iter(results[lab].get(fn, {}).values()), None)
                if f0 and f1:
                    L.append("- %s: insns %+d, bytes %+d, mem %+d (abs %+d, stack/fp %+d)" % (
                        lab, f1["insns"] - f0["insns"], f1["bytes"] - f0["bytes"], f1["mem_total"] - f0["mem_total"],
                        f1["abs"] - f0["abs"], f1["stack"] - f0["stack"]))
        L.append("")
    return "\n".join(L) + "\n"


def diff_section(allstats, labels, top=14):
    """Functions whose static counts differ from the first label: finds code that LTO inlined elsewhere."""
    L = ["## Functions whose code differs from `%s` (all symbols, by |bytes delta|)" % labels[0], ""]
    base = allstats[labels[0]]
    for lab in labels[1:]:
        rows = []
        for sym in set(base) | set(allstats[lab]):
            a, b = base.get(sym), allstats[lab].get(sym)
            if a is None or b is None:
                rows.append((sym, None if a is None else a, None if b is None else b)); continue
            if (a["insns"], a["bytes"], a["abs"], a["stack"]) != (b["insns"], b["bytes"], b["abs"], b["stack"]):
                rows.append((sym, a, b))
        L += ["### %s: %d differing symbols" % (lab, len(rows)), ""]
        if rows:
            L += ["| symbol | insns | bytes | mem | abs | stack/fp |", "|---|---|---|---|---|---|"]
        def key(r):
            a, b = r[1], r[2]
            return -abs((b["bytes"] if b else 0) - (a["bytes"] if a else 0))
        for sym, a, b in sorted(rows, key=key)[:top]:
            if a is None or b is None:
                L.append("| %s | only in %s | | | | |" % (sym, lab if a is None else labels[0])); continue
            L.append("| %s | %d -> %d | %d -> %d | %d -> %d | %d -> %d | %d -> %d |" % (
                sym, a["insns"], b["insns"], a["bytes"], b["bytes"], a["mem_total"], b["mem_total"], a["abs"], b["abs"], a["stack"], b["stack"]))
        L.append("")
    return L


def run_objdump(objdump, elf):
    """objdump -d; on failure keep the detailed stderr (tool, ELF, return code) and stop with a readable error."""
    r = subprocess.run([objdump, "-d", "-z", str(elf)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write("objdump FAILED rc=%d cmd=%s -d -z %s\n--- objdump stderr ---\n%s\n" % (r.returncode, objdump, elf, r.stderr))
        sys.exit(3)
    return r.stdout


def run(objdump, funcnames, out, pairs):
    out = pathlib.Path(out); out.mkdir(parents=True, exist_ok=True)
    results, labels, allstats = {}, [], {}
    for lab, elf in pairs:
        text = run_objdump(objdump, elf)
        funcs = parse(text)
        allstats[lab] = {k: stats(v) for k, v in funcs.items() if v}
        labels.append(lab); results[lab] = {}
        for fn in funcnames:
            found = pick(funcs, fn)
            if not found: continue
            results[lab][fn] = {k: stats(v) for k, v in found.items()}
            listing = []
            for k, v in found.items():
                listing.append("<%s>:" % k)
                listing += ["%x\t%s %s" % (i["addr"], i["mn"], ",".join(i["ops"])) for i in v]
            (out / ("disasm-%s-%s.txt" % (lab, fn))).write_text("\n".join(listing) + "\n")
    (out / "disasm.json").write_text(json.dumps(results, indent=1))
    md = report(results, labels, funcnames) + "\n".join(diff_section(allstats, labels)) + "\n"
    # full listings of the (up to 4) most changed functions, so the inlined loop can be read
    if len(labels) > 1:
        ctl = allstats[labels[0]]
        changed = sorted({s for lab in labels[1:] for s in allstats[lab] if s in ctl and allstats[lab][s]["bytes"] != ctl[s]["bytes"]},
                         key=lambda s: -max(abs(allstats[lab][s]["bytes"] - ctl[s]["bytes"]) for lab in labels[1:] if s in allstats[lab]))[:4]
        for lab, elf in pairs:
            funcs = parse(run_objdump(objdump, elf))
            for sym in changed:
                if sym in funcs:
                    (out / ("disasm-%s-changed-%s.txt" % (lab, sym.replace("/", "_")))).write_text(
                        "\n".join("%x\t%s %s" % (i["addr"], i["mn"], ",".join(i["ops"])) for i in funcs[sym]) + "\n")
    (out / "DISASM-COMPARE.md").write_text(md)
    return results, md


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--objdump", required=True); ap.add_argument("--func", default="R_RenderSegLoop,R_StoreWallRange")
    ap.add_argument("out"); ap.add_argument("pairs", nargs="+")
    a = ap.parse_args()
    pairs = [tuple(p.split("=", 1)) for p in a.pairs]
    _, md = run(a.objdump, a.func.split(","), a.out, pairs)
    print(md)


if __name__ == "__main__":
    main()
