Tue Nov  3 01:28:20 UTC 2026

Run requested for R116 demotest from branch head f302d7973d30; retain ROMs and demos private.

R116 probe fix experiment: configure selected demo before G_DoPlayDemo and reject any FAIL (CI gate).

R116 test gate v2: stable G_Ticker breakpoint + explicit r116_active verification; no missing optimized symbol.

R116 safety pass: allow gameplay deviations; check live ticker progress, zone, I_Error, return code and bounded completion.
