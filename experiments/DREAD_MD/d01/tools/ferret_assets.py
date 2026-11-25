"""Geometry preparation for the Ferret-derived wall backend; collision unchanged."""
import math

def split_render_segments(rows, subs, vertices, maximum=256):
    result, outsubs = [], []
    for count, first in subs:
        begin = len(result)
        for row in rows[first:first+count]:
            a, b = vertices[row[0]], vertices[row[1]]
            parts = max(1, math.ceil(row[-1] / maximum))
            prev, oldoff = row[0], 0
            for k in range(1, parts+1):
                if k == parts:
                    end, offset = row[1], row[-1]
                else:
                    point = (round(a[0]+(b[0]-a[0])*k/parts), round(a[1]+(b[1]-a[1])*k/parts))
                    end = len(vertices); vertices.append(point)
                    offset = round(row[-1]*k/parts)
                if vertices[prev] != vertices[end]:
                    r = list(row); r[0:2] = [prev, end]
                    r[8] += oldoff; r[-1] = offset-oldoff
                    result.append(tuple(r))
                prev, oldoff = end, offset
        outsubs.append((len(result)-begin, begin))
    if len(vertices) > 65535 or len(result) > 65535:
        raise ValueError('Ferret render geometry exceeds 16-bit indices')
    return result, outsubs
