#!/usr/bin/env python3
"""Link one set of converted maps into an episode with shared graphics and packed PVS."""
import re
import os
from ferret_columns import encode_column
import sys
from pathlib import Path

TABLES = (
    "map_verts map_segs map_subs map_nodes map_sectors_init map_lines map_doors "
    "map_ndoors map_sector_tag map_tex map_start map_counts map_sprites map_things "
    "map_nthings map_sub_things map_bm map_bm_off map_bm_list "
    "map_mframes map_fx map_reject map_secadj_off map_secadj"
).split()
SCALARS = {"map_ndoors", "map_nthings"}
PAD = 32   # EP_TEX_PAD in mapdata.h, conv --tex-pad
SHARED = {"md_palette", "pal_rgb_all", "num_palettes", "pal_remap", "sintab"}


def entries(path):
    source = path.read_text().replace(", pvs_sbytes = ", ";\nconst uint16_t pvs_sbytes = ")
    return dict((match[1], match[0]) for match in re.finditer(
        r"^const \w+ (\w+)(?:\[\d+\])* = [^;]+;", source, re.M))


def initializer(line):
    return line.partition(" = ")[2].removesuffix(";")


def numbers(line):
    return list(map(int, re.findall(r"-?\d+", initializer(line))))


def array(name, values, kind="uint8_t", storage="static "):
    return f"{storage}const {kind} {name}[{len(values)}] = " + "{" + ",".join(map(str, values)) + "};"


class Bank:
    def __init__(self):
        self.data = bytearray()
        self.index = {}

    def add(self, block, alignment=1):
        if block not in self.index:
            self.data.extend(bytes(-len(self.data) % alignment))
            self.index[block] = len(self.data)
            self.data.extend(block)
        return self.index[block]


def pvs_encode(raw):
    """Encode zero runs and nonzero literals, with a raw fallback."""
    packed = bytearray([1])
    first = 0
    while first < len(raw):
        zero = raw[first] == 0
        last = first + 1
        while last < min(first + 128, len(raw)) and (raw[last] == 0) == zero:
            last += 1
        packed.append((last-first-1) | (0x80 if zero else 0))
        if not zero:
            packed.extend(raw[first:last])
        first = last
    return bytes(packed) if len(packed) < len(raw)+1 else b"\0" + raw


