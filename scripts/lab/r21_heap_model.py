#!/usr/bin/env python3
"""SGDK cb114ac heap budget: boot, runtime allocations, result font.
This is a static model of the selected SDK configuration, not a runtime proof.
--flags infers S5, V2c and F1; --expect-hang permits only the named lab failure.
"""
import argparse, pathlib, struct, sys
STACK_SIZE = 0x0A00
MEMORY_HIGH = 0xE1000000 - STACK_SIZE
QUEUE = 80 * 16 + 2
FONT = 3072 + 8 + 2
DEFAULT_BUFFER = 8192 + 2
S5_QUEUE, S5_BUFFER = 32 * 16 + 2, 2048 + 2

def bend(elf):
    b = pathlib.Path(elf).read_bytes()
    if b[:6] != b'\x7fELF\x01\x02': raise ValueError('expected big-endian ELF32')
    shoff = struct.unpack_from('>I', b, 32)[0]
    shsize, shnum = struct.unpack_from('>HH', b, 46)
    sh = [struct.unpack_from('>10I', b, shoff+i*shsize) for i in range(shnum)]
    for h in sh:
        if h[1] != 2: continue
        st = sh[h[6]]; strings = b[st[4]:st[4]+st[5]]
        for off in range(h[4], h[4]+h[5], h[9]):
            name, value = struct.unpack_from('>II', b, off)
            if strings[name:].split(b'\0',1)[0] == b'_bend': return value
    raise ValueError('missing _bend: '+str(elf))

def model(end, s5=False, alloc=0, no_init=False):
    total = MEMORY_HIGH - ((end+1)&~1) - 2
    boot = total - QUEUE
    # DMA_init attempts the default data buffer and keeps it only if it fits.
    if boot >= DEFAULT_BUFFER: boot -= DEFAULT_BUFFER
    after = total-S5_QUEUE-S5_BUFFER if s5 else boot
    if alloc: after -= ((alloc+1)&~1)+2
    return dict(total=total, boot=boot, after=after,
                boot_margin=boot-FONT, end_margin=after-FONT,
                boot_fail=boot<FONT, end_fail=(not no_init and after<FONT))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf',nargs='+');p.add_argument('--flags',type=pathlib.Path)
    p.add_argument('--extra-static',type=int,default=0);p.add_argument('--alloc',type=int,default=0)
    p.add_argument('--s5',action='store_true');p.add_argument('--require-end-font',action='store_true')
    p.add_argument('--expect-hang',choices=['boot','end'])
    p.add_argument('--nm',help='compatibility only; symbols are parsed directly')
    a=p.parse_args(); flags=set(a.flags.read_text().split()) if a.flags else set()
    s5=a.s5 or '-DDOOM_R20_SGDK_HEAP' in flags
    alloc=a.alloc+(2128 if '-DDOOM_R21_V2_HEAPBUF' in flags else 0)
    no_init=bool(a.flags) and '-DDOOM_R21_NO_VDP_INIT' in flags
    failed=False
    for elf in a.elf:
        m=model(bend(elf)+a.extra_static,s5,alloc,no_init)
        end_fail=m['end_fail'] and (a.require_end_font or a.flags is not None)
        if a.expect_hang=='boot': ok=m['boot_fail']
        elif a.expect_hang=='end': ok=not m['boot_fail'] and end_fail
        else: ok=not m['boot_fail'] and not end_fail
        if m['after']<0: ok=False
        failed |= not ok
        verdict=('EXPECTED-'+a.expect_hang.upper()+'-HANG') if ok and a.expect_hang else ('PASS' if ok else 'REJECT')
        print(f"{pathlib.Path(elf).name}: total={m['total']} boot={m['boot']} after={m['after']} "
              f"font@boot={m['boot_margin']:+} font@end={m['end_margin']:+} "
              f"S5={int(s5)} alloc={alloc} F1={int(no_init)} {verdict}")
    return int(failed)
if __name__=='__main__':sys.exit(main())
