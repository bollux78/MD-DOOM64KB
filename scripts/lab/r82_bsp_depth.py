#!/usr/bin/env python3
"""R82: maximum BSP tree depth of every map in an IWAD (static, no emulator).

Depth = number of recursive R_RenderBSPNode frames on the deepest root-to-leaf path:
one per node plus the final call made with a subsector number (NF_SUBSECTOR, 0x8000).
usage: r82_bsp_depth.py WAD [--frame 48] [--out JSON]
"""
import argparse, json, re, struct, sys


def lumps(data):
    ident, n, ofs = struct.unpack_from("<4sii", data, 0)
    for i in range(n):
        p, sz, name = struct.unpack_from("<ii8s", data, ofs + 16 * i)
        yield name.rstrip(b"\0").decode("ascii", "replace"), data[p:p + sz]


def max_depth(nodes):
    n = len(nodes) // 28
    if n == 0:
        return 1
    best, stack = 0, [(n - 1, 1)]
    while stack:
        node, d = stack.pop()
        for child in struct.unpack_from("<hh", nodes, node * 28 + 24):
            if child & 0x8000 or child < 0:
                best = max(best, d + 1)
            else:
                stack.append((child, d + 1))
    return best


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("wad"); ap.add_argument("--frame", type=int, default=48); ap.add_argument("--out")
    a = ap.parse_args()
    data = open(a.wad, "rb").read()
    res, cur = {}, None
    for name, blob in lumps(data):
        if re.fullmatch(r"E\dM\d|MAP\d\d", name):
            cur = name
        elif name == "NODES" and cur:
            d = max_depth(blob)
            res[cur] = {"nodes": len(blob) // 28, "max_depth": d, "recursive_bsp_stack_bytes": d * a.frame}
    out = {"frame_bytes": a.frame, "maps": res, "worst": max(res.items(), key=lambda kv: kv[1]["max_depth"]) if res else None}
    s = json.dumps(out, indent=1)
    if a.out:
        open(a.out, "w").write(s + "\n")
    print(s)


if __name__ == "__main__":
    sys.exit(main())
