#!/usr/bin/env python3
"""Experimental Pair-H 25% CHROMA microdither on the original R22 palette.

Uses one provably unused R22 palette slot (index 1, formerly black) as a new
blue-family accent without modifying any source-index -> base-color mapping.
All 14 PLAYPAL effect palettes receive the corresponding tinted accent.
Partners are selected against original PLAYPAL source colors; gray base slots
are locked to themselves. No runtime color search and no new VDP tile banks.
This is an A/B visual probe, not guaranteed to improve perceptual fidelity.
"""
from __future__ import annotations

import colorsys
import json
import math
import re
import runpy
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HEADER=ROOT/'src/r22_palette.h'
TABLE=ROOT/'src/r53_pairh_micro_tables.h'
REPORT=ROOT/'src/r53_pairh_chroma_report.json'

def lin(v):
    v=v/255.0
    return v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4

def srgb(v):
    v=max(0.0,min(1.0,v))
    return 255.0*(12.92*v if v<=0.0031308 else 1.055*v**(1.0/2.4)-0.055)

def mix(a,b):
    return tuple(srgb(0.75*lin(x)+0.25*lin(y)) for x,y in zip(a,b))

def sq(a,b):
    return sum((x-y)**2 for x,y in zip(a,b))

def luma(a):
    return .2126*a[0]+.7152*a[1]+.0722*a[2]

def hue_compatible(a,m):
    ha,sa,_=colorsys.rgb_to_hsv(*(x/255.0 for x in a))
    hb,sb,_=colorsys.rgb_to_hsv(*(x/255.0 for x in m))
    if sa<.22 or sb<.16: return True
    return min(abs(ha-hb),1-abs(ha-hb))<=.11

