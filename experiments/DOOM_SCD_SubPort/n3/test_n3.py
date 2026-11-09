"""N3 in BlastEm (Sega CD): autostart E1M1, player idle; count MD frames, how many came from the
sub, desyncs, and FPS over ~20 s of game time. Numbers only, no image leaves the runner."""
import hashlib, os, struct, subprocess, sys
from pathlib import Path
from r64a_rsp_capture import RSP

rom, elf, label = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
nm = Path.home() / "mars/m68k-elf/bin/m68k-elf-nm"
sym, size = {}, {}
for line in subprocess.check_output([nm, "-S", elf], text=True).splitlines():
    f = line.split()
    if len(f) == 4: sym[f[3].split(".")[0]] = int(f[0], 16) & 0xffffff; size[f[3].split(".")[0]] = int(f[1], 16)
    elif len(f) == 3: sym.setdefault(f[2].split(".")[0], int(f[0], 16) & 0xffffff)
SCRIPT = [(10, 50, (4,)), (50, 70, (4, 6)), (70, 90, (1,)), (90, 110, (7,)), (110, 150, (4, 1)), (150, 170, (6,))]
def keys(g, pressed):
    if "gamekeydown" not in sym: return
    n = size.get("gamekeydown", 12); el = n // 12 if n >= 12 else 1
    data = bytearray(n)
    for k in pressed: data[k * el + el - 1] = 1
    assert g.req("M%x,%x:%s" % (sym["gamekeydown"], n, data.hex())) == "OK"
def rd(g, name, n=None):
    n = n or size.get(name, 4)
    v = int.from_bytes(g.readmem(sym[name], n), "big")
    return v - (1 << (8 * n)) if name == "_g_gamestate" and v >= 1 << (8 * n - 1) else v
