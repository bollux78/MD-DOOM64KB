# R46 M2C/P2F — 76-column native sprite visible-post emission

User-approved baseline: P2E three ROMs; demo control 11.80 FPS / 180.82 s; P2E experimental 11.78 FPS / 181.12 s, 2134 frames each.

Added callback-driven emission of visible 4x4 sprite posts. This consumes
the existing P2E depth / solid mask / ceiling / floor clipping helper,
iterates at most 76 columns, allocates no permanent memory, and can serve
as a future caller-owned native sprite pipeline interface.

Limitations: one clipped span per column only; portal/window splitting,
masked middle textures, sprite texture selection/rotation, depth ordering,
hardware sprite weapon/sky ownership and pixel4 renderer integration are
NOT implemented here. No actual native 4x4 gameplay or runtime toggle yet.

Acceptance: host oracle 10,000 randomized sprite scans, linked symbols in
M2C only, BSS no greater than control, ROM integrity, three BlastEm smoke
tests, complete DEMO3 A/B and manual PLAY check.

CI: restored automatic push on the P2F branch, with explicit workflow_dispatch.
