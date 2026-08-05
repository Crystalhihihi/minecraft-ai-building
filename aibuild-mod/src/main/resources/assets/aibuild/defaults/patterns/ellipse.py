#!/usr/bin/env python3
"""ellipse.py — shared circle/ellipse rasterization (共用圆/椭圆栅格化).

Single source of truth for curved-plan generators. round_plan / dome /
rose_window MUST all reuse this module — 禁止各写一份 (contract from the
card-authoring brief). Pure functions, no I/O.

- circle_ring(r): single-cell-width connected ring of radius r (midpoint
  circle / Bresenham), returned as [(x, z), ...] sorted, relative to (0,0).
- ellipse_ring(rx, rz): elliptical ring (parametric sampling), relative to
  (0,0).
- disc(rx, rz): filled (solid) ellipse.

All coordinates are relative offsets; the caller adds its own origin.
"""
import math

DIRS8 = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def circle_ring(r, cx=0, cz=0):
    """Single-cell-width connected ring at integer radius r (r >= 1).

    Midpoint (Bresenham) circle: produces a connected, hole-free ring — the
    standard for MC round walls / roofs. Returns sorted [(x,z), ...].
    """
    r = max(1, int(round(r)))
    pts = set()
    x, y = r, 0
    err = 1 - r
    while x >= y:
        for px, pz in ((x, y), (y, x), (-y, x), (-x, y),
                       (-x, -y), (-y, -x), (y, -x), (x, -y)):
            pts.add((cx + px, cz + pz))
        y += 1
        if err < 0:
            err += 2 * y + 1
        else:
            x -= 1
            err += 2 * (y - x) + 1
    return sorted(pts)


def ellipse_ring(rx, rz, cx=0, cz=0):
    """Elliptical ring via parametric sampling. rx/rz >= 1.

    Sample count scales with the larger radius so large rings stay dense;
    returns a connected-looking set (may have 1-cell gaps for extreme aspect
    ratios — acceptable for organic/curved MC forms). Sorted [(x,z), ...].
    """
    rx, rz = max(1, int(round(rx))), max(1, int(round(rz)))
    pts = set()
    n = max(16, int(4 * math.pi * max(rx, rz)))
    for i in range(n):
        a = 2 * math.pi * i / n
        pts.add((cx + int(round(rx * math.cos(a))),
                 cz + int(round(rz * math.sin(a)))))
    return sorted(pts)


def disc(rx, rz, cx=0, cz=0):
    """Filled (solid) ellipse. rx/rz >= 1. Sorted [(x,z), ...]."""
    rx, rz = max(1, int(round(rx))), max(1, int(round(rz)))
    pts = set()
    for dx in range(-rx, rx + 1):
        for dz in range(-rz, rz + 1):
            if (dx / rx) ** 2 + (dz / rz) ** 2 <= 1.0:
                pts.add((cx + dx, cz + dz))
    return sorted(pts)


def rim_offsets(r):
    """Radius deltas for a tapered stack: [r, r-1, ..., 1] given base r."""
    return [max(1, r - i) for i in range(max(0, r))]
