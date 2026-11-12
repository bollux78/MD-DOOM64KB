"""Generate one same-image wall fixture and Doom linedef wire geometry."""
import math
import struct

from import_wad import camera_at, initializer


def close_wall(data):
    vertices, sectors, segs, *_, spawn = data
    sx, sy, _ = spawn
    candidates = []
    for i, (a, b, front, back) in enumerate(segs):
        if back != 0xFFFF:
            continue
        ax, ay = vertices[a]
        bx, by = vertices[b]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length < 64:
            continue
        x = round((ax + bx) / 2 + dy * 24 / length)
        y = round((ay + by) / 2 - dx * 24 / length)
        camera = camera_at(data, x, y, math.atan2(dx, -dy))
        _, _, eye, cosine, sine = camera
        floor, ceiling = sectors[front]
        if not floor + 20 < eye < ceiling - 20:
            continue
        points = [((vx - x) * sine - (vy - y) * cosine,
                   (vx - x) * cosine + (vy - y) * sine) for vx, vy in vertices]
        covered = True
        for col in range(80):
            slope = (col + .5 - 40) / 40
            hits = []
            for j, (v0, v1, _, _) in enumerate(segs):
                x0, z0 = points[v0]
                x1, z1 = points[v1]
                delta = x1 - x0 - slope * (z1 - z0)
                if delta > 0:
                    t = (slope * z0 - x0) / delta
                    depth = z0 + t * (z1 - z0)
                    if 0 <= t < 1 and depth >= 512:
                        hits.append((depth, j))
            if not hits or min(hits)[1] != i:
                covered = False
                break
        if covered:
            candidates.append(((x - sx) ** 2 + (y - sy) ** 2, i, camera))
    if not candidates:
        raise ValueError("no single wall covers all 80 columns")
    _, index, camera = min(candidates)
    return index, camera


def wire_lines(entries, map_name, data):
    index = max(i for i, (key, _) in enumerate(entries) if key == map_name)
    lumps = dict(entries[index + 1:index + 9])
    sides = [row[-1] for row in struct.iter_unpack("<hh8s8s8sH", lumps["SIDEDEFS"])]
    sectors = data[1]
    edges = set()

    def edge(a, z0, b, z1):
        if (a, z0) != (b, z1):
            edges.add((*min((a, z0), (b, z1)), *max((a, z0), (b, z1))))

    def band(a, b, floor, ceiling):
        if ceiling <= floor:
            return
        edge(a, floor, b, floor)
        edge(a, ceiling, b, ceiling)
        edge(a, floor, a, ceiling)
        edge(b, floor, b, ceiling)

    for a, b, flags, _, _, right, left in struct.iter_unpack("<7H", lumps["LINEDEFS"]):
        if right == 0xFFFF:
            right, left = left, right
        floor, ceiling = sectors[sides[right]]
        if left == 0xFFFF or not flags & 4:
            band(a, b, floor, ceiling)
            continue
        other_floor, other_ceiling = sectors[sides[left]]
        band(a, b, min(floor, other_floor), max(floor, other_floor))
        band(a, b, min(ceiling, other_ceiling), max(ceiling, other_ceiling))
    return sorted(edges)


def wire_tree(edges, vertices):
    boxes = []
    for a, za, b, zb in edges:
        ax, ay = vertices[a]
        bx, by = vertices[b]
        boxes.append((min(ax, bx), min(ay, by), min(za, zb),
                      max(ax, bx), max(ay, by), max(za, zb)))
    nodes, order = [], []

    def build(ids):
        limits = tuple(min(boxes[i][axis] for i in ids) for axis in range(3)) + tuple(
            max(boxes[i][axis] for i in ids) for axis in range(3, 6))
        left, bottom, low, right, top, high = limits
        node = len(nodes)
        nodes.append(None)
        if len(ids) <= 10:
            nodes[node] = ((top, bottom, left, right), low, high, len(order), len(ids))
            order.extend(ids)
        else:
            axis = int(top - bottom > right - left)
            ids.sort(key=lambda i: boxes[i][axis] + boxes[i][axis + 3])
            middle = len(ids) // 2
            build(ids[:middle])
            build(ids[middle:])
            nodes[node] = ((top, bottom, left, right), low, high, len(nodes), 0)
        return node

    build(list(range(len(edges))))
    return nodes, order


def emit(path, entries, map_name, data, kind):
    lines = ['#include "nexus.h"']
    if kind == "lines":
        index, camera = close_wall(data)
        lines += [f"const uint16_t nexus_wall_seg = {index};",
                  f"const NxCamera nexus_wall_camera = {initializer(camera)};"]
    else:
        edges = wire_lines(entries, map_name, data)
        lines += ["const NxWireEdge nexus_wire_edges[] = {"]
        lines += ["    " + initializer(edge) + "," for edge in edges]
        lines += ["};", f"const unsigned int nexus_wire_count = {len(edges)};",
                  f"const unsigned int nexus_wire_vertex_count = {len(data[0])};"]
        nodes, order = wire_tree(edges, data[0])
        lines += ["const NxWireNode nexus_wire_nodes[] = {"]
        lines += ["    " + initializer(node) + "," for node in nodes]
        lines += ["};", f"const unsigned int nexus_wire_node_count = {len(nodes)};",
                  "const uint16_t nexus_wire_order[] = {"]
        for i in range(0, len(order), 20):
            lines.append("    " + ", ".join(map(str, order[i:i + 20])) + ",")
        lines += ["};"]
    path.write_text("\n".join(lines) + "\n")