def main():
    gp=runpy.run_path(str(ROOT/'scripts/genpal.py'))
    text=HEADER.read_text()
    ma=re.search(r'r22_color\[256\]=\{([^}]+)\}',text)
    assert ma, 'missing R22 color map'
    indices=[int(v) for v in ma.group(1).split(',')]
    assert len(indices)==256 and 1 not in indices, 'palette slot 1 must be UNUSED'
    prefix,split,rest=text.partition('static const uint16_t r22_cram[14][16]={')
    assert split, 'unexpected CRAM format'
    body,close,suffix=rest.partition('};')
    assert close
    rows=re.findall(r'\{([^}]+)\}',body)
    assert len(rows)==14
    cram=[[int(v) for v in row.split(',')] for row in rows]
    assert all(len(row)==16 for row in cram) and cram[0][1]==0
    src=gp['decode_subpal'](gp['load_playpal'](),0)
    assert len(src)==256
    colors=[gp['gen_to_rgb'](w) for w in cram[0]]
    groups={i:[src[k] for k in range(256) if indices[k]==i] for i in range(2,16)}
    means={i:tuple(sum(p[c] for p in group)/len(group) for c in range(3))
           for i,group in groups.items() if group}
    # Pure grays MUST stay exact: previous M25 shifted index 8 gray to beige.
    neutral={0,1,8,11,14,15}
    chromatic=[i for i in means if i not in neutral]
    blue=[i for i in chromatic if colors[i][2]>colors[i][0]+24 and
          colors[i][2]>colors[i][1]+24]
    assert blue, 'no blue group to test'
    choices={}
    baseloss={}
    for i in chromatic:
        base=colors[i]
        best=(sq(base,means[i]),i)
        for j in range(2,16):
            if j==i: continue
            c=colors[j]
            if math.sqrt(sq(base,c))>145 or abs(luma(base)-luma(c))>68: continue
            m=mix(base,c)
            if not hue_compatible(base,m):continue
            loss=sq(m,means[i])
            if loss<best[0]:best=(loss,j)
        baseloss[i]=best[0]
        choices[i]=best[1]
    # Optimize the unused CRAM slot in the full 3-bit/channel Mega Drive grid.
    # Restrict to blue/violet hue so gray ceilings cannot acquire beige tints.
    candidates=[]
    for red in range(8):
        for green in range(8):
            for bluechan in range(8):
                word=(bluechan<<9)|(green<<5)|(red<<1)
                rgb=gp['gen_to_rgb'](word)
                if rgb[2]<109 or rgb[2]<rgb[0]+40 or rgb[2]<rgb[1]+25:
                    continue
                if min(math.sqrt(sq(rgb,colors[j])) for j in range(2,16))<30:
                    continue
                gains={}
                for i in blue:
                    if math.sqrt(sq(colors[i],rgb))>165 or abs(luma(colors[i])-luma(rgb))>82:continue
                    mixed=mix(colors[i],rgb)
                    if not hue_compatible(colors[i],mixed):continue
                    gain=baseloss[i]-sq(mixed,means[i])
                    if gain>0:gains[i]=gain*len(groups[i])
                score=sum(gains.values())
                candidates.append((score,word,rgb,gains))
    assert candidates, 'no free-slot blue candidates'
    candidates.sort(key=lambda x:(x[0],-x[1]),reverse=True)
    score,accent_word,accent,gains=candidates[0]
    # At worst, force the least-error blue pairing for a visible A/B test,
    # explicitly report that it did not improve this proxy metric.
    forced=False
    if not gains:
        forced=True
        best=None
        for _,word,rgb,_ in candidates:
            for i in blue:
                if math.sqrt(sq(colors[i],rgb))>165:continue
                loss=sq(mix(colors[i],rgb),means[i])
                rec=(loss,word,rgb,i)
                if best is None or rec[0]<best[0]:best=rec
        assert best, 'no usable blue accent'
        _,accent_word,accent,forced_i=best
        choices[forced_i]=1
    else:
        for i in blue:
            mixed=mix(colors[i],accent)
            if i in gains and sq(mixed,means[i])+0.001<baseloss[i]:
                choices[i]=1
    partners=list(range(16))
    for i,j in choices.items():
        if i not in neutral:partners[i]=j
    assert all(partners[i]==i for i in neutral),partners
    assert any(partners[i]==1 for i in blue),('new slot unused',partners)
    assert partners[1]==1
    # Select a source PLAYPAL anchor to preserve red/green flashes and other
    # subpalette effects without hand-invented tint constants.
    src_anchor=min(range(256),key=lambda i:sq(src[i],accent))
    for sub in range(14):
        if sub==0:
            cram[sub][1]=accent_word
        else:
            colors_sub=gp['decode_subpal'](gp['load_playpal'](),sub)
            cram[sub][1]=gp['gen_color'](colors_sub[src_anchor])
    HEADER.write_text(prefix+split+'\n'+',\n'.join('{'+','.join(map(str,row))+'}' for row in cram)+'};'+suffix)
    TABLE.write_text('/* Generated chromatic Pair-H M25: new CRAM slot 1 is an accent. */\n'
                     '#ifndef R53_PAIRH_MICRO_TABLES_H\n'
                     '#define R53_PAIRH_MICRO_TABLES_H\n'
                     '#include <stdint.h>\n'
                     'static const uint8_t r53_pairh_partner[16]={'+
                     ','.join(map(str,partners))+'};\n#endif\n')
    report={
        'mode':'Pair-H micro25 CHROMA', 'ratio_percent':25,
        'unused_slot_repurposed':1,'r22_index_1_unused':True,
        'base_index_mapping_unchanged':True,
        'neutral_locked':sorted(neutral),
        'blue_slots':blue,'new_accent_RGB':[int(round(c)) for c in accent],
        'new_accent_genesis_word':hex(accent_word),
        'subpalette_words_for_slot1':[hex(row[1]) for row in cram],
        'proxy_weighted_blue_gain':round(score,3),
        'forced_visual_probe':forced,
        'active_color_pairs':sum(j!=i for i,j in enumerate(partners)),
        'partner_map':partners,
        'note':'Original R22 palette except unused slot1, tinted across 14 palettes; no claims of better appearance without visual test.'}
    REPORT.write_text(json.dumps(report,indent=2)+'\n')
    print('Pair-H chroma micro25 accent',report['new_accent_RGB'],
          'blue slots',blue,'active',report['active_color_pairs'],
          'forced',forced,'partner',partners)

if __name__=='__main__':
    main()
