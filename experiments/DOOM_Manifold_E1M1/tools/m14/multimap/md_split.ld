OUTPUT_ARCH(m68k)
SEARCH_DIR(.)
/*GROUP(-lbcc -lc -lgcc)*/
__DYNAMIC  =  0;

/*
 * Setup the memory map of the SEGA Genesis.
 * stack grows down from high memory.
 *
 * The memory map look like this:
 * +--------------------+ <- low memory
 * | .text              |
 * |        _etext      |
 * |        ctor list   | the ctor and dtor lists are for
 * |        dtor list   | C++ support
 * +--------------------+
 * .                    .
 * .                    .
 * .                    .
 * +--------------------+ <- 0xE0FF0000
 * | .data              | initialized data goes here
 * |        _data       |
 * |        _edata      |
 * +--------------------+
 * | .bss               |
 * |        _bstart     | start of bss, cleared by crt0
 * |        _bend       | start of heap, used by sbrk()
 * +--------------------+
 * .                    .
 * .                    .
 * .                    .
 * |        __stack     | top of stack
 * +--------------------+ <- 0xE1000000
 */
MEMORY
{
	rom (rx) : ORIGIN = 0x00000000, LENGTH = 0xE0000000
	ram : ORIGIN = 0xE0FF0000, LENGTH = 0x00010000
}

/*
 * allocate the stack to be at the top of memory, since the stack
 * grows down
 */

PROVIDE (__stack = 0xE1000000);


