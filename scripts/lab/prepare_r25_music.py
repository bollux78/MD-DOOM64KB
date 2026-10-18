#!/usr/bin/env python3
"""Restore pinned offline ZGM payload; rescomp compiles VGM to classic XGM."""
from pathlib import Path
import base64,hashlib,json,os,struct
ROOT=Path(__file__).resolve().parents[2]

def decode(b):
    out=bytearray();p=0
    while True:
        flags=b[p];p+=1
        for bit in range(8):
            if flags&(1<<bit):
                distance=(b[p]<<8)|b[p+1];length=b[p+2]+1;p+=3
                if length==1:
                    assert p==len(b),'unexpected appended PCM data'
                    return bytes(out)
                assert distance<len(out) and distance<32768
                for _ in range(length):out.append(out[-distance-1])
            else:out.append(b[p]);p+=1

def validate(b):
    u=lambda p:struct.unpack_from('<I',b,p)[0]
    assert b[:4]==b'Vgm ' and u(4)+4==len(b)
    assert u(0x2c)==7670453 and u(0xc)==3579545
    p=0x34+u(0x34) if u(0x34) else 64;boundaries=set()
    while p<len(b):
        boundaries.add(p);op=b[p];p+=1
        if op==0x66:break
        if op in (0x50,0x4f):p+=1
        elif op in (0x52,0x53,0x61):p+=2
        elif op in (0x62,0x63) or 0x70<=op<=0x8f:pass
        else:raise ValueError(f'Unsupported command {op:02x}')
        assert p<=len(b)
    else:raise ValueError('No end command')
    assert 0x1c+u(0x1c) in boundaries
    g=0x14+u(0x14)
    assert b[g:g+4]==b'Gd3 ' and g+12+u(g+8)==len(b)

def restore():
    payload=json.loads((ROOT/'assets/r25-music.json').read_text())
    for t in payload['tracks']:
        packed=base64.b64decode(t['zgm'],validate=True)
        assert hashlib.sha256(packed).hexdigest()==t['sha256_zgm']
        raw=decode(packed);validate(raw)
        assert hashlib.sha256(raw).hexdigest()==t['sha256_vgm']
        (ROOT/'res'/('r25-'+t['name'].lower()+'.vgm')).write_bytes(raw)
    if os.environ.get('DOOM_R29_XGM2')=='1':
        if os.environ.get('DOOM_R27_SINGLE_TRACK')=='1':
            return 'XGM2 bgm_e1m1 "r25-e1m1.vgm"\nXGM2 bgm_silent "silent.vgm"\n'
        names=[f'r25-e1m{i}.vgm' for i in range(1,10)]+['r25-intro.vgm','r25-inter.vgm','r25-end.vgm','silent.vgm']
        if os.environ.get('DOOM_R29_MULTI')=='1':
            return 'XGM2 bgm_episode '+ ' '.join('"'+x+'"' for x in names)+'\n'
        ids=['bgm_e1m'+str(i) for i in range(1,10)]+['bgm_intro','bgm_inter','bgm_victor','bgm_silent']
        return ''.join('XGM2 '+ident+' "'+filename+'"\n' for ident,filename in zip(ids,names))
    if os.environ.get('DOOM_R27_SINGLE_TRACK')=='1':
        return 'XGM bgm_e1m1 "r25-e1m1.vgm"\nXGM bgm_silent "silent.vgm"\n'
    lines=[f'XGM bgm_e1m{i} "r25-e1m{i}.vgm"' for i in range(1,10)]
    lines += ['XGM bgm_intro "r25-intro.vgm"','XGM bgm_inter "r25-inter.vgm"',
              'XGM bgm_victor "r25-end.vgm"','XGM bgm_silent "silent.vgm"']
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    descriptor=restore() if os.environ.get('DOOM_R25_MUSIC')=='1' else 'XGM bgm_e1m1 "e1m1.vgm"\nXGM bgm_silent "silent.vgm"\n'
    (ROOT/'res/music.res').write_text(descriptor)
    print('R25 full soundtrack restored' if os.environ.get('DOOM_R25_MUSIC')=='1' else 'Legacy control music selected')
