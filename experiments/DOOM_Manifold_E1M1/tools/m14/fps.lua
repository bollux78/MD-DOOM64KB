-- Mede FPS renderizado: cur_frame (RAM, ADDR_CF hex) por VBlank. Saida em FPS_OUT.
local mem = manager.machine.devices[":maincpu"].spaces["program"]
local A = tonumber(os.getenv("ADDR_CF"), 16)
local n, f = 0, io.open(os.getenv("FPS_OUT"), "w")
emu.register_frame_done(function()
  n = n + 1
  if n % 60 == 0 then f:write(string.format("%d %d\n", n, mem:read_u32(A))); f:flush() end
end)
