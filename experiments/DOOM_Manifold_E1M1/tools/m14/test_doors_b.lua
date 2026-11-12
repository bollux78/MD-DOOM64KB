local mem=manager.machine.devices[":maincpu"].spaces["program"]
local P=tonumber(os.getenv("AP"),16); local L=tonumber(os.getenv("AL"),16)
local fB=manager.machine.ioport.ports[":ctrl1:mdpad:PAD"].fields["P1 B"]
local doors={{68,159,2947,-3837},{68,160,2911,-3840},{76,172,3008,-4036},{76,178,3008,-4016}}
local n=0
local function st(d) local b=mem:read_u32(L)&0xFFFFFF; return mem:read_i16(b+d*16+4), mem:read_i16(b+d*16+10) end
local base={}
emu.register_frame_done(function() n=n+1
 for k,d in ipairs(doors) do
  local t0=300+(k-1)*400
  if n>=t0 and n<t0+250 then
   mem:write_u32(P,d[3]<<10); mem:write_u32(P+4,d[4]<<10); mem:write_u16(P+12,d[2])
   if n==t0+5 then base[k]={st(d[1])} ; print(string.format("door %d before state=%d ceil=%d",d[1],st(d[1]))) end
   if n==t0+10 then fB:set_value(1) end
   if n==t0+20 then fB:set_value(0) end
   if n==t0+80 or n==t0+200 then print(string.format("door %d t+%d state=%d ceil=%d",d[1],n-t0,st(d[1]))) end
  end
 end end)
