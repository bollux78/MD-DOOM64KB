#!/usr/bin/env python3
"""Read a local Heretic IWAD; print map inventory. Never commit WAD assets."""
import argparse
import hashlib
import pathlib
import re
import struct

SIZES = {"THINGS": 10, "LINEDEFS": 14, "SIDEDEFS": 30, "VERTEXES": 4,
         "SEGS": 12, "SSECTORS": 4, "NODES": 28, "SECTORS": 26}

def inspect(wad):
    data = pathlib.Path(wad).read_bytes()
    magic, n, offset = struct.unpack_from("<4sII", data)
    if magic != b"IWAD" or offset + n*16 > len(data):
        raise ValueError("Not a valid IWAD")
    lumps = []
    for i in range(n):
        p, size, name = struct.unpack_from("<II8s", data, offset+i*16)
        name = name.rstrip(b"\x00").decode("ascii", "replace")
        if size and p+size > len(data):
            raise ValueError("Invalid lump bounds: "+name)
        lumps.append((name,p,size))
    print("sha256:", hashlib.sha256(data).hexdigest())
    print("bytes:", len(data), "lumps:", n)
    for i, (name,_,_) in enumerate(lumps):
        if not re.fullmatch(r"E[1-9]M[1-9]", name):
            continue
        parts = dict((k,(p,s)) for k,p,s in lumps[i+1:i+11])
        if not all(k in parts for k in SIZES):
            continue
        counts = {}
        for key, unit in SIZES.items():
            _, size = parts[key]
            if size % unit:
                raise ValueError(f"{name}/{key}: unexpected size {size}")
            counts[key] = size//unit
        p, size = parts["THINGS"]
        players = sum(struct.unpack_from("<h",data,p+j+6)[0] == 1 for j in range(0,size,10))
        print(f"{name}:", " ".join(f"{k}={v}" for k,v in counts.items()), f"P1={players}")
if __name__ == "__main__":
    a=argparse.ArgumentParser()
    a.add_argument("iwad",type=pathlib.Path)
    inspect(a.parse_args().iwad)