g = RSP(os.environ["BLASTEM"], rom, 9500, 900)
res = {"label": label}
try:
    g.req("qSupported")
    trace_tic = int(os.environ.get("N3_TRACE_TIC", "-1"))
    if trace_tic >= 0:
        # MD P_Random callers during one tic (return address at (SP) on entry)
        funcs = sorted((a, n) for n, a in sym.items())
        import bisect
        def fname(a):
            i = bisect.bisect_right([f[0] for f in funcs], a) - 1
            return "%s+0x%x" % (funcs[i][1], a - funcs[i][0]) if i >= 0 else hex(a)
        assert g.req(f"Z0,{sym['G_Ticker']:x},2") == "OK"
        callers = []; tracing = False
        for _ in range(200000):
            g.cont()
            regs = g.req("g")
            pc = int(regs[17 * 8:18 * 8], 16) & 0xffffff
            if pc == sym["G_Ticker"]:
                tic = rd(g, "_g_gametic")
                if tracing: break
                if tic == trace_tic:
                    tracing = True
                    assert g.req(f"Z0,{sym['P_Random']:x},2") == "OK"
                continue
            if pc == sym["P_Random"]:
                sp = int(regs[15 * 8:16 * 8], 16) & 0xffffff
                ra = int.from_bytes(g.readmem(sp, 4), "big") & 0xffffff
                callers.append(fname(ra))
        print("N3 TRACE tic %d: %d P_Random calls:" % (trace_tic, len(callers)), callers, flush=True)
        g.close(); raise SystemExit(0)
    assert g.req(f"Z0,{sym['I_FinishUpdate']:x},2") == "OK"
    frames = 0; start = None; hashes = {}
    while True:
        try:
            g.cont(); frames += 1
        except RuntimeError as e:
            print("N3 stopped early:", e, "frames", frames, "start", start, "last tic", locals().get("tic"), flush=True)
            res["partial"] = True
            break
        gs, tic, vb = rd(g, "_g_gamestate"), rd(g, "_g_gametic"), rd(g, "_g_vblankCount")
        last = (frames, tic, vb)
        if gs == 0 and start is None and tic > 0: start = (frames, tic, vb)
        if start and gs != 0:
            res["left_level_at_tic"] = tic; break
        if start:
            k = frames - start[0]
            if os.environ.get("N3_MOVE"):
                cur = next((p for a, b2, p in SCRIPT if a <= k < b2), ())
                if k < 175: keys(g, cur)
            if k in (40, 80):
                fb = g.readmem(sym["r22_fb"] + 4, 3344)
                hashes[k] = (tic, hashlib.sha1(fb).hexdigest()[:12])
            if tic - start[1] >= int(os.environ.get("N3_TICS", "700")) or k >= 400: break
        if frames > int(os.environ.get("N3_MAXFRAMES", "3000")): break
    if start:
        frames_, tic, vb = last
        res.update(frames=frames_ - start[0], tics=tic - start[1], seconds=round((vb - start[2]) / 60.0, 2))
        res["fps"] = round(res["frames"] / max(res["seconds"], 0.01), 2)
        res["fb_hash"] = hashes
    else:
        res["error"] = "never reached a level"
    if res.get("partial"):
        pass
    elif "n3" in sym:
        ptr = rd(g, "n3", 4)
        res["n3_ptr"] = hex(ptr)
        if ptr > 1:
            tn = int.from_bytes(g.readmem(ptr, 4), "big")
            if tn:
                funcs = sorted((a, n) for n, a in sym.items())
                import bisect
                keys_ = [f[0] for f in funcs]
                def fname(a):
                    i = bisect.bisect_right(keys_, a) - 1
                    return "%s+0x%x" % (funcs[i][1], a - funcs[i][0]) if i >= 0 else hex(a)
                tr = struct.unpack(">24I", g.readmem(ptr + 4, 96))
                res["md_rnd_trace"] = (tn, [fname(a & 0xffffff) for a in tr[:min(tn, 24)]])
            ptr += 100
            raw = g.readmem(ptr, 60)
            keys = ("active", "lock", "snap_pending", "have_frame", "ntics", "seq", "frames_sub", "frames_md", "desyncs",
                    "timeouts", "wait_vblanks", "exchanges", "sub_render_units", "sub_tic_units", "chk_gametic", "chk_x",
                    "chk_y", "chk_angle", "chk_valid", "prev_valid", "last_error", "pad")
            st = dict(zip(keys, struct.unpack(">BBBBHH8I4i4B", raw)))
            vf, vd, vm, vz, _vb, split, mx0, mx1, ef, rend, ss, wb, mr = struct.unpack(">4II3hBB3I", g.readmem(ptr + 60, 40))
            if vf: st.update(verify_frames=vf, verify_avg_diff=round(vd / max(vf, 1), 1), verify_max=vm, verify_identical=vz)
            dd = struct.unpack(">6i4H", g.readmem(ptr + 100 + 4 + 4 + 4, 32))
            if st["desyncs"]: st["first_desync_md_vs_sub"] = dd
            if ss: st.update(split_now=split, split_avg=round(ss / max(st["frames_sub"], 1), 1), wait_b_vblanks=wb, md_render_vblanks=mr)
            if st["exchanges"]:
                st["sub_render_ms_per_exchange"] = round(st["sub_render_units"] * 0.03072 / st["exchanges"], 1)
                st["sub_tic_ms_per_exchange"] = round(st["sub_tic_units"] * 0.03072 / st["exchanges"], 1)
            res["n3"] = st
    if res.get("partial"): raise SystemExit(print("N3 RESULT", res, flush=True))
    res["gamemap"] = rd(g, "_g_gamemap", 2); res["demoplayback"] = rd(g, "_g_demoplayback", size.get("_g_demoplayback", 1))
    for name in ("r59_color_mode", "r57_view"):
        if name in sym: res[name] = g.readmem(sym[name], max(1, size.get(name, 1))).hex()
    res["sub_sig"] = hex(int.from_bytes(g.readmem(0xA12020, 2), "big"))
    res["boot_diag"] = g.readmem(0x61F0F0, 8).hex()
    if res["sub_sig"] == "0xdead":
        res["sub_error"] = bytes(g.readmem(0x61F100, 40)).split(b"\0")[0].decode("latin1")
        res["sub_error_regs"] = g.readmem(0xA12026, 4).hex()
        res["sub_error_addr"] = g.readmem(0xA1202A, 4).hex()
        regs = int(res["sub_error_regs"], 16)
        subelf = elf.parent / "sub" / "n3-sub.elf"
        if subelf.exists() and regs:
            addr = regs & (0x0FFFFFFF if (regs >> 28) == 0xE else 0xFFFF)
            if (regs >> 28) != 0xE: addr = 0   # exception: high word of PC + vector, not mappable
            best = None
            for line in subprocess.check_output([nm, subelf], text=True).splitlines():
                f = line.split()
                if len(f) == 3 and f[1] in "Tt" and int(f[0], 16) <= addr and (best is None or int(f[0], 16) > best[0]): best = (int(f[0], 16), f[2])
            res["sub_error_caller"] = (hex(addr), best[1] if best else None)
        if subelf.exists() and os.environ.get("N3_TRACE_TIC"):
            subsyms = sorted((int(f.split()[0], 16), f.split()[2]) for f in subprocess.check_output([nm, subelf], text=True).splitlines() if len(f.split()) == 3 and f.split()[1] in "Tt")
            import bisect
            ks = [a for a, _ in subsyms]
            def sname(a):
                i = bisect.bisect_right(ks, a) - 1
                return "%s+0x%x" % (subsyms[i][1], a - subsyms[i][0]) if i >= 0 else hex(a)
            parts = res["sub_error"].split()
            try: res["sub_rnd_trace"] = (parts[0], [sname(int(x, 16)) for x in parts[1:]])
            except Exception: pass
finally:
    g.close()
print("N3 RESULT", res, flush=True)
