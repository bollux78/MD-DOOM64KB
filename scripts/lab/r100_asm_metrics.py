#!/usr/bin/env python3
"""R100: static code metrics of the function(s) holding the seg loop (objdump -d text), control vs candidate.
Counts per function: bytes, instructions, stack-frame accesses ((%fp)/(%sp) with displacement),
read-modify-write to the stack frame, MOVEM, JSR/BSR, LINK frame size. Usage: OBJDUMP_TXT FUNC [FUNC...]"""
import re, sys, json
txt = open(sys.argv[1]).read().splitlines(); want = set(sys.argv[2:]); cur = None; res = {}
rmw = re.compile(r'\t(add|sub|and|or|eor)[lwb]\s+%d\d,%(fp|sp)@\(')
for line in txt:
    m = re.match(r'^([0-9a-f]{8}) <([^>]+)>:', line)
    if m:
        cur = m[2] if m[2] in want else None
        if cur: res[cur] = dict(start=int(m[1], 16), end=int(m[1], 16), insns=0, stack_access=0, stack_rmw=0, movem=0, calls=0, link=None)
        continue
    if not cur: continue
    m = re.match(r'^\s+([0-9a-f]+):\t([0-9a-f ]+)\t(.*)$', line)
    if not m: continue
    r = res[cur]; a = int(m[1], 16); n = len(m[2].split()) * 2; r["end"] = max(r["end"], a + n); r["insns"] += 1; ins = m[3]
    if re.search(r'%(fp|sp)@\(-?\d', ins): r["stack_access"] += 1
    if rmw.search('\t' + ins): r["stack_rmw"] += 1
    if ins.startswith('moveml'): r["movem"] += 1
    if ins.startswith(('jsr', 'bsr')): r["calls"] += 1
    if ins.startswith('linkw') or ins.startswith('link'): r["link"] = ins
for k, r in res.items(): r["bytes"] = r["end"] - r["start"]; del r["end"]; r["start"] = hex(r["start"])
print(json.dumps(res, indent=1))
