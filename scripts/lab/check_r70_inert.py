#!/usr/bin/env python3
"""Prove that WITHOUT -DDOOM_R70A_INVARIANTS the patched src/r_draw.c equals the base (R66): resolve every
conditional on the R70-A flags as 'undefined', normalise whitespace and compare.
R70-A1 needs no source change (it only enables the existing DOOM_R21_SEGLOOP_LOCALS).
Usage: check_r70_inert.py BASE_DIR PATCHED_DIR"""
import re, sys
from pathlib import Path

FILES = ["src/r_draw.c"]
A = re.compile(r"DOOM_R70A_[A-Z_]+")


def resolve(text):
    out, stack = [], []          # frame: [special, taken, active_here, converted]
    def live(): return all(f[2] for f in stack)
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"#\s*(if|ifdef|ifndef|elif|else|endif)\b(.*)", s)
        if not m:
            if live(): out.append(line)
            continue
        d, rest = m.group(1), m.group(2).strip()
        if d in ("if", "ifdef", "ifndef"):
            if A.search(rest):
                if "&&" in rest or "||" in rest:
                    sys.exit("unsupported compound condition on R70A flag: %s" % s)
                neg = rest.startswith("!") or d == "ifndef"
                val = True if neg else False
                stack.append([True, val, val, False])
            else:
                stack.append([False, True, True, False])
                if live(): out.append(line)
        elif d == "elif":
            f = stack[-1]
            if f[0]:
                if f[1]: f[2] = False
                else:
                    f[1], f[2], f[3] = True, True, True
                    if live(): out.append("#if" + line.strip()[len("#elif"):])
            elif live(): out.append(line)
        elif d == "else":
            f = stack[-1]
            if f[0]: f[2] = not f[1]; f[1] = True
            elif live(): out.append(line)
        else:
            f = stack.pop()
            if (not f[0]) or f[3]:
                if live(): out.append(line)
    assert not stack, "unbalanced conditionals"
    return "\n".join(out)


def norm(t):
    return [l for l in (re.sub(r"[ 	]+", " ", x).strip() for x in t.splitlines()) if l]


def main(a, b):
    ok = True
    for f in FILES:
        x = norm(Path(a, f).read_text()); y = norm(resolve(Path(b, f).read_text()))
        same = x == y; ok &= same
        print(("IDENTICAL " if same else "DIFFERS   ") + f + "  (R70A undefined)")
        if not same:
            import difflib
            print("\n".join(list(difflib.unified_diff(x, y, lineterm=""))[:40]))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
