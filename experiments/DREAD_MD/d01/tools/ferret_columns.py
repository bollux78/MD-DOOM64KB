"""Lossless per-column PackBits, including vertical wrap padding."""
def encode_column(data):
    if not 1 <= len(data) <= 512:raise ValueError('Ferret column exceeds 512 decoded bytes')
    out=bytearray(len(data).to_bytes(2,'big'));i=0
    while i<len(data):
        run=1
        while i+run<len(data) and run<128 and data[i+run]==data[i]:run+=1
        if run>=3:
            out.extend((127+run,data[i]));i+=run;continue
        begin=i;i+=run
        while i<len(data) and i-begin<128:
            n=1
            while i+n<len(data) and n<128 and data[i+n]==data[i]:n+=1
            if n>=3:break
            i+=min(n,128-(i-begin))
        out.append(i-begin-1);out.extend(data[begin:i])
    return bytes(out)

def decode_column(data):
    size=int.from_bytes(data[:2],'big');out=bytearray();i=2
    while len(out)<size:
        control=data[i];i+=1;n=(control&127)+1
        if control&128:out.extend([data[i]]*n);i+=1
        else:out.extend(data[i:i+n]);i+=n
    if len(out)!=size or i!=len(data):raise ValueError('Invalid column stream')
    return bytes(out)
