local mem = manager.machine.devices[":maincpu"].spaces["program"]
local A=tonumber(os.getenv("AP"),16); local n=0
local angs={0,256,512,768}
emu.register_frame_done(function() n=n+1
 if n>=200 then
  local ph=((n-200)//60)+1
  if ph<=4 then
   mem:write_u32(A,(1312-64)<<10); mem:write_u32(A+4,(-3264)<<10); mem:write_u16(A+12,105); mem:write_u16(A+14,angs[ph])
   if (n-200)%60==55 then manager.machine.video:snapshot() end
  end
 end end)
