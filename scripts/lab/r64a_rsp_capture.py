#!/usr/bin/env python3
"""Read-only BlastEm GDB RSP snapshotter. No GDB binary or ROM changes required.
Reproducible R60 vs R64A framebuffer bytes at selected PERF renders, and R64D WRAM.
Max 10_000 emulated frames per individual BlastEm process. This is NOT a 2134-frame
complete timedemo; R64D counters here represent a prefix, not final totals.
"""
import argparse,hashlib,json,os,pathlib,selectors,shutil,subprocess,sys,time

FRAMES=(8,16,64,128,256)
PIXELS=3344
RSP_CHUNK=192
class RSP:
    def __init__(self,exe,rom,max_frames,timeout):
        self.timeout=timeout
        self.proc=subprocess.Popen([exe,"-b",str(max_frames),"-D",str(rom)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            env={**os.environ,"SDL_AUDIODRIVER":"dummy","SDL_VIDEODRIVER":"dummy"},
            bufsize=0,start_new_session=True)
        self.buf=bytearray()
        self.sel=selectors.DefaultSelector()
        self.sel.register(self.proc.stdout,selectors.EVENT_READ)
        self.started=time.monotonic()
    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:self.proc.wait(timeout=4)
            except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait(timeout=3)
        self.sel.close()
        self.proc.stdin.close()
        self.proc.stdout.close()
        # stderr is buffered by pipe: only read after process is no longer running.
        err=self.proc.stderr.read(2500)
        self.proc.stderr.close()
        if err: print("BLASTEM STDERR:",err.decode(errors="replace")[-1200:],file=sys.stderr)
    def send(self,command):
        b=command.encode("ascii")
        frame=b"$"+b+b"#"+f"{sum(b)&255:02x}".encode("ascii")
        self.proc.stdin.write(frame)
        self.proc.stdin.flush()
    def recv(self,timeout=None):
        deadline=time.monotonic()+(timeout if timeout is not None else self.timeout)
        while True:
            a=self.buf.find(b"$")
            if a>=0:
                if a:self.buf=self.buf[a:]
                h=self.buf.find(b"#",1)
                if h>=0 and len(self.buf)>=h+3:
                    body=bytes(self.buf[1:h]); tail=self.buf[h+1:h+3]
                    self.buf=self.buf[h+3:]
                    if (sum(body)&255)!=int(tail,16):
                        raise RuntimeError("RSP response checksum mismatch")
                    self.proc.stdin.write(b"+");self.proc.stdin.flush()
                    return body.decode("ascii",errors="replace")
            elif len(self.buf)>4096:self.buf.clear()
            remain=deadline-time.monotonic()
            if remain<=0:raise TimeoutError("BlastEm RSP reply timeout")
            if self.proc.poll() is not None:raise RuntimeError("BlastEm exited before RSP reply: "+str(self.proc.returncode))
            if not self.sel.select(timeout=min(remain,1)):continue
            data=os.read(self.proc.stdout.fileno(),32768)
            if not data:raise RuntimeError("BlastEm RSP EOF")
            self.buf.extend(data)
    def req(self,command,timeout=None):
        self.send(command)
        reply=self.recv(timeout)
        if len(reply)==3 and reply.startswith("E") and all(c in "0123456789abcdefABCDEF" for c in reply[1:]):\n            raise RuntimeError("RSP "+command+" -> "+reply)
        return reply
    def readmem(self,addr,size):
        out=bytearray()
        for off in range(0,size,RSP_CHUNK):
            n=min(size-off,RSP_CHUNK)
            h=self.req(f"m{addr+off:x},{n:x}")
            if len(h)!=2*n:
                raise RuntimeError(f"readmem {addr+off:06X} wanted {n} got {len(h)//2} bytes: {h[:80]}")
            out.extend(bytes.fromhex(h))
        return bytes(out)
    def cont(self):
        self.send("c")
        r=self.recv(timeout=self.timeout)
        if not (r.startswith("S") or r.startswith("T")):raise RuntimeError("RSP unexpected stop "+r)
        return r

def symbols(elf):
    nm=os.environ.get("M68K_NM") or str(pathlib.Path.home()/"mars/m68k-elf/bin/m68k-elf-nm")
    if not pathlib.Path(nm).is_file():nm=shutil.which("m68k-elf-nm") or nm
    p=subprocess.run([nm,str(elf)],check=True,capture_output=True,text=True)
    result={}
    for line in p.stdout.splitlines():
        parts=line.split()
        if len(parts)>=3:
            try:result[parts[-1]]=int(parts[0],16)
            except ValueError:pass
    # GCC commonly emits translation-unit-local statics with suffixes (.0, .123).
    for want in ("r22_fb", "bench_active", "r64d_ptr"):
        if want not in result:
            matching=[(k,v) for k,v in result.items()
                      if k==("_"+want) or k.startswith(want+".")]
            if len(matching)==1:
                result[want]=matching[0][1]
                print("SYMBOL ALIAS",want,matching[0][0],hex(matching[0][1]),flush=True)
    return result

def run(args):
    out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
    syms=symbols(args.elf)
    required=["I_FinishUpdate","r22_fb","_g_gametic"]
    if args.kind=="diag":required+=["r64d_ptr"]
    missing=[k for k in required if k not in syms]
    if missing:
        related=[k for k in syms if ("fb" in k.lower() or "r22" in k.lower() or "pixel" in k.lower())][:80]
        raise RuntimeError("ELF missing debug symbols: "+str(missing)+"; related="+str(related))
    print("SYMBOLS", {k:hex(syms[k]) for k in required},flush=True)
    g=RSP(args.blastem,args.rom,args.max_emulated_frames,args.timeout)
    records=[]
    try:
        welcome=g.req("qSupported")
        print("RSP",welcome,flush=True)
        assert g.req(f"Z0,{syms['I_FinishUpdate']:x},2")=="OK"
        # In PERF one visible frame may have multiple ticks? Index by game tic and
        # capture the first frame for each unique tic. Never compare wall-clock timing.
        seen=set()
        frame_hits=0
        for _ in range(args.max_breaks):
            g.cont()
            frame_hits+=1
            gametic=int.from_bytes(g.readmem(syms["_g_gametic"],4),"big")
            if not gametic or gametic in seen:continue
            seen.add(gametic)
            if args.kind=="frame" and gametic in FRAMES:
                fb=g.readmem(syms["r22_fb"]+4,PIXELS)
                fn=f"frame-gametic-{gametic:04d}.bin"
                (out/fn).write_bytes(fb)
                row={"gametic":gametic,"file":fn,"sha256":hashlib.sha256(fb).hexdigest(),
                     "bytes":len(fb),"frame_hit":frame_hits}
                records.append(row)
                print("SNAP",row,flush=True)
                if len(records)==len(FRAMES):break
            elif args.kind=="diag" and gametic>=args.diag_tic:
                rawaddr=int.from_bytes(g.readmem(syms["r64d_ptr"],4),"big")
                addr=rawaddr & 0xffffff  # Genesis 68000 exposes 24-bit physical addressing
                if not (0xff0000<=addr<0x1000000):
                    raise RuntimeError(f"R64D diagnostic pointer invalid: {rawaddr:08X} (phys {addr:06X})")
                block=g.readmem(addr,236)
                (out/"R64D-counter-block.bin").write_bytes(block)
                # Capture whole physical WRAM; Cláudio's r64d_read accepts this dump.
                wram=g.readmem(0xff0000,65536)
                (out/"WRAM_R64D_PARTIAL.bin").write_bytes(wram)
                row={"gametic":gametic,"counter_address":f"0x{addr:06X}","raw_pointer":f"0x{rawaddr:08X}",
                    "counter_sha256":hashlib.sha256(block).hexdigest(),
                    "wram_sha256":hashlib.sha256(wram).hexdigest(),
                    "wram_bytes":len(wram),"frame_hit":frame_hits,
                    "scope":"prefix until gametic, NOT full DEMO3"}
                records.append(row)
                print("DIAG",row,flush=True)
                break
        else:raise RuntimeError("max_breaks reached without all expected data")
        if not records:raise RuntimeError("No data captured; not a passing diagnostic")
        if args.kind=="frame" and len(records)!=len(FRAMES):raise RuntimeError("Missing snapshots")
    finally:
        g.close()
    result={"rom":args.rom,"elf":args.elf,"kind":args.kind,
            "max_emulated_frames":args.max_emulated_frames,
            "records":records,"notes":"Read-only RSP: emulator paused at I_FinishUpdate; not a hardware timing measurement"}
    (out/"CAPTURE.json").write_text(json.dumps(result,indent=2)+"\n")
    print("CAPTURE PASS",args.kind,len(records),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--rom",required=True)
    p.add_argument("--elf",required=True)
    p.add_argument("--blastem",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--kind",choices=["frame","diag"],required=True)
    p.add_argument("--diag-tic",type=int,default=128)
    p.add_argument("--max-emulated-frames",type=int,default=10000)
    p.add_argument("--max-breaks",type=int,default=1500)
    p.add_argument("--timeout",type=int,default=60)
    args=p.parse_args()
    if args.max_emulated_frames>10000 or args.max_emulated_frames<1:
        p.error("hard limit: 1..10000 frames per BlastEm invocation")
    run(args)
if __name__=="__main__":main()
