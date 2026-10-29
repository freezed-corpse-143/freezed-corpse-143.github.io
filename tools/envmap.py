#!/usr/bin/env python3
"""Render an L1 resource-constraint map (environment profile) as SVG from a JSON spec.

    python tools/envmap.py tools/envmaps/rtx3080.json out.svg

The value is the encoding, not the drawing. Four quantities share one picture, each on
its own channel, so a report reader sees capability, evidence grade and the binding
edge without a paragraph of prose:

  edge thickness  ~ sustained bandwidth, LOG scale, fixed px per decade (legend shows real ticks)
  edge arrowheads ~ direction: one head = simplex, both = duplex, "asym" = duplex but unequal
  edge dash       ~ evidence: solid = measured on this machine, dashed = spec sheet,
                    dotted = derived / estimated
  edge colour     ~ utilisation U = demand / capability for the target workload
                    (neutral below 60 %, amber at or above = binding)
  node shape      ~ kind: compute = rounded, memory = square, domain = dashed outline

Every number drawn comes from the spec; the renderer infers nothing.

Spec: nodes carry "row" (vertical map, the default) or "col" (horizontal map), a title
and optional detail lines; links name two nodes, a bandwidth in GB/s and optionally
evidence, dir, duty and notes. Two nodes in different rows with several links between
them is a fan; two columns of several nodes is a pipeline.
"""

import json
import math
import sys
from pathlib import Path

FONT = 13
MONO_ADV = 7.0
CJK_ADV = 13.0
PAD = 14
GROUP_GAP = 66
BLOCK_GAP = 26
INK = "currentColor"
ACCENT = "#d97706"


def text_w(s, size=FONT):
    """Advance width estimate: CJK is full-width, the rest monospace-ish."""
    return sum(CJK_ADV if ord(c) > 0x2E80 else MONO_ADV for c in s) * size / FONT


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def stroke_w(bw, scale):
    """Log scale. DRAM and PCIe differ by 60x; linear would erase everything below DRAM."""
    w = scale["base_px"] + scale["px_per_decade"] * math.log10(max(bw, 0.1))
    return max(scale["min_px"], min(scale["max_px"], w))


def marker_id(colour, size):
    return f"a{size}-{colour.lstrip('#')}"


def marker(colour, size):
    """userSpaceOnUse: markerUnits defaults to strokeWidth, which turns a 28 px edge
    into a 170 px wedge. One marker per (colour, width) keeps the head proportional."""
    s = max(9, size)
    return (f'<marker id="{marker_id(colour, size)}" viewBox="0 0 10 10" refX="9.5" refY="5" '
            f'markerWidth="{s}" markerHeight="{s}" markerUnits="userSpaceOnUse" '
            f'orient="auto-start-reverse"><path d="M0,0.5 L10,5 L0,9.5 z" fill="{colour}"/>'
            f'</marker>')


class Node:
    def __init__(self, spec):
        self.id = spec["id"]
        self.title = spec.get("title", self.id)
        self.lines = spec.get("lines", [])
        self.kind = spec.get("kind", "memory")
        self.group = spec.get("row", spec.get("col"))
        self.w = max(150, max(text_w(self.title, FONT + 2),
                              *(text_w(t) for t in self.lines)) + 2 * PAD)
        self.h = PAD * 2 + FONT + 4 + len(self.lines) * (FONT + 4) + (4 if self.lines else 0)
        self.x = self.y = 0.0


def place(nodes, horizontal, width, margin, gap):
    """Groups lie along one axis: rows stack vertically (vertical map), columns
    stack horizontally (left-to-right map). Members of a group are centred."""
    groups = {}
    for n in nodes.values():
        groups.setdefault(n.group, []).append(n)
    keys = sorted(groups)
    along = (lambda n: n.h) if horizontal else (lambda n: n.w)
    cross = (lambda n: n.w) if horizontal else (lambda n: n.h)
    extents = {g: sum(along(n) for n in groups[g]) + BLOCK_GAP * (len(groups[g]) - 1)
               for g in keys}
    bands = {g: max(cross(n) for n in groups[g]) for g in keys}
    along_total = max(extents.values()) if horizontal else width
    cross_total = sum(bands[g] for g in keys) + gap * (len(keys) - 1)
    c0 = (width - cross_total) / 2 if horizontal else margin + 34
    for g in keys:
        a0 = (margin + 34 + (along_total - extents[g]) / 2) if horizontal \
            else (width - extents[g]) / 2
        for n in groups[g]:
            if horizontal:
                n.y, n.x = a0, c0
                a0 += n.h + BLOCK_GAP
            else:
                n.x, n.y = a0, c0
                a0 += n.w + BLOCK_GAP
        c0 += bands[g] + gap
    return margin + 34 + along_total if horizontal else c0 - gap


