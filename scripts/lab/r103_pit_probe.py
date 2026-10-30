#!/usr/bin/env python3
"""R103: find the DEMO3 call where PIT_AddThingIntercepts receives an invalid mobj pointer.

Real hardware raises ADDRESS ERROR at PIT_AddThingIntercepts (thing = 0xBCFCFFFF, read of
thing->... at an odd address). BlastEm does not trap odd accesses, so the bad pointer may pass
silently there. Read-only probe: breakpoint at PIT_AddThingIntercepts entry, read the stacked
argument, flag anything that is not an even work-RAM address. The caller (P_PathTraverse) keeps
the block x/y in d4/d5 at the call through the SRAM head (see disassembly), so they are logged.
One BlastEm run, <= 10000 emulated frames (AGENTS.md).
"""
import argparse, importlib.util, json, pathlib, sys


def load_rsp():
    here = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("r64a_rsp_capture", here / "r64a_rsp_capture.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def sym(syms, name):
    if name in syms: return syms[name]
    m = [v for k, v in syms.items() if k.startswith(name + ".")]
    assert len(m) == 1, (name, m)
    return m[0]


def be(b): return int.from_bytes(b, "big")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blastem", required=True); ap.add_argument("--rom", required=True); ap.add_argument("--elf", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--label", default="")
    ap.add_argument("--max-emulated-frames", type=int, default=9800)
    ap.add_argument("--max-bad", type=int, default=8)
    ap.add_argument("--max-breaks", type=int, default=400000)
    ap.add_argument("--norender", type=int, default=1)
    ap.add_argument("--shadow", type=int, default=0, help="1=A2, 2=L3: Shadow On from the first tic")
    ap.add_argument("--render-from", type=int, default=0, help="with --norender 1: render again from this tic")
    a = ap.parse_args()
    assert 1 <= a.max_emulated_frames <= 10000
    rsp = load_rsp(); syms = rsp.symbols(a.elf)
    pit = sym(syms, "PIT_AddThingIntercepts") & 0xFFFFFF
    tic_a = sym(syms, "_g_gametic"); map_a = syms.get("_g_gamemap"); bw_a = syms.get("_g_bmapwidth")
    g = rsp.RSP(a.blastem, a.rom, a.max_emulated_frames, 600)
    res = {"label": a.label, "rom": a.rom, "pit": hex(pit), "calls": 0, "bad": [], "last_tic": 0}
    calls_per_tic = {}
    try:
        g.req("qSupported")
        diag = "R103_Bad" in syms
        if diag:
            # diag ROM: skip rendering (r103_norender=1) to reach late tics; stop at R103_Bad.
            badf = syms["R103_Bad"] & 0xFFFFFF; fin = sym(syms, "G_Ticker") & 0xFFFFFF  # one stop per game tic
            nr = syms["r103_norender"]; res["diag"] = True; armed = False
            assert g.req("Z0,%x,2" % badf) == "OK" and g.req("Z0,%x,2" % fin) == "OK"
            for _ in range(a.max_breaks):
                try:
                    g.cont()
                except (RuntimeError, TimeoutError) as e:
                    res["end"] = "emulator: %s" % e; break
                regs = g.req("g"); pc = int(regs[17 * 8:18 * 8], 16) & 0xFFFFFF; sp = int(regs[15 * 8:16 * 8], 16) & 0xFFFFFF
                tic = be(g.readmem(tic_a, 4))
                if pc == fin:
                    if armed is False and a.shadow:
                        on_a = sym(syms, "r92_shadow_on"); col_a = sym(syms, "r77_color_state")
                        assert g.req("M%x,1:01" % (on_a & 0xFFFFFF)) == "OK"
                        assert g.req("M%x,2:%02x01" % (col_a & 0xFFFFFF, a.shadow)) == "OK"
                        res["shadow_mode"] = a.shadow
                    if not armed and a.norender:
                        assert g.req("M%x,1:01" % (nr & 0xFFFFFF)) == "OK"; armed = True
                    elif armed is False:
                        armed = 0
                    if armed and a.render_from and tic >= a.render_from:
                        assert g.req("M%x,1:00" % (nr & 0xFFFFFF)) == "OK"; armed = None; res["render_from_tic"] = tic
                    if tic < res["last_tic"] - 5: res["end"] = "demo_restarted"; break
                    res["last_tic"] = max(res["last_tic"], tic); continue
                if pc == badf:
                    st = g.readmem(sp, 20)
                    bad = {"tic": tic, "gamemap": be(g.readmem(map_a, 2)) if map_a else None, "ret": hex(be(st[0:4])),
                           "thing": hex(be(st[4:8])), "cell": be(st[8:12]) & 0xFFFF, "head": hex(be(st[12:16])), "prev": hex(be(st[16:20]))}
                    pv = be(st[16:20]) & 0xFFFFFF
                    if pv: bad["prev_mobj_hex"] = g.readmem(pv, 0x50).hex()
                    res["bad"].append(bad); print(json.dumps(bad), flush=True); res["end"] = "r103_bad"; break
            res.setdefault("end", "max_breaks"); res["status"] = "ok"
            raise StopIteration
        assert g.req("Z0,%x,2" % pit) == "OK"
        for _ in range(a.max_breaks):
            try:
                g.cont()
            except (RuntimeError, TimeoutError) as e:
                res["end"] = "emulator: %s" % e; break
            regs = g.req("g")
            r = [int(regs[i * 8:(i + 1) * 8], 16) for i in range(18)]
            pc = r[17] & 0xFFFFFF
            if pc != pit: continue
            sp = r[15] & 0xFFFFFF
            ret, thing = be(g.readmem(sp, 4)), be(g.readmem(sp + 4, 4))
            res["calls"] += 1
            t24 = thing & 0xFFFFFF
            ok = (t24 & 1) == 0 and 0xFF0000 <= t24 <= 0xFFFFFF
            tic = be(g.readmem(tic_a, 4)); res["last_tic"] = tic
            calls_per_tic[tic] = calls_per_tic.get(tic, 0) + 1
            if not ok:
                bw = be(g.readmem(bw_a, 2)) if bw_a else None
                bx, by = r[4] & 0xFFFF, r[5] & 0xFFFF
                bad = {"tic": tic, "thing": hex(thing), "ret": hex(ret), "block_x": bx, "block_y": by,
                       "bmapwidth": bw, "block_index": (by * bw + bx) if bw else None,
                       "gamemap": be(g.readmem(map_a, 2)) if map_a else None,
                       "d": [hex(x) for x in r[0:8]], "a": [hex(x) for x in r[8:16]]}
                res["bad"].append(bad); print(json.dumps(bad), flush=True)
                if len(res["bad"]) >= a.max_bad: res["end"] = "max_bad"; break
        res.setdefault("end", "max_breaks")
        res["status"] = "ok"
    except StopIteration:
        pass
    except Exception as e:
        res["status"] = "error: %s" % e
    finally:
        g.close()
    res["tics_with_calls"] = len(calls_per_tic)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "bad"}), "bad:", len(res["bad"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
