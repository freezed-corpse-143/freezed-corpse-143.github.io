#!/usr/bin/env python3
"""Render an L1 resource-constraint map (environment profile) as SVG from a JSON spec.

    python tools/envmap.py tools/envmaps/rtx3080.json out.svg

The value is the encoding, not the drawing. Four quantities share one picture, each on
its own channel, so a reader sees capability, evidence grade and the binding edge
without a paragraph of prose:

  edge thickness  ~ sustained bandwidth, LOG scale, fixed px per decade (legend shows real ticks)
  edge arrowheads ~ direction: one head = simplex, both = duplex
  edge dash       ~ evidence: solid = measured on this machine, dashed = spec sheet,
                    dotted = derived / estimated
  edge colour     ~ utilisation U = demand / capability for the target workload
                    (neutral below 60 %, amber at or above = binding)
  node shape      ~ kind: compute = rounded, memory = square, domain = dashed outline

Every number drawn comes from the spec; the renderer infers nothing.

Spec: a node has "row" (vertical map, the default) or "col" (left-to-right map), a title
and optional detail lines. A link names two nodes and a bandwidth in GB/s, and may carry
evidence, dir, duty (0..1) and notes. Several links between the same pair fan out into
lanes, wide enough that each label lands beside its own line.
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
# The figure is embedded as an <img>, i.e. a standalone SVG document: currentColor
# resolves to black there and disappears on a dark theme, and an <img> cannot see the
# page's theme toggle. So the figure carries its own paper, matched to the site's
# light background: invisible in light mode, a legible card in dark mode.
PAPER = "#faf8f8"
INK = "#2b2b2b"
ACCENT = "#b45309"


def text_w(s, size=FONT):
    """Advance width estimate: CJK is full-width, the rest monospace-ish."""
    return sum(CJK_ADV if ord(c) > 0x2E80 else MONO_ADV for c in s) * size / FONT


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def stroke_w(bw, scale):
    """Log scale: DRAM and PCIe differ by 60x, linear would erase everything below DRAM."""
    w = scale["base_px"] + scale["px_per_decade"] * math.log10(max(bw, 0.1))
    return max(scale["min_px"], min(scale["max_px"], w))


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
    """Groups lie along one axis: rows stack vertically, columns stack horizontally.
    Members of a group are centred on the other axis. Returns the content's end."""
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
    cross_total = sum(bands.values()) + gap * (len(keys) - 1)
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


def ports(a, b, horizontal):
    """The port on a facing b, and on b facing a."""
    if horizontal:
        right = b.x >= a.x
        return ((a.x + a.w) if right else a.x, a.y + a.h / 2), \
               (b.x if right else b.x + b.w, b.y + b.h / 2)
    down = b.y >= a.y
    return (a.x + a.w / 2, (a.y + a.h) if down else a.y), \
           (b.x + b.w / 2, b.y if down else b.y + b.h)


def head(p, u, w, colour):
    """Arrowhead as an explicit triangle: markers default to strokeWidth units and
    their orientation is one more thing to get wrong."""
    L, hw = max(12.0, w * 1.5), max(6.0, w * 0.9)
    ax, ay = p[0] + u[0] * 1.5, p[1] + u[1] * 1.5
    bx, by = p[0] - u[0] * L, p[1] - u[1] * L
    px, py = -u[1], u[0]
    return (f'<path d="M{ax:.1f},{ay:.1f} L{bx + px * hw:.1f},{by + py * hw:.1f} '
            f'L{bx - px * hw:.1f},{by - py * hw:.1f} Z" fill="{colour}"/>')


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
                   f'fill-opacity="0.78">{esc(line)}</text>')
    return "".join(out)