def edge_points(a, b, horizontal):
    """The port on a facing b and the port on b facing a."""
    if horizontal:
        p0 = ((a.x + a.w) if b.x >= a.x else a.x, a.y + a.h / 2)
        p1 = (b.x if b.x >= a.x else (b.x + b.w), b.y + b.h / 2)
        return p0, p1
    p0 = (a.x + a.w / 2, (a.y + a.h) if b.y >= a.y else a.y)
    p1 = (b.x + b.w / 2, b.y if b.y >= a.y else (b.y + b.h))
    return p0, p1


def path_for(p0, p1, horizontal, lane):
    """Straight when the ports line up, elbow otherwise."""
    c = lane if lane is not None else (p0[0] + p1[0]) / 2
    if not horizontal:
        if lane is None:
            return f"M{c:.1f},{p0[1]:.1f} L{c:.1f},{p1[1]:.1f}", c, (p0[1] + p1[1]) / 2
        mid = (p0[1] + p1[1]) / 2
        return (f"M{p0[0]:.1f},{p0[1]:.1f} L{p0[0]:.1f},{mid:.1f} L{p1[0]:.1f},{mid:.1f} "
                f"L{p1[0]:.1f},{p1[1]:.1f}"), (p0[0] + p1[0]) / 2, mid
    y = lane if lane is not None else (p0[1] + p1[1]) / 2
    return (f"M{p0[0]:.1f},{y:.1f} L{p1[0]:.1f},{y:.1f}"), (p0[0] + p1[0]) / 2, y


def node_svg(n):
    r = 9 if n.kind == "compute" else 3
    dash = ' stroke-dasharray="5 4"' if n.kind == "domain" else ""
    out = [f'<rect x="{n.x:.1f}" y="{n.y:.1f}" width="{n.w:.1f}" height="{n.h:.1f}" rx="{r}" '
           f'fill="none" stroke="{INK}" stroke-opacity="0.45"{dash}/>']
    ty = n.y + PAD + FONT
    out.append(f'<text x="{n.x + n.w / 2:.1f}" y="{ty:.1f}" text-anchor="middle" '
               f'font-size="{FONT + 2}" font-weight="600">{esc(n.title)}</text>')
    for i, line in enumerate(n.lines):
        out.append(f'<text x="{n.x + n.w / 2:.1f}" y="{ty + (i + 1) * (FONT + 4):.1f}" '
                   f'text-anchor="middle" font-size="{FONT}" fill="{INK}" '
                   f'fill-opacity="0.72">{esc(line)}</text>')
    return "".join(out)


def legend(spec, y):
    sc = spec["scale"]
    rows = []
    rows.append([f'<text x="28" y="{y:.1f}" font-size="{FONT}" font-weight="600">粗细</text>',
                 f'<text x="76" y="{y:.1f}" font-size="{FONT - 1}" fill-opacity="0.7">'
                 f'{sc["base_px"]:.0f} + {sc["px_per_decade"]}×log10(GB/s)，'
                 f'对数量表：读数用数字，粗细只给量级</text>'])
    ticks = []
    x = 76
    for bw in sc.get("ticks", [1, 10, 100, 1000]):
        w = stroke_w(bw, sc)
        ticks.append(f'<line x1="{x:.1f}" y1="{y + 24:.1f}" x2="{x + 44:.1f}" y2="{y + 24:.1f}" '
                     f'stroke="{INK}" stroke-width="{w:.1f}"/>')
        ticks.append(f'<text x="{x + 50:.1f}" y="{y + 28:.1f}" font-size="{FONT - 1}" '
                     f'fill-opacity="0.7">{bw}</text>')
        x += 58 + text_w(str(bw)) + 30
    rows.append(ticks)
    y2 = y + 52
    items = [f'<text x="28" y="{y2:.1f}" font-size="{FONT - 1}" fill-opacity="0.7">证据</text>']
    x = 76
    for dash, label in [("", "实测"), ("6 4", "标称"), ("2 3", "推算")]:
        items.append(f'<line x1="{x}" y1="{y2 - 4:.1f}" x2="{x + 30}" y2="{y2 - 4:.1f}" '
                     f'stroke="{INK}" stroke-width="3" stroke-dasharray="{dash}"/>')
        items.append(f'<text x="{x + 36}" y="{y2:.1f}" font-size="{FONT - 1}" '
                     f'fill-opacity="0.7">{label}</text>')
        x += 30 + text_w(label) + 26
    x += 14
    items.append(f'<line x1="{x}" y1="{y2 - 4:.1f}" x2="{x + 30}" y2="{y2 - 4:.1f}" '
                 f'stroke="{ACCENT}" stroke-width="7"/>')
    items.append(f'<text x="{x + 36}" y="{y2:.1f}" font-size="{FONT - 1}" '
                 f'fill-opacity="0.7">U ≥ 60%，本次负载的绑定项</text>')
    rows.append(items)
    y3 = y2 + 24
    rows.append([f'<text x="28" y="{y3:.1f}" font-size="{FONT - 1}" fill-opacity="0.7">'
                 f'箭头：单头 = 单工，双头 = 全双工；线宽取双向的较小值</text>'])
    return "".join("".join(r) for r in rows), y3 + 16


