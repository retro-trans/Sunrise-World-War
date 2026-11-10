"""Render proportional ASCII glyphs in the game's 4bpp ROM-font style.

Pixel values: 0 transparent, 1-3 partial coverage, 4 full ink (the original glyphs use
the same 0..4 range; the window palette maps them). Ink is left-aligned at column 0;
the advance is ink width + GAP. Cells: 26px font 12x24 (baseline row 20), 22px font
10x20 (baseline row 16). Space advance is set explicitly.

usage: py -3.11 tools/fontgen.py preview   -> work/ui/font/vwf_preview.png
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = r'C:\Windows\Fonts\NotoSansJP-VF.ttf'
# cell: (w, h, pixel size, baseline row, weight, gap, space advance)
STYLE = {
    26: dict(w=12, h=24, size=21, baseline=20, weight=560, gap=1, space=5),
    22: dict(w=10, h=20, size=17, baseline=16, weight=560, gap=1, space=4),
}
S = 8  # supersampling


def _font(size, weight):
    f = ImageFont.truetype(FONT_PATH, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


def render_glyph(ch, kind, squeeze=1.0):
    """Wide glyphs (W, M, %, @...) are condensed horizontally to fit the cell."""
    st = STYLE[kind]; w, h = st['w'], st['h']
    big = _font(st['size'] * S, st['weight'])
    W = w * 3
    img = Image.new('L', (W * S, h * S), 0)
    ImageDraw.Draw(img).text((w * S, st['baseline'] * S), ch, font=big, fill=255, anchor='ls')
    if squeeze != 1.0:
        img = img.resize((int(W * S * squeeze), h * S), Image.LANCZOS)
        pad = Image.new('L', (W * S, h * S), 0); pad.paste(img, (0, 0)); img = pad
    cov = img.resize((W, h), Image.BOX).load()
    vals = [[0] * W for _ in range(h)]
    for y in range(h):
        for x in range(W):
            c = cov[x, y] / 255.0
            vals[y][x] = 0 if c < 0.12 else 1 if c < 0.35 else 2 if c < 0.58 else 3 if c < 0.8 else 4
    cols = [x for x in range(W) if any(vals[y][x] for y in range(h))]
    if not cols:
        return [0] * (w * h), 0
    left, right = cols[0], cols[-1]
    ink = right - left + 1
    if ink > w:
        if squeeze < 0.5:
            raise ValueError('glyph %r too wide (%d > %d)' % (ch, ink, w))
        return render_glyph(ch, kind, squeeze * (w - 0.5) / ink)
    out = [0] * (w * h)
    for y in range(h):
        for x in range(ink):
            out[y * w + x] = vals[y][left + x]
    return out, ink


def pack4(vals):
    b = bytearray(len(vals) // 2)
    for k, v in enumerate(vals):
        b[k // 2] |= v << (4 * (k & 1))
    return bytes(b)


def build(kind, count):
    """Return (glyph bytes for codes 0x20.., advances list) for `count` codes."""
    st = STYLE[kind]
    data = bytearray(); adv = []
    for c in range(0x20, 0x20 + count):
        if c == 0x20:
            vals, ink = [0] * (st['w'] * st['h']), 0
            a = st['space']
        elif c < 0x7F:
            vals, ink = render_glyph(chr(c), kind)
            a = ink + st['gap']
        else:
            vals, a = [0] * (st['w'] * st['h']), st['w'] + st['gap']
        data += pack4(vals); adv.append(a)
    return bytes(data), adv


def preview(lines, out='work/ui/font/vwf_preview.png', scale=2):
    imgs = []
    for kind in (26, 22):
        st = STYLE[kind]; w, h = st['w'], st['h']
        data, adv = build(kind, 96)
        Wd = 640
        img = Image.new('RGB', (Wd, h * len(lines) + 6), (30, 40, 90))
        px = img.load()
        for li, line in enumerate(lines):
            x = 6
            for ch in line:
                c = ord(ch) - 0x20
                g = data[c * w * h // 2:(c + 1) * w * h // 2]
                for k in range(w * h):
                    v = (g[k // 2] >> (4 * (k & 1))) & 15
                    if v and x + k % w < Wd:
                        lv = 255 * v // 4
                        px[x + k % w, 3 + li * h + k // w] = (lv, lv, lv)
                x += adv[c] + 2   # +2: typical window font spacing (assumed)
            print(kind, '%3d px' % (x - 6), line)
        imgs.append(img)
    full = Image.new('RGB', (640, sum(i.height for i in imgs)))
    y = 0
    for i in imgs:
        full.paste(i, (0, y)); y += i.height
    full.resize((full.width * scale, full.height * scale), Image.NEAREST).save(out)


if __name__ == '__main__':
    preview(["Kanji! We've got to hurry to the hangar, now!",
             "The Impulse 7's cloud system checks out fine.",
             "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789 (100%)",
             "abcdefghijklmnopqrstuvwxyz \"quote\" it's... -?!"])