def legend(spec, y):
    """The scale claim has to be checkable, so the ticks are drawn at the real widths."""
    sc = spec["scale"]
    out = [f'<text x="28" y="{y:.1f}" font-size="{FONT}" font-weight="600">粗细</text>',
           f'<text x="76" y="{y:.1f}" font-size="{FONT - 1}" fill-opacity="0.7">'
           f'{sc["base_px"]:.0f} + {sc["px_per_decade"]}×log10(GB/s)，对数量表：'
           f'读数用数字，粗细只给量级</text>']
    x = 76
    for bw in sc.get("ticks", [1, 10, 100, 1000]):
        w = stroke_w(bw, sc)
        out.append(f'<text x="{x + 22:.1f}" y="{y + 16:.1f}" text-anchor="middle" '
                   f'font-size="{FONT - 1}" fill-opacity="0.7">{bw}</text>')
        out.append(f'<line x1="{x:.1f}" y1="{y + 26:.1f}" x2="{x + 44:.1f}" '
                   f'y2="{y + 26:.1f}" stroke="{INK}" stroke-width="{w:.1f}"/>')
        x += 44 + max(26.0, text_w(str(bw)) + 30)
    y2 = y + 66
    out.append(f'<text x="28" y="{y2:.1f}" font-size="{FONT - 1}" fill-opacity="0.7">证据</text>')
    x = 76
    for dash, label in [("", "实测"), ("6 4", "标称"), ("2 3", "推算")]:
        out.append(f'<line x1="{x}" y1="{y2 - 4:.1f}" x2="{x + 30}" y2="{y2 - 4:.1f}" '
                   f'stroke="{INK}" stroke-width="3" stroke-dasharray="{dash}"/>')
        out.append(f'<text x="{x + 36}" y="{y2:.1f}" font-size="{FONT - 1}" '
                   f'fill-opacity="0.7">{label}</text>')
        x += 30 + text_w(label) + 26
    x += 14
    out.append(f'<line x1="{x}" y1="{y2 - 4:.1f}" x2="{x + 30}" y2="{y2 - 4:.1f}" '
               f'stroke="{ACCENT}" stroke-width="7"/>')
    out.append(f'<text x="{x + 36}" y="{y2:.1f}" font-size="{FONT - 1}" '
               f'fill-opacity="0.7">U ≥ 60%，本次负载的绑定项</text>')
    y3 = y2 + 26
    out.append(f'<text x="28" y="{y3:.1f}" font-size="{FONT - 1}" fill-opacity="0.7">'
               f'箭头：单头 = 单工，双头 = 全双工，双向链路的粗细取较小的一侧；'
               f'虚框 = 域外或共享资源，不计入本卡预算</text>')
    return "".join(out), y3 + 16


def render(spec):
    horizontal = "col" in (spec.get("nodes") or [{}])[0]
    nodes = {s["id"]: Node(s) for s in spec["nodes"]}
    scale = spec["scale"]
    W, margin = spec["width"], spec.get("margin", 28)
    gap = spec.get("group_gap", GROUP_GAP)

    groups = {}
    for lk in spec["links"]:
        groups.setdefault(tuple(sorted([lk["a"], lk["b"]])), []).append(lk)
    for (ka, kb), lks in groups.items():  # room for one lane per link
        if len(lks) > 1:
            need = len(lks) * 26 + 60
            for k in {ka, kb}:
                if horizontal:
                    nodes[k].h = max(nodes[k].h, need)
                else:
                    nodes[k].w = max(nodes[k].w, need)

    content_end = place(nodes, horizontal, W, margin, gap)
    body = []
    for (ka, kb), lks in groups.items():
        a, b = nodes[ka], nodes[kb]
        count = len(lks)
        for i, lk in enumerate(lks):
            lane = None
            if count > 1:
                span = (min(a.h, b.h) if horizontal else min(a.w, b.w)) * 0.8
                centre = (a.y + a.h / 2) if horizontal else (a.x + a.w / 2)
                lane = centre + (i - (count - 1) / 2) * span / count
            p0, p1 = ports(a, b, horizontal)
            w = stroke_w(lk["bw"], scale)
            u = lk.get("duty")
            bind = u is not None and u >= 0.6
            colour = ACCENT if bind else INK
            if horizontal:
                y = lane if lane is not None else (p0[1] + p1[1]) / 2
                d, lx, ly = f"M{p0[0]:.1f},{y:.1f} L{p1[0]:.1f},{y:.1f}", \
                    (p0[0] + p1[0]) / 2, y
            else:
                x = lane if lane is not None else (p0[0] + p1[0]) / 2
                d, lx, ly = f"M{x:.1f},{p0[1]:.1f} L{x:.1f},{p1[1]:.1f}", x, (p0[1] + p1[1]) / 2
            dash = {"measured": "", "spec": "6 4", "derived": "2 3"}[lk.get("evidence", "measured")]
            attrs = [f'd="{d}"', f'stroke="{colour}"', f'stroke-opacity="{1 if bind else 0.8}"',
                     f'stroke-width="{w:.1f}"', 'fill="none"']
            if dash:
                attrs.append(f'stroke-dasharray="{dash}"')
            body.append(f'<path {" ".join(attrs)}/>')

            length = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) or 1.0
            u_ab = ((p1[0] - p0[0]) / length, (p1[1] - p0[1]) / length)
            want = {"one": (False, True), "both": (True, True),
                    "asym": (True, True)}[lk.get("dir", "one")]
            for at_start, at_end in [want]:
                if at_end:
                    body.append(head(p1, u_ab, w, colour))
                if at_start:
                    body.append(head(p0, (-u_ab[0], -u_ab[1]), w, colour))

            label = lk.get("label") or f'{lk["bw"]:g} GB/s'
            if u is not None:
                label += f' · U {u * 100:.0f}%'
            if horizontal:
                side = -1 if count == 1 or i % 2 == 0 else 1
                tx = lx - text_w(label) / 2
                ty = ly + side * (w / 2 + 9) + (0 if side < 0 else FONT)
                body.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="{FONT}" '
                            f'fill="{colour}" fill-opacity="{1 if bind else 0.9}">'
                            f'{esc(label)}</text>')
                if lk.get("note"):
                    ny = ly + side * (w / 2 + 23) + (0 if side < 0 else FONT)
                    body.append(f'<text x="{lx - text_w(lk["note"]) / 2:.1f}" y="{ny:.1f}" '
                                f'font-size="{FONT - 2}" fill="{INK}" fill-opacity="0.55">'
                                f'{esc(lk["note"])}</text>')
            else:
                tx = lx + w / 2 + 10
                body.append(f'<text x="{tx:.1f}" y="{ly - 3:.1f}" font-size="{FONT}" '
                            f'fill="{colour}" fill-opacity="{1 if bind else 0.9}">'
                            f'{esc(label)}</text>')
                if lk.get("note"):
                    body.append(f'<text x="{tx:.1f}" y="{ly + 13:.1f}" font-size="{FONT - 2}" '
                                f'fill="{INK}" fill-opacity="0.6">{esc(lk["note"])}</text>')

    body += [node_svg(n) for n in nodes.values()]
    leg, bottom = legend(spec, content_end + 26)

    title = (f'<text x="{W / 2:.1f}" y="26" text-anchor="middle" font-size="{FONT + 5}" '
             f'font-weight="700">{esc(spec.get("title", ""))}</text>')
    sub = ""
    if spec.get("subtitle"):
        sub = (f'<text x="{W / 2:.1f}" y="46" text-anchor="middle" font-size="{FONT}" '
               f'fill-opacity="0.7">{esc(spec["subtitle"])}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {bottom:.0f}" '
            f'width="{W}" height="{bottom:.0f}" font-family="system-ui, -apple-system, '
            f'Segoe UI, sans-serif" color="{INK}" role="img">'
            f'<rect width="{W}" height="{bottom:.0f}" fill="{spec.get("paper", PAPER)}"/>'
            f'<title>{esc(spec.get("title", ""))}</title>'
            f'<desc>{esc(spec.get("subtitle", ""))}</desc>'
            f'{title}{sub}{"".join(body)}{leg}</svg>')


