-- NTSC DREAD C7 benchmark launched from frozen title via RAM request.
-- Starts the first 312 rendered frames of the WAD DEMO3 E1M7 in all ROMs.
-- Adds, per run: a histogram of VBlanks per game frame (sampled once per
-- emulated frame, so every game frame is counted) and a visual hash of the
-- final screen, to check that variants marked "exact" really draw the same image.
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
local last_f=-1
local last_v=0
local hist={}
local function screen_hash()
  local screen=manager.machine.screens[":screen"] or manager.machine.screens:at(1)
  local w=screen.width
  local h=screen.height
  local acc=0
  for y=0,h-1,2 do
    for x=0,w-1,2 do
      acc=(acc*31+screen:pixel(x,y)) % 4294967296
    end
  end
  return acc
end
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
  if requested and not reported then
    -- bench_vints is only filled at the end of the run, so count VBlanks here: one emulated frame = one VBlank
    local f=mem:read_u32(frames_addr)
    if f~=last_f then
      if last_f>=0 then
        local d=frame-last_v
        hist[d]=(hist[d] or 0)+1
      end
      last_f=f
      last_v=frame
    end
  end
  if requested and not reported and mem:read_u16(done)>=1 then
    local f=mem:read_u32(frames_addr)
    local v=mem:read_u32(vblanks_addr)
    print(string.format("DREAD_BENCH_RESULT mode=%d frames=%d vblanks=%d fps_x1000=%d",
                        mode,f,v, v>0 and math.floor(f*60000/v+0.5) or 0))
    local keys={}
    for d in pairs(hist) do keys[#keys+1]=d end
    table.sort(keys)
    local parts={}
    for _,d in ipairs(keys) do parts[#parts+1]=d.."x"..hist[d] end
    print("DREAD_BENCH_HIST "..table.concat(parts,","))
    print(string.format("DREAD_VISUAL_HASH mode=%d hash=%d",mode,screen_hash()))
    reported=true
    manager.machine:exit()
  end
  if frame%1800==0 then print(string.format("DREAD_BENCH_PROGRESS emu_vblanks=%d game_frames=%d done=%d",frame,mem:read_u32(frames_addr),mem:read_u16(done))) end
end)
