#!/usr/bin/env python3
"""WAD を 68000 向けに再パックする。

Doom64KB は level/render データ(segs/sidedefs/nodes 等)を W_GetLumpByNum の戻り値で
WAD バイト配列へ直接 far 参照し、int16/int32 フィールドを読む。元 WAD には奇数 filepos の
lump が多数あり、Sega Genesis(68000) では非整列アクセスで address error になる。

各 lump の filepos を 4 バイト境界へ揃えて再パックし、ディレクトリを更新する。
出力 WAD を doom_iwad[] として doom64ng.h(aligned(4)) に焼き直す。

入力 : scripts/doom64.wad  (doom64ng.h から wad_from_header.py で抽出)
出力 : scripts/doom64_aligned.wad, src/doom64ng.h
"""
import struct, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "scripts", "doom64.wad")
WOUT = os.path.join(ROOT, "scripts", "doom64_aligned.wad")
HOUT = os.path.join(ROOT, "src", "doom64ng.h")
ALIGN = 4


# R34 isolated REJECT experiment: each 128/256B block is independently
# PackBits-RLE encoded. Do not change LINEDEFS/SEGS/NODES, which are hot ROM pointers.
def r34_packbits(raw):
    out=bytearray()
    i=0
    while i<len(raw):
        run=1
        while run<128 and i+run<len(raw) and raw[i+run]==raw[i]:
            run+=1
        if run>=3:
            out.extend((0x80 | (run-1),raw[i]))
            i+=run
            continue
        start=i
        i+=1
        while i<len(raw) and i-start<128:
            if i+2<len(raw) and raw[i]==raw[i+1]==raw[i+2]:
                break
            i+=1
        out.append(i-start-1)
        out+=raw[start:i]
    return bytes(out)

def r34_unpackbits(src,expected):
    out=bytearray()
    i=0
    while i<len(src):
        cmd=src[i]
        i+=1
        n=(cmd&127)+1
        if cmd&128:
            out.extend(bytes([src[i]])*n)
            i+=1
        else:
            out+=src[i:i+n]
            i+=n
    assert i==len(src) and len(out)==expected
    return bytes(out)

def r34_pack_reject(data,block_size):
    if not data:return data
    assert block_size in (128,256) and len(data)<65536
    pieces=[]
    for start in range(0,len(data),block_size):
        chunk=data[start:start+block_size]
        coded=r34_packbits(chunk)
        part=(b'\x01'+coded) if len(coded)<len(chunk) else (b'\x00'+chunk)
        pieces.append(part)
    n=len(pieces)
    pos=0
    offsets=[0]
    for piece in pieces:
        pos+=len(piece)
        if pos>65535:return data
        offsets.append(pos)
    header=b'RJ64'+struct.pack('>HH',len(data),n)
    table=b''.join(struct.pack('>H',o) for o in offsets)
    packed=header+table+b''.join(pieces)
    if len(packed)+4>=len(data):return data
    # Lossless proof includes all blocks, not just a hash comparison.
    for j,piece in enumerate(pieces):
        chunk=data[j*block_size:(j+1)*block_size]
        expanded=(piece[1:] if piece[0]==0 else
                  r34_unpackbits(piece[1:],len(chunk)))
        assert expanded==chunk
    assert len(packed)<len(data)
    return packed

def main():
    b = open(SRC, "rb").read()
    ident    = b[0:4]
    numlumps = struct.unpack_from('>h', b, 4)[0]
    infoofs  = struct.unpack_from('>i', b, 8)[0]

    lumps = []
    for i in range(numlumps):
        e = infoofs + i*16
        fp   = struct.unpack_from('>i', b, e)[0]
        sz   = struct.unpack_from('>H', b, e+4)[0]
        name = b[e+8:e+16]
        data = b[fp:fp+sz] if sz else b''
        # The R30 display uses independently packed 320x224 tile pictures.
        # Retain lump names/indices for Doom initialization, but do not
        # duplicate the old 240x160 raw bitmaps in the cartridge.
        if os.environ.get('DOOM_R30_NATIVE') == '1' and name.rstrip(b'\x00') in (
                b'TITLEPIC', b'WIMAP0', b'HELP2'):
            assert sz == 240*160, (name,sz)
            data = b''
            sz = 0
        if os.environ.get('DOOM_R34_REJECT')=='1' and name.rstrip(b'\x00')==b'REJECT' and sz:
            block_size=int(os.environ.get('DOOM_R34_REJECT_BLOCK','256'))
            compressed=r34_pack_reject(data,block_size)
            if compressed!=data:
                print(f'R34 REJECT: {sz} -> {len(compressed)} bytes, block={block_size}')
            data=compressed
            sz=len(data)
        lumps.append([name, sz, data])

    # 新 WAD を構築: ヘッダ(12) -> lump データ(4整列) -> ディレクトリ
    out = bytearray()
    out += ident
    out += struct.pack('>h', numlumps)
    out += struct.pack('>h', 0)
    out += struct.pack('>i', 0)   # infotableofs は後で埋める

    positions = []
    shared = {}
    dedup = os.environ.get("DOOM_WAD_DEDUP") == "1"
    for name, sz, data in lumps:
        if dedup and data in shared:
            positions.append(shared[data])
            continue
        while len(out) % ALIGN != 0:
            out += b'\x00'
        positions.append(len(out) if sz else 0)
        if dedup: shared[data] = positions[-1]
        out += data

    while len(out) % ALIGN != 0:
        out += b'\x00'
    infotableofs = len(out)
    for (name, sz, data), pos in zip(lumps, positions):
        out += struct.pack('>i', pos)
        out += struct.pack('>H', sz)
        out += struct.pack('>h', 0)
        out += name
    struct.pack_into('>i', out, 8, infotableofs)

    open(WOUT, "wb").write(out)

    # 整列検証
    bad = 0
    for (name, sz, data), pos in zip(lumps, positions):
        if sz and (pos % ALIGN):
            bad += 1
    print(f"repacked: {len(out)} bytes, lumps={numlumps}, misaligned={bad}, infoofs={infotableofs}")

    # doom64ng.h を生成（aligned(4)）
    with open(HOUT, "w") as f:
        f.write("// 自動生成 (scripts/repack_wad.py) — 68000 向けに 4 バイト整列した WAD を埋め込む。\n")
        section = ",section(\".rodata_binf\")" if os.environ.get("DOOM_R25_MUSIC") == "1" else ""
        f.write("static const unsigned char __attribute__((aligned(4)%s)) doom_iwad[%d] = {\n" % (section,len(out)))
        for i in range(0, len(out), 20):
            chunk = out[i:i+20]
            f.write("".join("0x%02x," % x for x in chunk) + "\n")
        f.write("};\n")
    print("wrote", HOUT)

if __name__ == "__main__":
    main()
