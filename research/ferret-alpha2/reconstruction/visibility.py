"""Independent interpreter for the observed visibility stream, not an instruction emulator."""
class Memory:
 def __init__(self,rom,ram):self.rom=rom;self.ram=bytearray(ram)
 def get(self,address,n):
  a=address&0xffffff
  if a>=0xff0000:return bytes(self.ram[(a&65535):(a&65535)+n])
  if a+n<=len(self.rom):return self.rom[a:a+n]
  raise ValueError(hex(a))
 def u8(self,a):return self.get(a,1)[0]
 def u16(self,a):return int.from_bytes(self.get(a,2),'big')
 def s16(self,a):v=self.u16(a);return v-65536 if v&32768 else v
 def u32(self,a):return int.from_bytes(self.get(a,4),'big')
 def put(self,a,v,n):a&=65535;self.ram[a:a+n]=(v&((1<<(8*n))-1)).to_bytes(n,'big')

def visible_list(mem,stream):
 wallbase=mem.u32(0xff1014);sectorbase=mem.u32(0xff1008);commonbase=mem.u32(0xff1010)
 actorend=mem.u32(0xff1b80);actorlimit=mem.u32(0xff1a7c);stamp=mem.u16(0xff1a28);previous=(stamp-1)&65535
 mem.put(0xff0026,1,2)
 records=[];actors=[];flag=1;return_to=None;common_end=None;tokens=[]
 for _ in range(100000):
  if stream==common_end:
   stream=return_to;return_to=None;common_end=None
  token=mem.u16(stream);stream+=2;tokens.append(token)
  if token==0:break
  if token<0x8000:
   assert return_to is None, 'Unexpected nested common run'
   return_to=stream;mem.put(0xff0022,stream,4);common_end=commonbase+token*2;stream=common_end
   while True:
    stream-=2
    if mem.u16(stream)==0:stream+=2;break
  elif token<0xc000:
   records.append((flag,wallbase+28*(token-0x8000)))
  elif token<0xf000:
   sec=sectorbase+14*(token-0xc000)
   if mem.u16(sec+8)!=previous:
    actor=mem.u32(sec+4)
    while actor:
     if not mem.u8(actor+12):
      if actorend>=actorlimit:break
      actors.append(actor);mem.put(actorend,actor,4);actorend+=4;mem.put(actor+12,1,1)
     actor=mem.u32(actor)
   mem.put(sec+8,stamp,2)
  else:
   flag=token-0xf000;mem.put(0xff0026,flag,2)
   if not mem.u8(0xff1b84+(flag>>1)):
    while True:
     token=mem.u16(stream);stream+=2;tokens.append(token)
     if token==0:break
     if token>=0xf000:
      stream-=2;break
    if token==0:break
 else:raise RuntimeError('Stream did not terminate')
 dest=0xff01e4
 for f,p in records:mem.put(dest,f,2);mem.put(dest+2,p,4);dest+=6
 mem.put(dest,0xffff,2);mem.put(0xff1b80,actorend,4)
 return {'records':records,'actors':actors,'tokens':tokens,'destination_end':dest}

def read_records(mem):
 out=[];p=0xff01e4
 for _ in range(2000):
  f=mem.u16(p)
  if f==65535:return out
  out.append((f,mem.u32(p+2)));p+=6
 raise RuntimeError('No sentinel')
