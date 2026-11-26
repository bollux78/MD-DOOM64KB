-- MAME alternate diagnostic, run on the existing R01 cartridge.
local cpu=manager.machine.devices[":maincpu"]
local screen=manager.machine.screens[":screen"] or manager.machine.screens:at(1)
local mem=cpu.spaces["program"]
local frames,last=0,0
local pending=nil
local capture=os.getenv("FR_SCREEN_DIR")
local count=tonumber(os.getenv("FR_POSES")) or 4
emu.register_frame_done(function()
  frames=frames+1
  local magic=mem:read_u32(0xfff000)
  if magic~=0x46523031 then
    if frames==60 or frames==600 then
      local pc=cpu.state["CURPC"] or cpu.state["PC"]
      print(string.format("BOOT frame=%d pc=%08X magic=%08X",frames,pc and pc.value or 0,magic))
    end
    return
  end
  local seq=mem:read_u32(0xfff004)
  local stage=mem:read_u32(0xfff008)
  if stage>=0x80000000 then
    local d={};for i=0,12 do d[#d+1]=string.format("%08X",mem:read_u32(0xfff0a0+i*4)) end
    print(string.format("FATAL stage=%08X exception=%s",stage,table.concat(d," ")));manager.machine:exit();return
  end
  if pending and frames>pending.frame then
    local filename=capture and (capture.."/pose-"..pending.pose..".png")
    if filename then local ok,err=pcall(function() screen:snapshot(filename) end);print("SNAPSHOT "..pending.pose.." "..tostring(ok).." "..tostring(err)) end
    local colors={};local nonblack=0
    for y=48,175,4 do for x=0,319,4 do local p=screen:pixel(x,y);colors[p]=true;if p~=0 and p~=0xff000000 then nonblack=nonblack+1 end end end
    local n=0;for _ in pairs(colors) do n=n+1 end
    print("PUBLISHED "..frames.." "..table.concat(pending.m," ").." "..n.." "..nonblack)
    local done=pending.seq>=count;pending=nil
    if done then manager.machine:exit();return end
  end
  if seq>last and stage~=4 then
    last=seq
    local m={}
    for i=0,16 do m[#m+1]=string.format("%08X",mem:read_u32(0xfff000+4*i)) end
    pending={frame=frames,pose=mem:read_u32(0xfff010),seq=seq,m=m}
  end
end)