def check(svg, spec):
    """Fail loudly on the defects this renderer produced while it was being written:
    overlapping text, text outside the canvas, and width not monotone in bandwidth.
    Geometry only, no vision needed."""
    import re
    W = spec["width"]
    H = float(re.search(r'height="(\d+)"', svg).group(1))
    boxes = []
    for m in re.finditer(r'<text x="([-\d.]+)" y="([-\d.]+)"([^>]*)>([^<]*)</text>', svg):
        x, y, attrs, raw = float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
        size = float(re.search(r'font-size="([\d.]+)"', attrs).group(1))
        w = text_w(raw, size)
        if 'text-anchor="middle"' in attrs:
            x -= w / 2
        boxes.append((x, y - size * 0.85, x + w, y + size * 0.25, raw))
    bad = []
    for i, a in enumerate(boxes):
        if a[0] < 0 or a[2] > W + 1 or a[1] < 0 or a[3] > H:
            bad.append(f"outside canvas: {a[4]!r} ({a[0]:.0f}..{a[2]:.0f} x {a[1]:.0f}..{a[3]:.0f})")
        for b in boxes[i + 1:]:
            dx = min(a[2], b[2]) - max(a[0], b[0])
            dy = min(a[3], b[3]) - max(a[1], b[1])
            if dx > 1.5 and dy > 1.5:
                bad.append(f"text overlap: {a[4]!r} / {b[4]!r}")
    ws = sorted((lk["bw"], stroke_w(lk["bw"], spec["scale"])) for lk in spec["links"])
    for (b1, w1), (b2, w2) in zip(ws, ws[1:]):
        if w2 < w1 - 0.01:
            bad.append(f"width not monotone: {b1:g} -> {b2:g} GB/s")
    if bad:
        raise SystemExit("\n".join(bad))
    return len(boxes)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    spec = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    svg = render(spec)
    n = check(svg, spec)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(svg, encoding="utf-8")
        print(f'{sys.argv[2]}: {len(svg)} bytes, {n} labels, no overlap')
    else:
        sys.stdout.write(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
