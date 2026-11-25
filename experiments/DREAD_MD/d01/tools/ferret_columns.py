"""Lossless per-column PackBits, including vertical wrap padding."""
def _encode_runs(data):
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

def encode_column(data):
    runs=_encode_runs(data)
    palette=bytes(sorted(set(data)));bits=max(1,(len(palette)-1).bit_length())
    lookup={v:i for i,v in enumerate(palette)};stream=bytearray();acc=0;have=0
    for value in data:
        acc=(acc<<bits)|lookup[value];have+=bits
        while have>=8:
            have-=8;stream.append((acc>>have)&255)
    if have:stream.append((acc<<(8-have))&255)
    dictionary=(len(data)|32768).to_bytes(2,'big')+bytes([len(palette)&255])+palette+stream
    return min([runs,dictionary],key=len)

def decode_column(data):
    header=int.from_bytes(data[:2],'big');size=header&32767;out=bytearray();i=2
    if header&32768:
        count=data[i] or 256;i+=1;palette=data[i:i+count];i+=count
        bits=max(1,(count-1).bit_length());mask=(1<<bits)-1;acc=have=0
        while len(out)<size:
            if have<bits:acc=(acc<<8)|data[i];have+=8;i+=1
            have-=bits;out.append(palette[(acc>>have)&mask])
        if i!=len(data):raise ValueError('Invalid dictionary column')
        return bytes(out)
    while len(out)<size:
        control=data[i];i+=1;n=(control&127)+1
        if control&128:out.extend([data[i]]*n);i+=1
        else:out.extend(data[i:i+n]);i+=n
    if len(out)!=size or i!=len(data):raise ValueError('Invalid column stream')
    return bytes(out)
