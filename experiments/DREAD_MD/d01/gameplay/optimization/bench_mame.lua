-- NTSC DREAD C7 benchmark launched from frozen title via RAM request.
-- Starts the same 312-frame scripted E1M1 camera route for all ROMs.
local cpu=manager.machine.devices[":maincpu"]
assert(cpu,"Genesis MAME maincpu unavailable")
local mem=cpu.spaces["program"]
assert(mem,"MAME 68000 program space unavailable")
local function addr(var)
  local off=assert(tonumber(os.getenv("DREAD_"..var)),var.." missing")
  return 0xff0000+(off%65536)
end
local req=addr("BENCH_REQ")
local done=addr("BENCH_DONE")
local frames_addr=addr("BENCH_FRAMES")
local vblanks_addr=addr("BENCH_VINTS")
local mode=assert(tonumber(os.getenv("DREAD_BENCH_MODE")),"benchmark mode missing")
local frame=0
local requested=false
local reported=false
emu.register_frame_done(function()
  frame=frame+1
  if frame==60 then
    local screen=manager.machine.screens[":screen"] or manager.machine.screens:at(1)
    local colors={}
    for y=20,180,20 do
      for x=20,300,20 do colors[screen:pixel(x,y)]=true end
    end
    local n=0 for _ in pairs(colors) do n=n+1 end
    print("DREAD_BOOT_SAMPLED_COLORS="..n)
  end
  if frame>=90 and not requested then
    mem:write_u16(req,mode)
    requested=true
    print(string.format("DREAD_BENCH_REQUEST mode=%d readback=%d",mode,mem:read_u16(req)))
  end
  if requested and not reported and mem:read_u16(done)>=1 then
    local f=mem:read_u32(frames_addr)
    local v=mem:read_u32(vblanks_addr)
    print(string.format("DREAD_BENCH_RESULT mode=%d frames=%d vblanks=%d fps_x1000=%d",
                        mode,f,v, v>0 and math.floor(f*60000/v+0.5) or 0))
    reported=true
  end
  if frame%1800==0 then print(string.format("DREAD_BENCH_PROGRESS emu_vblanks=%d done=%d",frame,mem:read_u16(done))) end
end)
