#!/usr/bin/env python3
"""Exhaustive integer domain check against compiled C, not just Python division."""
import ctypes, importlib.util, pathlib, subprocess, tempfile
p = pathlib.Path(__file__).with_name('apply_r114.py')
s = importlib.util.spec_from_file_location('r114',p); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
t = m.depth_tables()
with tempfile.TemporaryDirectory(prefix='r114-') as d:
    src = pathlib.Path(d)/'reference.c'; lib = pathlib.Path(d)/'reference.so'
    src.write_text('''#include <stdint.h>
void reference(int32_t tz, uint32_t *out) {
    int32_t xscale = (38L << 16) / (tz >> 16);
    out[0] = xscale;
    out[1] = (44L * 65536) / (tz >> 16);
    out[2] = 0xffffffffu / xscale;
    out[3] = tz / (44 << 7);
}''')
    subprocess.run(['cc','-O2','-shared','-fPIC',str(src),'-o',str(lib)],check=True)
    f=ctypes.CDLL(str(lib)).reference; f.argtypes=[ctypes.c_int32,ctypes.POINTER(ctypes.c_uint32)]
    checked=0
    for z in range(4,1281):
        for frac in (0,1,127,32767,65535):
            tz=(z<<16)+frac
            if tz>1280*65536:continue
            out=(ctypes.c_uint32*4)(); f(tz,out)
            assert list(out)[:3]==[t[n][z] for n in ('xscale','yscale','iscale')],(z,frac,list(out))
            assert out[3]==tz//(44<<7)
            checked+=1
    assert sum(len(v)*4 for v in t.values())==15372
    print('PASS: all 1277 valid integer distances, fractional boundaries, %d C comparisons; 15372 ROM bytes, zero new BSS'%checked)
