#!/usr/bin/env python3
"""Verify SRAM fallback, gameplay and timing using the instrumented GPGX core.

The companion results describe the instrumentation patch. It exposes
retro_sram_block (0=16-bit, 1=absent, 2=odd-byte SRAM), cartridge counters,
and VDP register/DMA event arrays. ELF symbols are used only for local tests.
"""
from pathlib import Path
import argparse, sys, ctypes as C, subprocess, json, hashlib
import numpy as np
from PIL import Image

class GameInfo(C.Structure):
    _fields_ = [("path", C.c_char_p), ("data", C.c_void_p),
                ("size", C.c_size_t), ("meta", C.c_char_p)]


ENV = C.CFUNCTYPE(C.c_bool, C.c_uint, C.c_void_p)
VIDEO = C.CFUNCTYPE(None, C.c_void_p, C.c_uint, C.c_uint, C.c_size_t)
AUDIO = C.CFUNCTYPE(None, C.c_int16, C.c_int16)
BATCH = C.CFUNCTYPE(C.c_size_t, C.c_void_p, C.c_size_t)
POLL = C.CFUNCTYPE(None)
INPUT = C.CFUNCTYPE(C.c_int16, C.c_uint, C.c_uint, C.c_uint, C.c_uint)


class Emulator:
    def __init__(self, core, rom):
        self.pad = set()
        self.pixel_format = 0
        self.capture = False
        self.screen = None
        self.core = C.CDLL(str(core.resolve()))
        callbacks = (
            ("environment", ENV, self.environment),
            ("video_refresh", VIDEO, self.video),
            ("audio_sample", AUDIO, lambda left, right: None),
            ("audio_sample_batch", BATCH, lambda data, frames: frames),
            ("input_poll", POLL, lambda: None),
            ("input_state", INPUT, lambda port, device, index, button:
             int(port == 0 and device == 1 and button in self.pad)),
        )
        self.callbacks = []
        for name, cb_type, fn in callbacks:
            cb = cb_type(fn)
            self.callbacks.append(cb)
            getattr(self.core, "retro_set_" + name)(cb)
        self.core.retro_init()
        self.core.retro_load_game.argtypes = [C.POINTER(GameInfo)]
        self.core.retro_load_game.restype = C.c_bool
        self.rom_bytes = C.create_string_buffer(rom.read_bytes())
        game = GameInfo(str(rom.resolve()).encode(), C.cast(self.rom_bytes, C.c_void_p),
                        C.sizeof(self.rom_bytes) - 1, None)
        if not self.core.retro_load_game(C.byref(game)):
            raise RuntimeError(f"Could not load {rom}")
        if self.core.retro_get_region() != 0:
            raise RuntimeError("Expected NTSC")
        self.core.retro_set_controller_port_device(0, 1)
        self.core.retro_get_memory_data.restype = C.c_void_p
        self.core.retro_get_memory_size.restype = C.c_size_t
        if self.core.retro_get_memory_size(2) != 65536:
            raise RuntimeError("Expected 64 KiB of Mega Drive work RAM")
        self.ram = self.core.retro_get_memory_data(2)
        if not self.ram:
            raise RuntimeError("Missing work RAM pointer")

    def environment(self, command, data):
        if command == 10:  # RETRO_ENVIRONMENT_SET_PIXEL_FORMAT
            self.pixel_format = C.cast(data, C.POINTER(C.c_int))[0]
            return self.pixel_format in (0, 1, 2)
        if command == 3:  # RETRO_ENVIRONMENT_GET_CAN_DUPE
            C.cast(data, C.POINTER(C.c_bool))[0] = True
            return True
        return False

    def video(self, data, width, height, pitch):
        if self.capture and data:
            self.screen = (C.string_at(data, height * pitch), width, height, pitch,
                           self.pixel_format)

    def step(self, count, button=None, capture=False):
        self.pad = {button} if button is not None else set()
        self.capture = capture
        for _ in range(count):
            self.core.retro_run()
        self.capture = False

    def screenshot(self):
        raw, width, height, pitch, fmt = self.screen
        dtype = np.uint32 if fmt == 1 else np.uint16
        pixels = np.frombuffer(raw, dtype=dtype).reshape(height, pitch // np.dtype(dtype).itemsize)
        pixels = pixels[:, :width].astype(np.uint32)
        if fmt == 1:
            channels = ((pixels >> 16) & 255, (pixels >> 8) & 255, pixels & 255)
        elif fmt == 2:
            channels = ((pixels >> 11) * 255 // 31, ((pixels >> 5) & 63) * 255 // 63,
                        (pixels & 31) * 255 // 31)
        else:
            channels = (((pixels >> 10) & 31) * 255 // 31, ((pixels >> 5) & 31) * 255 // 31,
                        (pixels & 31) * 255 // 31)
        return Image.fromarray(np.stack(channels, axis=2).astype(np.uint8))


    def close(self):
        self.core.retro_unload_game()
        self.core.retro_deinit()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--core", type=Path, required=True)
parser.add_argument("--builds", type=Path, required=True)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--nm", default="m68k-elf-nm")
parser.add_argument("--scenario", choices=("bench", "fixed", "turn", "smoke"), default="bench")
args = parser.parse_args()
root, core, nm = args.builds, args.core, args.nm
args.out.mkdir(parents=True, exist_ok=True)
shots = args.out / "shots"
shots.mkdir(exist_ok=True)

def test(config,condition,scenario='bench',idx=0):
    folder=root/config
    syms={}
    for row in subprocess.check_output([nm,'-S',folder/'EPISODE.elf'],text=True).splitlines():
        cols=row.split()
        if len(cols)==4: syms[cols[3]]=(int(cols[0],16)&65535,int(cols[1],16))
    e=Emulator(core,folder/'EPISODE.bin')
    block=C.c_uint.in_dll(e.core,'retro_sram_block')
    block.value=condition
    trace=C.c_uint.in_dll(e.core,'retro_trace_active')
    counts=(C.c_ulonglong*4).in_dll(e.core,'retro_sram_counts')
    txcount=C.c_uint.in_dll(e.core,'retro_trace_dmas')
    regcount=C.c_uint.in_dll(e.core,'retro_trace_regs')
    regs=np.ctypeslib.as_array((C.c_uint*(16384*4)).in_dll(e.core,'retro_trace_reg')).reshape(-1,4)
    tx=np.ctypeslib.as_array((C.c_uint*(32768*6)).in_dll(e.core,'retro_trace_dma')).reshape(-1,6)
    def raw(name,size=2):
        b=C.string_at(e.ram+syms[name][0],size)
        return b''.join(b[i:i+2][::-1] for i in range(0,size,2))
    def rd(name,size=2):return int.from_bytes(raw(name,size),'big')
    def put(name,value,size=2):
        b=value.to_bytes(size,'big')
        C.memmove(e.ram+syms[name][0],b''.join(b[i:i+2][::-1] for i in range(0,size,2)),size)
    def press(button,n=5,after=5):
        e.step(n,button);e.step(after,capture=True)
    key=f'{config}-{condition}-{scenario}-{idx}'
    try:
        assert e.core.retro_trace_hardware()==0x80
        e.step(80,capture=True)
        if condition==0 and scenario=='bench':e.screenshot().save(shots/(config+'-title.png'))
        assert rd('sram_kind')==[16,0,8][condition],(key,rd('sram_kind'))
        active=condition==0 and not config.startswith('control')
        assert bool(rd('sram_active'))==active
        if scenario=='bench':
            press(0)
            assert rd('bench_req')==1
            for _ in range(140):
                e.step(80)
                if rd('bench_done')>=1:break
            assert rd('bench_done')>=1,key
            result=dict(key=key,frames=rd('bench_frames',4),vblanks=rd('bench_vints',4))
            assert result['frames']==312,result
            result['fps']=result['frames']*60/result['vblanks']
            e.step(20,capture=True)
        else:
            press(3)
            if idx:
                press(5);press(8)
                for _ in range(idx):press(5)
                if condition==0 and idx==2:e.screenshot().save(shots/(config+'-levels.png'))
                press(3,5,130)
            else:press(3,5,130)
            assert rd('selected_map')==idx
            assert rd('nbuf')==(2 if active or not config.endswith('columns') else 1),(key,rd('nbuf'))
            if scenario=='fixed':
                put('bench_req',3)   # disables actors without taking over input
                put('bench_done',3)
                put('fcap',0)
                stable=raw('view',12)
            else:
                # Switch the game limiter to LIVRE through the pause menu.
                press(3,22,10)
                for _ in range(4):press(5)
                for _ in range(2):press(6)
                assert rd('fcap')==0
                press(3,22,20)
            txcount.value=regcount.value=0
            counts[:]=(0,)*4
            trace.value=1
            e.step(300,6 if scenario=='turn' else None,capture=True)
            trace.value=0
            result=dict(key=key)
            times=regs[:regcount.value,0].astype(np.int64)
            if len(times)>1:result.update(frames=len(times)-1,vblanks=int(times[-1]-times[0]),fps=float(60*(len(times)-1)/(times[-1]-times[0])))
            result['sram_counts']=list(counts)
            result['sram_dma_words']=int(sum(int(length) for _,_,src,_,length,_ in tx[:txcount.value] if 0x200000<=src<0x210000))
            assert (result['sram_dma_words']>0)==active,result
            if not active:assert sum(counts)==0,result
            if scenario=='fixed':
                assert raw('view',12)==stable,key
                result['viewport_sha256']=hashlib.sha256(np.asarray(e.screenshot())[16:160].tobytes()).hexdigest()
            # Verify return from pause, a video mode switch, and a pistol shot.
            if scenario=='smoke':
                press(3,22,10)
                press(5);press(7)
                press(3,22,20)
                press(1,70,20)
        result['nbuf']=rd('nbuf')
        result['kind']=rd('sram_kind')
        result['active']=rd('sram_active')
        e.screenshot().save(shots/(key+'.png'))
        print(json.dumps(result),flush=True)
        return result
    finally:e.close()

if __name__=='__main__':
    scenario=args.scenario
    results=[]
    for config in ['control-lines','auto-lines','control-columns','auto-columns']:
        for condition in [0,1,2]:
            for idx in ([0,1,2] if scenario=='smoke' else [1] if scenario=='turn' else [0]):
                results.append(test(config,condition,scenario,idx))
    (args.out/(scenario+'.json')).write_text(json.dumps(results,indent=2)+'\n')