SECTIONS
{
  .common 0x00010000 :
  {
    */res/graphics_res.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */res/hud.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */res/sfx_res.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */res/sprites_res.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/active_sectors.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/bob.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/building_test_map.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/bunch_render.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/clip_buf.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/collision.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/console.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/div_lut.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/doom_statusbar.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/draw.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/editor_test_map.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/fire.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/fire_native.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/game.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/game_mode.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/init.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/inventory.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/joy_helper.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/main.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/main_menu.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/map_table.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/math3d.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/menu_helper.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/music.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/my_bmp.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/my_bmp_a.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/obj_sprite.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/object.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/overlapping_test_map.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/portal_map.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/random.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/real_timer.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/sfx.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/tex_draw_tables.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/tex_table_lookup.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/texture.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/utils.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/vwf.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/vwf_decl.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */src/weapon_sprites.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */libmd.a:*(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    */libgcc.a:*(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = ALIGN(0x1000);
  } > rom
  .mapobjs 0x00301800 :
  {
    . = 0x0;
    */src/level.o(.text.check_trigger_switch)
    . = 0x400;
    */src/level.o(.text.clean_portal_map)
    . = 0x800;
    */src/level.o(.text.load_portal_map)
    . = 0xC00;
    */src/sector_group.o(.text.run_sector_group_processes)
    . = 0x1000;
    */src/sector_group.o(.text.activate_sector_group_enter_trigger)
    . = 0x1400;
    */src/portal.o(.text.portal_rend)
    . = 0x1500;
    */src/e1m1_map.o(.rodata.e1_block_offsets)
    . = 0x1B00;
    */src/m14_bgm.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .lit)
    . = 0x2000;
    */src/colors.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = 0x2800;
    */src/level.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = 0x3000;
    */src/sector_group.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = 0x3C00;
    */src/manifold_sky.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = 0x5200;
    */src/portal.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = 0x8800;
    */src/m12_doom_objects.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = 0x30000;
    */src/e1m1_map.o(.rodata.e1m1_map)
    . = 0x30100;
    */src/e1m1_map.o(.rodata.e1_block_segs)
    */src/e1m1_map.o(.rodata.str1.1)
    . = ALIGN(4);
    */src/e1m1_map.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = 0x50000;
    */src/textures.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
    . = ALIGN(2);
    */res/music_res.o(.text .text.* .rodata .rodata.* .rodata_bin .rodata_binf .gcc_except_table .gcc_except_table.* .lit)
  } > rom
  .maphead 0x00300000 :
  {
    KEEP(*(.text.keepboot))
    *(.text.*) *(.text)
    . = ALIGN(0x4);
     __CTOR_LIST__ = .;
    LONG((__CTOR_END__ - __CTOR_LIST__) / 4 - 2)
    *(.ctors)
    LONG(0)
    __CTOR_END__ = .;
    __DTOR_LIST__ = .;
    LONG((__DTOR_END__ - __DTOR_LIST__) / 4 - 2)
    *(.dtors)
    LONG(0)
    __DTOR_END__ = .;
    *(.rodata .rodata.*)
    *(.gcc_except_table .gcc_except_table.*)
    . = ALIGN(0x4);
    __INIT_SECTION__ = . ;
    *(.init)
    SHORT (0x4E75)
    __FINI_SECTION__ = . ;
    *(.fini)
    SHORT (0x4E75)
    . = ALIGN(0x4);
    ASSERT(. <= 0xE00, "map head too big");
    . = 0xE00;
  } > rom
  _etext = 0x00300E00;
  _stext = 0x00300E00;
  .data 0xE0FF0000 : AT ( 0x00300E00 ) SUBALIGN(2)
  {
    *(.got.plt) *(.got)
    *(.shdata)
    *(EXCLUDE_FILE(*/src/colors.o */src/e1m1_map.o */src/level.o */src/m12_doom_objects.o */src/manifold_sky.o */src/portal.o */src/sector_group.o */src/textures.o) .data EXCLUDE_FILE(*/src/colors.o */src/e1m1_map.o */src/level.o */src/m12_doom_objects.o */src/manifold_sky.o */src/portal.o */src/sector_group.o */src/textures.o) .data.*)
    *(.ramprog .ramprog.*)
    */src/colors.o(.data .data.*)
    */src/e1m1_map.o(.data .data.*)
    */src/level.o(.data .data.*)
    */src/m12_doom_objects.o(.data .data.*)
    */src/manifold_sky.o(.data .data.*)
    */src/portal.o(.data .data.*)
    */src/sector_group.o(.data .data.*)
    */src/textures.o(.data .data.*)
    _edata = .;
  } > ram
  _sdata = 0x6A0;

  .bss 0xE0FF0000 + 0x6C0 : SUBALIGN(2)
  {
    _start = . ;
    *(.shbss)
    *(EXCLUDE_FILE(*/src/colors.o */src/e1m1_map.o */src/level.o */src/m12_doom_objects.o */src/manifold_sky.o */src/portal.o */src/sector_group.o */src/textures.o) .bss EXCLUDE_FILE(*/src/colors.o */src/e1m1_map.o */src/level.o */src/m12_doom_objects.o */src/manifold_sky.o */src/portal.o */src/sector_group.o */src/textures.o) .bss.*)
    *(EXCLUDE_FILE(*/src/colors.o */src/e1m1_map.o */src/level.o */src/m12_doom_objects.o */src/manifold_sky.o */src/portal.o */src/sector_group.o */src/textures.o) COMMON)
    */src/colors.o(.bss .bss.* COMMON)
    */src/e1m1_map.o(.bss .bss.* COMMON)
    */src/level.o(.bss .bss.* COMMON)
    */src/m12_doom_objects.o(.bss .bss.* COMMON)
    */src/manifold_sky.o(.bss .bss.* COMMON)
    */src/portal.o(.bss .bss.* COMMON)
    */src/sector_group.o(.bss .bss.* COMMON)
    */src/textures.o(.bss .bss.* COMMON)
    . = 0x1D20;
    _bend = . ;
  } > ram
  .stab 0 (NOLOAD) : { *(.stab) }
  .stabstr 0 (NOLOAD) : { *(.stabstr) }
  .eh_frame 0 (NOLOAD) : { *(.eh_frame) }
}
