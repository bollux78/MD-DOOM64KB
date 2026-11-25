"""Small lossless byte LZ packets for a PVS row (decoded in existing row arena)."""
def encode(raw):
    out=bytearray([2]);literal=bytearray();i=0
    def flush():
        while literal:
            count=min(128,len(literal));out.append(count-1);out.extend(literal[:count]);del literal[:count]
    while i<len(raw):
        best=distance=0
        for d in range(1,min(i,255)+1):
            n=0
            while n<130 and i+n<len(raw) and raw[i+n]==raw[i+n-d]:n+=1
            if n>best:best,distance=n,d
        if best>=3:
            flush();out.extend((128|(best-3),distance));i+=best
        else:literal.append(raw[i]);i+=1
    flush();return bytes(out)

def decode(data,size):
    assert data[0]==2;out=bytearray();i=1
    while len(out)<size:
        packet=data[i];i+=1
        if packet&128:
            n=(packet&127)+3;distance=data[i];i+=1
            for _ in range(n):out.append(out[-distance])
        else:
            n=packet+1;out.extend(data[i:i+n]);i+=n
    assert len(out)==size and i==len(data)
    return bytes(out)

def encode_group(raw):
    # 16-bit distances permit sharing patterns across adjacent PVS rows.
    out=bytearray();literal=bytearray();i=0;positions={}
    def flush():
        while literal:
            n=min(128,len(literal));out.append(n-1);out.extend(literal[:n]);del literal[:n]
    while i<len(raw):
        best=distance=0;key=raw[i:i+3]
        for at in reversed(positions.get(key,[])):
            d=i-at;n=0
            while n<130 and i+n<len(raw) and raw[i+n]==raw[i+n-d]:n+=1
            if n>best:best,distance=n,d
            if best==130:break
        n=best if best>=4 else 1
        if best>=4:
            flush();out.extend((128|(best-3),distance>>8,distance&255))
        else:literal.append(raw[i])
        for at in range(i,i+n):positions.setdefault(raw[at:at+3],[]).append(at)
        i+=n
    flush();return bytes([3])+len(raw).to_bytes(2,'big')+out

def decode_group(data):
    assert data[0]==3;size=int.from_bytes(data[1:3],'big');out=bytearray();i=3
    while len(out)<size:
        packet=data[i];i+=1
        if packet&128:
            n=(packet&127)+3;distance=(data[i]<<8)|data[i+1];i+=2
            for _ in range(n):out.append(out[-distance])
        else:n=packet+1;out.extend(data[i:i+n]);i+=n
    assert len(out)==size and i==len(data)
    return bytes(out)