def main():
    target = Path(sys.argv[1])
    maps = [Path(p) for p in sys.argv[2:]]
    tex, spr, pvs = Bank(), Bank(), Bank()
    column_tables = {}
    columns = []
    counts, widths, definitions = [], [], []
    max_actors = 1
    out = ['#define DREAD_EPISODE_DATA', '#include "mapdata.h"']
    sizes = dict(textures=0, sprites=0, visibility=0)
    common = None
    for i, path in enumerate(maps):
        data = entries(path/"mapdata.c")
        if os.environ.get("DREAD_FERRET_COLUMN_RLE","0")=="1" and 'DREAD_SOURCE_PIXELS=1' not in (path/'mapdata.c').read_text():
            raise ValueError(f"{path}: compressed Ferret episode requires native WAD source pixels")
        shared = {name: data[name] for name in SHARED}
        if common is None:
            common = shared
            out.extend(shared[name] for name in sorted(shared))
        elif common != shared:
            raise ValueError(f"{path}: palette or sine tables differ")
        counts.append(numbers(data["map_counts"]))
        nsub = counts[-1][2]
        things = numbers(data["map_things"])
        max_actors = max(max_actors, sum(bool(flag & 1) for flag in things[4::5]))
        for field, blob_name, bank, alignment, size_name in [
            ("map_tex", "tex_blob", tex, 1, "textures"),
            ("map_sprites", "spr_blob", spr, 2, "sprites"),
        ]:
            blob = bytes(numbers(data[blob_name]))
            sizes[size_name] += len(blob)
            line = data[field]
            args = initializer(line)
            if field == "map_tex":
                # Keep the twice-stored column format for the 68000 scalers.
                pattern = r"\{(\d+),(\d+),\d+,\d+,\{([\d,]+)\},\{[\d,]+\}\}"
                groups = list(re.finditer(pattern, args))
                for group in reversed(groups):
                    width, h = 1 << int(group[1]), 1 << int(group[2])
                    stride = h + min(h, PAD)
                    indices = []
                    for start in map(int, group[3].split(",")):
                        if start + width * stride > len(blob):
                            raise ValueError(f"{path}: texture outside bank")
                        row = tuple(bank.add(encode_column(blob[pos:pos+stride]) if os.environ.get("DREAD_FERRET_COLUMN_RLE","0")=="1" else blob[pos:pos+stride])
                                    for pos in range(start, start+width*stride, stride))
                        if row not in column_tables:
                            column_tables[row] = len(columns)
                            columns.extend(row)
                        indices.append(column_tables[row])
                    args = args[:group.start(3)] + ",".join(map(str, indices)) + args[group.end(3):]
            else:
                groups = list(re.finditer(r"\{([\d,]+)\}", args))
                lookup = sorted({int(v) for group in groups for v in group[1].split(",")})
                offsets = {start: bank.add(blob[start:end], alignment)
                           for start, end in zip(lookup, lookup[1:]+[len(blob)])}
                for group in reversed(groups):
                    rewritten = ",".join(str(offsets[int(v)]) for v in group[1].split(","))
                    args = args[:group.start(1)] + rewritten + args[group.end(1):]
            data[field] = line.partition(" = ")[0] + " = " + args + ";"
        vis = entries(path/"pvs.c")
        nw, sw = (numbers(vis[k])[0] for k in ("pvs_nbytes", "pvs_sbytes"))
        widths.append(nw+sw)
        nodes, subs = (bytes(numbers(vis[k])) for k in ("pvs_nodes", "pvs_subs"))
        if len(nodes) != nsub*nw or len(subs) != nsub*sw:
            raise ValueError(f"{path}: PVS size mismatch")
        sizes["visibility"] += len(nodes)+len(subs)
        offsets = [pvs.add(pvs_encode(nodes[j*nw:(j+1)*nw] + subs[j*sw:(j+1)*sw])) for j in range(nsub)]
        out.append(array(f"ep{i}_pvs", offsets, "uint32_t"))
        # The renderer uses the segment length, but never reads its linedef ID.
        data["map_segs"] = re.sub(r"\{((?:-?\d+,){10})-?\d+,(-?\d+)\}",
                                 r"{\1\2}", data["map_segs"])
        fields = []
        for key in TABLES:
            if key in SCALARS:
                fields.append(initializer(data[key]))
            else:
                name = f"ep{i}_{key}"
                fields.append(name)
                out.append("static " + re.sub(r"\b"+key+r"\b", name, data[key], count=1))
        definitions.append("{" + ",".join(fields + [f"ep{i}_pvs", str(nw), str(sw)]) + "}")
    out.extend((array("tex_blob", tex.data, storage=""), array("spr_blob", spr.data, storage=""),
                array("episode_pvs", pvs.data, storage=""),
                "const uint8_t *const tex_columns[] = {" + ",".join(f"tex_blob+{o}" for o in columns) + "};",
                "const DreadMap episode_maps[] = {" + ",\n".join(definitions) + "};",
                f"const uint16_t episode_map_count = {len(maps)};",
                "const DreadMap *dread_map = episode_maps;"))
    target.mkdir(parents=True, exist_ok=True)
    (target/"episode.c").write_text("\n".join(out)+"\n")
    (target/"mapcounts.h").write_text(
        f"#define MAP_NVERTS {max(c[0] for c in counts)}\n"
        f"#define MAP_NSECTORS {max(c[4] for c in counts)}\n"
        f"#define MAP_NSUBS {max(c[2] for c in counts)}\n"
        f"#define MAP_NACTORS {max_actors}\n"
        f"#define EP_PVS_BYTES {max(widths)}\n")
    print(f"textures {sizes['textures']} -> {len(tex.data)+4*len(columns)} B (inclui ponteiros)")
    print(f"geometry: {2*sum(c[1] for c in counts)} B removed (unused segment linedef IDs)")
    print(f"sprites {sizes['sprites']} -> {len(spr.data)} B")
    print(f"PVS {sizes['visibility']} -> {len(pvs.data)+4*sum(c[2] for c in counts)} B (inclui índices)")


if __name__ == "__main__":
    main()