def render(spec):
    horizontal = "col" in (spec.get("nodes") or [{}])[0]
    nodes = {s["id"]: Node(s) for s in spec["nodes"]}
    scale = spec["scale"]
    W = spec["width"]
    margin = spec.get("margin", 28)
    gap = spec.get("group_gap", GROUP_GAP)

    # a fan needs enough node edge to land its lanes on
    groups = {}
    for lk in spec["links"]:
        groups.setdefault(tuple(sorted([lk["a"], lk["b"]])), []).append(lk)
    for (ka, kb), lks in groups.items():
        if len(lks) > 1:
            need = len(lks) * 26 + 60
            if horizontal:
                for k in {ka, kb}:
                    nodes[k].h = max(nodes[k].h, need)
            else:
                for k in {ka, kb}:
                    nodes[k].w = max(nodes[k].w, need)

    content_end = place(nodes, horizontal, W, margin, gap)

    body, markers = [], {}
    for (ka, kb), lks in groups.items():
        a, b = nodes[ka], nodes[kb]
        count = len(lks)
        for i, lk in enumerate(lks):
            # perpendicular lane so a fan does not overprint itself
            if count > 1:
                span = (min(a.h, b.h) if horizontal else min(a.w, b.w)) * 0.8
                step = span / count
                lane = (a.y + a.h / 2 if horizontal else a.x + a.w / 2) + (i - (count - 1) / 2) * step
            else:
                lane = None
            p0, p1 = edge_points(a, b, horizontal)
            d, lx, ly = path_for(p0, p1, horizontal, lane)
            w = stroke_w(lk["bw"], scale)
            u = lk.get("duty")
            bind = u is not None and u >= 0.6
            colour = ACCENT if bind else INK
            dash = {"measured": "", "spec": "6 4", "derived": "2 3"}[lk.get("evidence", "measured")]
            heads = {"one": "end", "both": "end start", "asym": "end start"}[lk.get("dir", "one")]
            attrs = [f'd="{d}"', f'stroke="{colour}"', f'stroke-opacity="{0.95 if bind else 0.62}"',
                     f'stroke-width="{w:.1f}"', 'fill="none"', 'stroke-linejoin="round"']
            if dash:
                attrs.append(f'stroke-dasharray="{dash}"')
            mid = marker_id(colour, int(round(w)))
            markers.setdefault((colour, int(round(w))), None)
            for h in heads.split():
                attrs.append(f'marker-{h}="url(#{mid})"')
            body.append(f'<path {" ".join(attrs)}/>')

            label = lk.get("label") or f'{lk["bw"]:g} GB/s'
            if u is not None:
                label += f' · U {u * 100:.0f}%'
            tx, ty = lx + w / 2 + 10, ly
            if horizontal:
                tx, ty = (p0[0] + p1[0]) / 2 - text_w(label) / 2, ly - w / 2 - 6
            body.append(f'<text x="{tx:.1f}" y="{ty + 4:.1f}" font-size="{FONT}" '
                       f'fill="{colour}" fill-opacity="{0.95 if bind else 0.8}">'
                       f'{esc(label)}</text>')
            if lk.get("note"):
                body.append(f'<text x="{tx:.1f}" y="{ty + 20:.1f}" font-size="{FONT - 2}" '
                            f'fill="{INK}" fill-opacity="0.55">{esc(lk["note"])}</text>')

    body += [node_svg(n) for n in nodes.values()]
    leg, bottom = legend(spec, content_end + 26)

    title = (f'<text x="{W / 2:.1f}" y="26" text-anchor="middle" font-size="{FONT + 5}" '
             f'font-weight="700">{esc(spec.get("title", ""))}</text>')
    sub = ""
    if spec.get("subtitle"):
        sub = (f'<text x="{W / 2:.1f}" y="46" text-anchor="middle" font-size="{FONT}" '
               f'fill-opacity="0.65">{esc(spec["subtitle"])}</text>')

    H = bottom
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H:.0f}" width="{W}" '
            f'height="{H:.0f}" font-family="system-ui, -apple-system, Segoe UI, sans-serif" '
            f'color="{INK}"><defs>{"".join(marker(*k) for k in markers)}</defs>{title}{sub}'
            f'{"".join(body)}{leg}</svg>')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    svg = render(spec)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(svg, encoding="utf-8")
        print(f'{sys.argv[2]}: {len(svg)} bytes')
    else:
        sys.stdout.write(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
