import sys
r,k,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
d=open(r,'rb').read(); B=0x80000; bank=5+2*k
open(out,'wb').write(d[:0x280000]+b'\xff'*0x80000+d[bank*B:(bank+2)*B])
