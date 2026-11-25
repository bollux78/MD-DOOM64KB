-- MAME alternate diagnostic, run on the existing R01 cartridge.
local cpu=manager.machine.devices[":maincpu"]
local screen=manager.machine.screens[":screen"] or manager.machine.screens:at(1)
local mem=cpu.spaces["program"]
local frames,last=0,0
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
  if stage>=0x80000000 then print(string.format("FATAL stage=%08X",stage));manager.machine:exit();return end
  if seq>last and stage~=4 then
    last=seq
    local m={}
    for i=0,16 do m[#m+1]=string.format("%08X",mem:read_u32(0xfff000+4*i)) end
    local colors={}
    local nonblack=0
    for y=48,175,4 do
      for x=0,319,4 do
        local p=screen:pixel(x,y)
        colors[p]=true
        if p~=0 and p~=0xff000000 then nonblack=nonblack+1 end
      end
    end
    local n=0;for _ in pairs(colors) do n=n+1 end
    print("PUBLISHED "..frames.." "..table.concat(m," ").." "..n.." "..nonblack)
    if seq>=count then manager.machine:exit() end
  end
end)
