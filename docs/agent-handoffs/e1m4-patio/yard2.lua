local n=0
local m=manager.machine.devices[":maincpu"].spaces["program"]
local p=manager.machine.ioport.ports[":ctrl1:mdpad:PAD"]
local D=0xFF2374
emu.register_frame_done(function() n=n+1
 local st=0
 if (n>=100 and n<110) or (n>=150 and n<160) then st=1 end
 p.fields["P1 Start"]:set_value(st)
 local b=0xFF13DE
 if n>=1500 then
  m:write_i32(b,1600*1024) m:write_i32(b+4,816*1024) m:write_u16(b+12,161)
  local k=(n-1500)//150
  m:write_u16(b+14,(k%8)*128)
  local ph=(n-1500)%150
  if ph==20 then for i=0,4 do m:write_u32(D+4*i,0) end end
  if ph==140 and k<8 then
   print("ang",(k%8)*128,"frustum",m:read_u32(D),"backface",m:read_u32(D+4),"x1>max",m:read_u32(D+8),"x2<min",m:read_u32(D+12),"nearcull",m:read_u32(D+16),"visits?")
  end
 end end)
