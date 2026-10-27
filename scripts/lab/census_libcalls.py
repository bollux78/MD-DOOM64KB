#!/usr/bin/env python3
"""R71 diagnostic: census of 32-bit libgcc arithmetic calls per function in a linked ELF.

Read-only: disassembles with m68k-elf-objdump and counts call sites of __mulsi3, __divsi3,
__udivsi3, __modsi3, __umodsi3 (and friends) per function, next to the native 16-bit
mul/div instructions. Does not change any build output.
usage: census_libcalls.py OBJDUMP ELF OUT_TXT
"""
import re, subprocess, sys
from collections import defaultdict
from pathlib import Path

LIB = ('__mulsi3', '__divsi3', '__udivsi3', '__modsi3', '__umodsi3', '__mulsidi3', '__divdi3', '__udivdi3')
HOT = re.compile(r'^(R42_|R60_|R64|R_|R22_|R47_|I_FinishUpdate|HUDW_|P_|V_|D_)')
FUNC = re.compile(r'^[0-9a-f]+ <([^>]+)>:$')
CALL = re.compile(r'\b(?:jsr|bsr(?:\.[bwl])?|jmp|bra(?:\.[bwl])?)\b.*<(' + '|'.join(LIB) + r')(?:\+0x[0-9a-f]+)?>')
NATIVE = re.compile(r'\t(muls\.w|mulu\.w|divs\.w|divu\.w|muls\.l|mulu\.l|divs\.l|divu\.l)\b')


def main():
    objdump, elf, out = sys.argv[1:4]
    text = subprocess.run([objdump, '-d', '--no-show-raw-insn', elf], check=True, capture_output=True, text=True).stdout
    calls = defaultdict(lambda: defaultdict(int))
    native = defaultdict(lambda: defaultdict(int))
    cur = None
    for line in text.splitlines():
        m = FUNC.match(line)
        if m:
            cur = m.group(1)
            continue
        if cur is None:
            continue
        c = CALL.search(line)
        if c:
            calls[cur][c.group(1)] += 1
        n = NATIVE.search(line)
        if n:
            native[cur][n.group(1)] += 1
    rows = sorted(calls.items(), key=lambda kv: -sum(kv[1].values()))
    lines = [f'# libgcc call-site census for {Path(elf).name}', '# function | hot-prefix | total | per-helper | native mul/div in same function']
    total = defaultdict(int)
    for fn, d in rows:
        for k, v in d.items():
            total[k] += v
        per = ' '.join(f'{k}={v}' for k, v in sorted(d.items()))
        nat = ' '.join(f'{k}={v}' for k, v in sorted(native.get(fn, {}).items())) or '-'
        lines.append(f'{fn} | {"HOT" if HOT.match(fn) else "-"} | {sum(d.values())} | {per} | {nat}')
    lines.append('')
    lines.append('# totals: ' + (' '.join(f'{k}={v}' for k, v in sorted(total.items())) or 'none'))
    lines.append('# functions with libgcc calls: %d (HOT-prefix: %d)' % (len(rows), sum(1 for fn, _ in rows if HOT.match(fn))))
    nat_tot = defaultdict(int)
    for d in native.values():
        for k, v in d.items():
            nat_tot[k] += v
    lines.append('# native totals: ' + (' '.join(f'{k}={v}' for k, v in sorted(nat_tot.items())) or 'none'))
    Path(out).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[-4:]))


if __name__ == '__main__':
    main()
