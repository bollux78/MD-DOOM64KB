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
def rd(g, name, n=None):
    n = n or size.get(name, 4)
    v = int.from_bytes(g.readmem(sym[name], n), "big")
    return v - (1 << (8 * n)) if name == "_g_gamestate" and v >= 1 << (8 * n - 1) else v
g = RSP(os.environ["BLASTEM"], rom, 9500, 900)
res = {"label": label}
try:
    g.req("qSupported")
    assert g.req(f"Z0,{sym['I_FinishUpdate']:x},2") == "OK"
    frames = 0; start = None; hashes = {}
    while True:
        try:
            g.cont(); frames += 1
        except RuntimeError as e:
            print("N3 stopped early:", e, "frames", frames, "start", start, "last tic", locals().get("tic"), flush=True); raise
        gs, tic, vb = rd(g, "_g_gamestate"), rd(g, "_g_gametic"), rd(g, "_g_vblankCount")
        if gs == 0 and start is None and tic > 0: start = (frames, tic, vb)
        if start:
            k = frames - start[0]
            if k in (40, 80):
                fb = g.readmem(sym["r22_fb"] + 4, 3344)
                hashes[k] = (tic, hashlib.sha1(fb).hexdigest()[:12])
            if tic - start[1] >= int(os.environ.get("N3_TICS", "700")) or k >= 400: break
        if frames > 3000: break
    if start:
        res.update(frames=frames - start[0], tics=tic - start[1], seconds=round((vb - start[2]) / 60.0, 2))
        res["fps"] = round(res["frames"] / max(res["seconds"], 0.01), 2)
        res["fb_hash"] = hashes
    else:
        res["error"] = "never reached a level"
    if "n3" in sym:
        ptr = rd(g, "n3", 4)
        res["n3_ptr"] = hex(ptr)
        if ptr > 1:
            raw = g.readmem(ptr, 60)
            keys = ("active", "lock", "snap_pending", "have_frame", "ntics", "seq", "frames_sub", "frames_md", "desyncs",
                    "timeouts", "wait_vblanks", "exchanges", "sub_render_units", "sub_tic_units", "chk_gametic", "chk_x",
                    "chk_y", "chk_angle", "chk_valid", "prev_valid", "last_error", "pad")
            st = dict(zip(keys, struct.unpack(">BBBBHH8I4i4B", raw)))
            vf, vd, vm, vz, _vb, split, mx0, mx1, ef, rend, ss, wb, mr = struct.unpack(">4II3hBB3I", g.readmem(ptr + 60, 40))
            if vf: st.update(verify_frames=vf, verify_avg_diff=round(vd / max(vf, 1), 1), verify_max=vm, verify_identical=vz)
            if ss: st.update(split_now=split, split_avg=round(ss / max(st["frames_sub"], 1), 1), wait_b_vblanks=wb, md_render_vblanks=mr)
            if st["exchanges"]:
                st["sub_render_ms_per_exchange"] = round(st["sub_render_units"] * 0.03072 / st["exchanges"], 1)
                st["sub_tic_ms_per_exchange"] = round(st["sub_tic_units"] * 0.03072 / st["exchanges"], 1)
            res["n3"] = st
    for name in ("r59_color_mode", "r57_view"):
        if name in sym: res[name] = g.readmem(sym[name], max(1, size.get(name, 1))).hex()
    res["sub_sig"] = hex(int.from_bytes(g.readmem(0xA12020, 2), "big"))
    if res["sub_sig"] == "0xdead":
        res["sub_error"] = bytes(g.readmem(0x61F100, 40)).split(b"\0")[0].decode("latin1")
        res["sub_error_regs"] = g.readmem(0x61F0F8, 4).hex()
finally:
    g.close()
print("N3 RESULT", res, flush=True)
