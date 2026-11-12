"""M12 pickup extension, opt-in; uses already-rendered static THINGS.

All logic is staged only in the disposable Manifold copy. Static barrels and
lamps remain unaffected. Coordinates share Doom units with player position.
"""
from pathlib import Path

# Slots in the generated Doom sprite table, resolved by NAME (never assume
# the WAD contains every optional sprite).
GRANTS = {"stimpack":1, "medikit":2, "ammo":3, "shotgun":4,
          "health":5, "armor":6,
          "shells":7, "bulletbox":8, "shellbox":9, "rocketbox":10,
          "greenarmor":11, "bluearmor":12, "chaingun":13, "rocketlauncher":14}

def install(out,templates):
    out=Path(out)
    mapping={name:index+1 for index,(_ident,name,*_) in enumerate(templates)}
    pairs=[(mapping[name],value) for name,value in GRANTS.items() if name in mapping]
    if not pairs:
        raise ValueError("M12 pickup stage found no pickable items")
    obj=out/"src/object.c"
    s=obj.read_text()
    anchor="void move_object_to_sector("
    if s.count(anchor)!=1: raise ValueError("M12 object-sector anchor changed")
    cases="".join(f"        case {slot}: kind={kind}; break;\n" for slot,kind in pairs)
    code="""/* M12: pick up existing DECORATIONs near the player's feet, in the
 * same convex cell. Do not traverse portal-connected cells yet, which
 * could pick up items through solid geometry or a closed door. */
extern u8 doom_hud_grant_pickup(u8 kind);
void m12_process_pickups(void) {
    u16 sector=cur_player_pos.cur_sector;
    if (sector>=num_sector_lists) return;
    s16 px=F32_toInt(cur_player_pos.x);
    s16 py=F32_toInt(cur_player_pos.y);
    decoration_link prev=NULL_DEC_LINK;
    decoration_link link=sector_decoration_lists[sector];
    u16 guard=0;
    while (link!=NULL_DEC_LINK && guard++<MAX_DECORATIONS) {
        decoration_link next=DEC_LINK_DEREF(link).next;
        u8 kind=0;
        switch (DEC_LINK_DEREF(link).object_type) {
""" + cases + """        default: break;
        }
        if (kind) {
            s32 dx=(s32)px-DEC_LINK_DEREF(link).x;
            s32 dy=(s32)py-DEC_LINK_DEREF(link).y;
            if (dx>=-24 && dx<=24 && dy>=-24 && dy<=24 &&
                dx*dx+dy*dy<=24*24 && doom_hud_grant_pickup(kind)) {
                /* Correctly unlink ANY node, not just the list head.
                 * Upstream free_decoration() does not fix the previous node. */
                if (prev==NULL_DEC_LINK) sector_decoration_lists[sector]=next;
                else DEC_LINK_DEREF(prev).next=next;
                DEC_LINK_DEREF(link).next=decoration_free_list;
                decoration_free_list=link;
                link=next;
                continue;
            }
        }
        prev=link;
        link=next;
    }
}
"""
    s=s.replace(anchor,code+"\n"+anchor,1)
    obj.write_text(s)

    game=out/"src/game.c"
    g=game.read_text()
    anchor="    process_all_objects(cur_frame);"
    if g.count(anchor)!=1:raise ValueError("M12 game tick anchor changed")
    g=g.replace(anchor,anchor+"\n    m12_process_pickups();",1)
    g=g.replace('#include "object.h"','#include "object.h"\nvoid m12_process_pickups(void);',1)
    game.write_text(g)

    hud=out/"src/doom_statusbar.c"
    h=hud.read_text()
    anchor="void doom_hud_update(void) {"
    if h.count(anchor)!=1:raise ValueError("M12 DOOM status bar anchor changed")
    grant="""/* M12: update the actual Doom HUD counters upon collecting THINGS.
 * No combat or firing mechanics are implied by these counters yet. */
u8 doom_hud_grant_pickup(u8 kind) {
    switch(kind) {
    case 1: /* stimpack */
        if (dhud_state.health>=100) return 0;
        dhud_state.health+=10;
        if (dhud_state.health>100) dhud_state.health=100;
        return 1;
    case 2: /* medikit */
        if (dhud_state.health>=100) return 0;
        dhud_state.health+=25;
        if (dhud_state.health>100) dhud_state.health=100;
        return 1;
    case 3: /* clip */
        if (dhud_state.ammo[0]>=200) return 0;
        dhud_state.ammo[0]+=10;
        if (dhud_state.ammo[0]>200) dhud_state.ammo[0]=200;
        dhud_state.ammo_r=dhud_state.ammo[0];
        return 1;
    case 4: /* shotgun pickup: mark as owned; ammo counter is
             * temporary, before weapon switching is implemented. */
        if ((dhud_state.arms & 2) && dhud_state.ammo[1]>=50) return 0;
        dhud_state.arms|=2;
        dhud_state.ammo[1]+=8;
        if (dhud_state.ammo[1]>50) dhud_state.ammo[1]=50;
        return 1;
    case 5: /* health bonus */
        if (dhud_state.health>=200) return 0;
        dhud_state.health++;
        return 1;
    case 6: /* armor bonus */
        if (dhud_state.armor>=200) return 0;
        dhud_state.armor++;
        return 1;
    case 7: /* shells */
        if (dhud_state.ammo[1]>=50) return 0;
        dhud_state.ammo[1]+=4; if (dhud_state.ammo[1]>50) dhud_state.ammo[1]=50;
        return 1;
    case 8: /* box of bullets */
        if (dhud_state.ammo[0]>=200) return 0;
        dhud_state.ammo[0]+=50; if (dhud_state.ammo[0]>200) dhud_state.ammo[0]=200;
        dhud_state.ammo_r=dhud_state.ammo[0];
        return 1;
    case 9: /* box of shells */
        if (dhud_state.ammo[1]>=50) return 0;
        dhud_state.ammo[1]+=20; if (dhud_state.ammo[1]>50) dhud_state.ammo[1]=50;
        return 1;
    case 10: /* box of rockets */
        if (dhud_state.ammo[2]>=50) return 0;
        dhud_state.ammo[2]+=5; if (dhud_state.ammo[2]>50) dhud_state.ammo[2]=50;
        return 1;
    case 11: /* green armor */
        if (dhud_state.armor>=100) return 0;
        dhud_state.armor=100;
        return 1;
    case 12: /* blue armor */
        if (dhud_state.armor>=200) return 0;
        dhud_state.armor=200;
        return 1;
    case 13: /* chaingun */
        if ((dhud_state.arms & 4) && dhud_state.ammo[0]>=200) return 0;
        dhud_state.arms|=4;
        dhud_state.ammo[0]+=20; if (dhud_state.ammo[0]>200) dhud_state.ammo[0]=200;
        dhud_state.ammo_r=dhud_state.ammo[0];
        return 1;
    case 14: /* rocket launcher */
        if ((dhud_state.arms & 8) && dhud_state.ammo[2]>=50) return 0;
        dhud_state.arms|=8;
        dhud_state.ammo[2]+=2; if (dhud_state.ammo[2]>50) dhud_state.ammo[2]=50;
        return 1;
    }
    return 0;
}

"""
    hud.write_text(h.replace(anchor,grant+anchor,1))
    print("M12 pickups enabled:",pairs)
