local mem = manager.machine.devices[":maincpu"].spaces["program"]
local f = io.open(os.getenv("CNT_OUT"), "w")
local n = 0
emu.register_frame_done(function()
  n = n + 1
  f:write(string.format("%d %d %d %d %d %d %d\n", n, mem:read_u16(0xFF022C), mem:read_u8(0xFF0228), mem:read_u8(0xFF0229), mem:read_u8(0xFF022A), mem:read_u16(0xFF09FC), mem:read_u16(0xFF09FA)))
  f:flush()
end)
