local n=0
local m=manager.machine.devices[":maincpu"].spaces["program"]
local p=manager.machine.ioport.ports[":ctrl1:mdpad:PAD"]
local W=0xFF2370
emu.register_frame_done(function() n=n+1
 local st=0
 if (n>=100 and n<110) or (n>=150 and n<160) then st=1 end
 p.fields["P1 Start"]:set_value(st)
 local b=0xFF13DE
 if n>=1500 then
  m:write_i32(b,1600*1024) m:write_i32(b+4,816*1024) m:write_u16(b+12,161)
  local k=(n-1500)//100
  local ang=(k%8)*128
  m:write_u16(b+14,ang)
  if (n-1500)%100==90 and k<8 then
   local s="ang "..ang..":"
   for i=0,3 do
    local o=W+i*16
    s=s..string.format(" [w%d v1=(%d,%d) v2=(%d,%d) clip=%d out=%d p=%d x=%d..%d]",i,m:read_i16(o),m:read_i16(o+2),m:read_i16(o+4),m:read_i16(o+6),m:read_i16(o+8),m:read_i16(o+10),m:read_i16(o+12),m:read_i16(o+12),m:read_i16(o+14))
   end
   print(s)
  end
 end end)
