#!/usr/bin/env python3
"""
pixelgrid.py - render pixel art onto a GitHub-style contribution calendar as SVG.

The core of this is the coordinate mapping: a contribution calendar is a
column-major 7-row grid where column = week index and row = day of week, so a
2D art coordinate (col, row) corresponds to exactly one calendar date:

    date(col, row) = anchor_sunday + (col * 7 + row) days

This renders that mapping to an image. It does not write git history - the art
is a picture of a calendar, not a claim about one.

Usage:
    python3 pixelgrid.py --text "ROH00T" -o art.svg
    python3 pixelgrid.py --grid design.txt -o art.svg
    python3 pixelgrid.py --text "HI" --dates          # print the coord->date map
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta

ROWS = 7           # days per week - the fixed height of a contribution calendar
DEFAULT_COLS = 53  # weeks shown by GitHub

# ---------------------------------------------------------------------------
# 3x5 pixel font. Narrow on purpose: at 3 columns + 1 space per glyph you fit
# ~13 characters across the 53-week span instead of ~8 with a 5-wide font.
# ---------------------------------------------------------------------------
FONT = {
    "A": ["###", "#.#", "###", "#.#", "#.#"],
    "B": ["##.", "#.#", "##.", "#.#", "##."],
    "C": ["###", "#..", "#..", "#..", "###"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "E": ["###", "#..", "##.", "#..", "###"],
    "F": ["###", "#..", "##.", "#..", "#.."],
    "G": ["###", "#..", "#.#", "#.#", "###"],
    "H": ["#.#", "#.#", "###", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "J": ["..#", "..#", "..#", "#.#", "###"],
    "K": ["#.#", "#.#", "##.", "#.#", "#.#"],
    "L": ["#..", "#..", "#..", "#..", "###"],
    "M": ["#.#", "###", "###", "#.#", "#.#"],
    "N": ["#.#", "###", "###", "###", "#.#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"],
    "P": ["###", "#.#", "###", "#..", "#.."],
    "Q": ["###", "#.#", "#.#", "###", "..#"],
    "R": ["###", "#.#", "##.", "#.#", "#.#"],
    "S": ["###", "#..", "###", "..#", "###"],
    "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#.#", "#.#", "###", "###", "#.#"],
    "X": ["#.#", "#.#", ".#.", "#.#", "#.#"],
    "Y": ["#.#", "#.#", ".#.", ".#.", ".#."],
    "Z": ["###", "..#", ".#.", "#..", "###"],
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", "..#", "..#", "..#"],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
    " ": ["..", "..", "..", "..", ".."],
    "-": ["...", "...", "###", "...", "..."],
    ".": ["...", "...", "...", "...", ".#."],
    "!": [".#.", ".#.", ".#.", "...", ".#."],
    "<": ["..#", ".#.", "#..", ".#.", "..#"],
    ">": ["#..", ".#.", "..#", ".#.", "#.."],
    "*": ["#.#", ".#.", "###", ".#.", "#.#"],
    "+": ["...", ".#.", "###", ".#.", "..."],
    "/": ["..#", "..#", ".#.", "#..", "#.."],
}

# GitHub-ish greens, level 0-4, in light and dark flavours.
PALETTE_LIGHT = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
PALETTE_DARK = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


# ---------------------------------------------------------------------------
# Art construction: text or a hand-drawn grid file -> {(col, row): level}
# ---------------------------------------------------------------------------
def text_to_cells(text: str, level: int) -> tuple[dict[tuple[int, int], int], int]:
    """Rasterise text with the 3x5 font. Returns cells keyed by (col, row_in_art)."""
    cells: dict[tuple[int, int], int] = {}
    col = 0
    for ch in text.upper():
        glyph = FONT.get(ch)
        if glyph is None:
            raise SystemExit(f"no glyph for {ch!r}; supported: {''.join(sorted(FONT))}")
        width = len(glyph[0])
        for r, line in enumerate(glyph):
            for c, px in enumerate(line):
                if px == "#":
                    cells[(col + c, r)] = level
        col += width + 1  # one blank column between glyphs
    return cells, max(col - 1, 0)


def grid_to_cells(path: str, level: int) -> tuple[dict[tuple[int, int], int], int]:
    """Read an ASCII design file.

    '.' or ' ' is empty; '#' is a full-intensity cell; digits 1-4 set intensity
    directly, so you can shade the art rather than draw it flat.
    """
    with open(path) as fh:
        lines = [ln.rstrip("\n") for ln in fh if not ln.startswith("//")]
    lines = [ln for ln in lines if ln.strip()]
    cells: dict[tuple[int, int], int] = {}
    for r, line in enumerate(lines):
        for c, px in enumerate(line):
            if px in ".  ":
                continue
            if px == "#":
                cells[(c, r)] = level
            elif px in "01234":
                if px != "0":
                    cells[(c, r)] = int(px)
            else:
                raise SystemExit(f"{path}:{r+1}: unexpected character {px!r}")
    width = max((c for c, _ in cells), default=-1) + 1
    return cells, width


# ---------------------------------------------------------------------------
# The coordinate -> date mapping
# ---------------------------------------------------------------------------
def anchor_sunday(end: date, cols: int) -> date:
    """First cell of the grid: the Sunday that starts the leftmost column.

    The calendar ends on the week containing `end`, so we walk back to that
    week's Sunday and then back (cols - 1) further weeks.
    """
    days_since_sunday = (end.weekday() + 1) % 7  # Python: Mon=0; calendar: Sun=0
    last_col_sunday = end - timedelta(days=days_since_sunday)
    return last_col_sunday - timedelta(weeks=cols - 1)


def cell_date(anchor: date, col: int, row: int) -> date:
    """The whole trick, in one line: columns are weeks, rows are days."""
    return anchor + timedelta(days=col * ROWS + row)


def place(cells, art_width, cols, row_offset, col_offset, center):
    """Position the art inside the 7 x cols calendar, returning placed cells."""
    art_height = max((r for _, r in cells), default=-1) + 1
    if art_height > ROWS:
        raise SystemExit(f"art is {art_height} rows tall; the calendar has {ROWS}")
    if art_width > cols:
        raise SystemExit(f"art is {art_width} columns wide; only {cols} weeks fit")
    if center:
        col_offset = (cols - art_width) // 2
        row_offset = (ROWS - art_height) // 2
    if row_offset + art_height > ROWS:
        raise SystemExit("row-offset pushes the art off the bottom of the calendar")
    if col_offset + art_width > cols:
        raise SystemExit("col-offset pushes the art off the right of the calendar")
    return {(c + col_offset, r + row_offset): lvl for (c, r), lvl in cells.items()}


# ---------------------------------------------------------------------------
# SVG output
# ---------------------------------------------------------------------------
def render_svg(placed, cols, anchor, cell=11, gap=3, pad=4,
               show_labels=True, title="Contribution-grid pixel art") -> str:
    step = cell + gap
    left = 28 if show_labels else pad
    top = 18 if show_labels else pad
    width = left + cols * step + pad
    height = top + ROWS * step + pad

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{title}">',
        f"<title>{title}</title>",
        "<style>",
        "  .bg { fill: #ffffff }",
        "  text { font: 9px ui-monospace, SFMono-Regular, Menlo, monospace; fill: #57606a }",
    ]
    for lvl, colour in enumerate(PALETTE_LIGHT):
        out.append(f"  .l{lvl} {{ fill: {colour} }}")
    out.append("  @media (prefers-color-scheme: dark) {")
    out.append("    .bg { fill: #0d1117 }")
    out.append("    text { fill: #8b949e }")
    for lvl, colour in enumerate(PALETTE_DARK):
        out.append(f"    .l{lvl} {{ fill: {colour} }}")
    out.append("  }")
    out.append("</style>")
    out.append(f'<rect class="bg" width="{width}" height="{height}" rx="6"/>')

    if show_labels:
        seen = set()
        for col in range(cols):
            d = cell_date(anchor, col, 0)
            if d.month not in seen and d.day <= 7:
                seen.add(d.month)
                out.append(f'<text x="{left + col * step}" y="{top - 6}">'
                           f"{MONTHS[d.month - 1]}</text>")
        for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
            y = top + row * step + cell - 2
            out.append(f'<text x="{pad - 2}" y="{y}">{label}</text>')

    for col in range(cols):
        for row in range(ROWS):
            lvl = placed.get((col, row), 0)
            d = cell_date(anchor, col, row)
            x, y = left + col * step, top + row * step
            out.append(
                f'<rect class="l{lvl}" x="{x}" y="{y}" width="{cell}" '
                f'height="{cell}" rx="2"><title>{d.isoformat()}</title></rect>'
            )
    out.append("</svg>")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="string to rasterise with the built-in 3x5 font")
    src.add_argument("--grid", help="ASCII art file ('.'=off, '#'=on, 1-4=intensity)")
    ap.add_argument("-o", "--out", default="pixelgrid.svg", help="output SVG path")
    ap.add_argument("--cols", type=int, default=DEFAULT_COLS, help="weeks wide")
    ap.add_argument("--end", help="last date on the calendar (YYYY-MM-DD, default today)")
    ap.add_argument("--level", type=int, default=4, choices=range(5),
                    help="intensity for '#' cells")
    ap.add_argument("--row-offset", type=int, default=1)
    ap.add_argument("--col-offset", type=int, default=0)
    ap.add_argument("--center", action="store_true", help="centre the art in the grid")
    ap.add_argument("--no-labels", action="store_true")
    ap.add_argument("--cell", type=int, default=11, help="cell size in px")
    ap.add_argument("--dates", action="store_true",
                    help="print the (col,row)->date mapping instead of writing SVG")
    ap.add_argument("--json", action="store_true", help="with --dates, emit JSON")
    args = ap.parse_args()

    end = date.fromisoformat(args.end) if args.end else date.today()
    anchor = anchor_sunday(end, args.cols)

    if args.text:
        cells, art_width = text_to_cells(args.text, args.level)
    else:
        cells, art_width = grid_to_cells(args.grid, args.level)

    placed = place(cells, art_width, args.cols,
                   args.row_offset, args.col_offset, args.center)

    if args.dates:
        rows = [
            {"col": c, "row": r, "level": lvl,
             "date": cell_date(anchor, c, r).isoformat()}
            for (c, r), lvl in sorted(placed.items(), key=lambda kv: (kv[0][0], kv[0][1]))
        ]
        if args.json:
            json.dump(rows, sys.stdout, indent=2)
            print()
        else:
            print(f"anchor Sunday: {anchor}   span: {anchor} .. "
                  f"{cell_date(anchor, args.cols - 1, ROWS - 1)}")
            for r in rows:
                print(f"  ({r['col']:2d},{r['row']}) -> {r['date']}  level {r['level']}")
        return

    svg = render_svg(placed, args.cols, anchor, cell=args.cell,
                     show_labels=not args.no_labels)
    with open(args.out, "w") as fh:
        fh.write(svg)
    print(f"wrote {args.out}  ({len(placed)} lit cells, "
          f"{anchor} .. {cell_date(anchor, args.cols - 1, ROWS - 1)})")


if __name__ == "__main__":
    main()
