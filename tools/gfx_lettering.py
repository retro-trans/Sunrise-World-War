"""Compose exact English sprite labels from the two ImageGen lettering sheets."""

from functools import lru_cache
from pathlib import Path
from statistics import median

import numpy as np
from PIL import Image, ImageFilter


ATLAS_DIR = Path(__file__).resolve().parents[1] / 'work/translation/gfx'
UPPER = ('ABCDEF', 'GHIJKL', 'MNOPQR', 'STUVWX', 'YZ0123', '456789')
LOWER = ('abcdef', 'ghijkl', 'mnopqr', 'stuvwx', "yz!'()", '-./>01')
BASELINES = ('abcdef', 'hikl', 'mnor', 'stuvwx', 'z!', '.01')
OVERSAMPLE = 4


def spans(projection):
    """Return the occupied ranges separated by blank rows or columns."""
    edges = np.flatnonzero(np.diff(np.r_[False, projection, False]))
    return list(zip(edges[::2], edges[1::2]))


def read_atlas(path, rows, baselines):
    with Image.open(path) as image:
        gray = np.asarray(image.convert('L'))
    ink = gray >= 128
    row_spans = spans(ink.any(axis=1))
    if len(row_spans) != len(rows):
        raise ValueError(f'{path.name}: expected {len(rows)} glyph rows, got {len(row_spans)}')
    glyphs = {}
    for (top, bottom), letters, anchors in zip(row_spans, rows, baselines):
        columns = spans(ink[top:bottom].any(axis=0))
        if len(columns) != len(letters):
            raise ValueError(f'{path.name}: expected {len(letters)} glyphs in {letters}')
        row = {}
        for (left, right), letter in zip(columns, letters):
            ys = np.flatnonzero(ink[top:bottom, left:right].any(axis=1)) + top
            y0, y1 = int(ys[0]), int(ys[-1]) + 1
            pixels = gray[y0:y1, left:right].astype(np.int32)
            mask = Image.fromarray(((pixels - 64) * 255 // 128).clip(0, 255).astype(np.uint8))
            row[letter] = mask, y0, y1
        baseline = round(median(row[c][2] for c in anchors))
        glyphs.update({c: (mask, y0 - baseline) for c, (mask, y0, _) in row.items()})
    return glyphs


@lru_cache(maxsize=1)
def load():
    upper = read_atlas(ATLAS_DIR / 'uppercase.png', UPPER, UPPER)
    lower = read_atlas(ATLAS_DIR / 'lowercase.png', LOWER, BASELINES)
    upper_cap = median(upper[c][0].height for c in 'ABEHIKLM')
    lower_cap = median(lower[c][0].height for c in 'bdfhkl')
    return {**{c: (mask, y, lower_cap) for c, (mask, y) in lower.items()},
            **{c: (mask, y, upper_cap) for c, (mask, y) in upper.items()}}


@lru_cache(maxsize=4096)
def line_mask(text, size):
    cap = size * 0.75 * OVERSAMPLE
    x = 0
    top = bottom = 0
    placed = []
    glyphs = load()
    for c in text:
        if c == ' ':
            x += round(cap * 0.37)
            continue
        mask, y, source_cap = glyphs[c]
        scale = cap / source_cap
        mask = mask.resize((max(1, round(mask.width * scale)),
                            max(1, round(mask.height * scale))), Image.Resampling.LANCZOS)
        y = round(y * scale)
        placed.append((mask, x, y))
        top = min(top, y)
        bottom = max(bottom, y + mask.height)
        x += mask.width + max(1, round(cap * 0.10))
    width = max((x + mask.width for mask, x, _ in placed), default=1)
    line = Image.new('L', (width, max(1, bottom - top)))
    for mask, x, y in placed:
        line.paste(mask, (x, y - top))
    return line


def render_line(text, size, fill, stroke, stroke_width):
    glyphs = line_mask(text, size)
    margin = (stroke_width + 1) * OVERSAMPLE
    width = (glyphs.width + OVERSAMPLE - 1) // OVERSAMPLE + 2 * (stroke_width + 1)
    height = (glyphs.height + OVERSAMPLE - 1) // OVERSAMPLE + 2 * (stroke_width + 1)
    alpha = Image.new('L', (width * OVERSAMPLE, height * OVERSAMPLE))
    alpha.paste(glyphs, (margin, margin))
    image = Image.new('RGBA', alpha.size, tuple(stroke) + (0,))
    if stroke_width:
        image.putalpha(alpha.filter(ImageFilter.MaxFilter(2 * stroke_width * OVERSAMPLE + 1)))
    foreground = Image.new('RGBA', alpha.size, tuple(fill) + (0,))
    foreground.putalpha(alpha)
    image.alpha_composite(foreground)
    return image.resize((width, height), Image.Resampling.LANCZOS)
