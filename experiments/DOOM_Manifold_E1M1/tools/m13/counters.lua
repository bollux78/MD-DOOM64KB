local mem = manager.machine.devices[":maincpu"].spaces["program"]
local f = io.open(os.getenv("CNT_OUT"), "w")
local n = 0
local D = tonumber(os.getenv("AD"), 16)
emu.register_frame_done(function()
  n = n + 1
  f:write(string.format("%d %d %d %d %d\n", n, mem:read_u16(0xFF0228), mem:read_u32(D), mem:read_u32(D+28), mem:read_u16(tonumber(os.getenv("AC"),16))))
  f:flush()
end)
