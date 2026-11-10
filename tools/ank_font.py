"""Replace the ASCII glyphs of the 10x14 ANK font (unit / pilot / weapon / skill lists,
battle panel labels such as "FT" / "Lv36").

Font: Get10x14FontAddr, 0x250F78, 70 bytes per glyph from 0x20, 4bpp, 5 bytes per row,
high nibble = left pixel (as PutIdx8TextureFont10x14Ank reads it). Levels: 0 clear,
1 outline, 2 shade, 3 stroke. The original Latin letters are a squared 1-pixel design that
reads poorly in English (A, t, l). New glyphs keep the original style and metrics:
Lucida Console 13 px (monospace, aliased) drawn bold (2-pixel vertical strokes), cap
height rows 2-10 with the baseline on row 10, descenders below, then a drop shadow
(level 2, right/below) and a 1-pixel outline.
Keeping the original height matters: the battle panel clips anything below row 11.

  py -3.11 tools/ank_font.py preview OUT.png
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

F14 = 0x250F78
FIRST, LAST = 0x20, 0x7F        # ASCII only; half-width kana (0xA1-) keep their glyphs
VA_TO_FILE = 0xFF000
FONT, SIZE, BASE = r'C:\Windows\Fonts\lucon.ttf', 13, 10      # BASE = baseline row


def glyph(ch):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(FONT, SIZE)
    cap = f.getbbox('H')
    im = Image.new('1', (30, 30), 0)
    d = ImageDraw.Draw(im); d.fontmode = '1'
    d.text((10, 10 - cap[1]), chr(ch), font=f, fill=1)          # cap top lands on y = 10
    d.text((11, 10 - cap[1]), chr(ch), font=f, fill=1)          # 2-pixel vertical strokes (bold)
    px = im.load()
    pts = [(x, y) for y in range(30) for x in range(30) if px[x, y]]
    g = [[0] * 10 for _ in range(14)]
    if pts:
        x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts)
        dx = (10 - (x1 - x0 + 1)) // 2 - x0
        dy = (BASE + 1 - (cap[3] - cap[1])) - 10
        for x, y in pts:
            if 0 <= x + dx < 10 and 0 <= y + dy < 14:
                g[y + dy][x + dx] = 3
    # drop shadow (2) right / below / diagonal of each stroke pixel, then a 1-pixel outline
    for x, y in [(x, y) for y in range(14) for x in range(10) if g[y][x] == 3]:
        for i, j in ((1, 1), (1, 0), (0, 1)):
            if 0 <= x + i < 10 and 0 <= y + j < 14 and g[y + j][x + i] == 0:
                g[y + j][x + i] = 2
    add = [(x, y) for y in range(14) for x in range(10) if g[y][x] == 0 and
           any(0 <= y + j < 14 and 0 <= x + i < 10 and g[y + j][x + i] >= 2
               for j in (-1, 0, 1) for i in (-1, 0, 1))]
    for x, y in add:
        g[y][x] = 1
    return g


def encode(g):
    return bytes((row[x] << 4) | row[x + 1] for row in g for x in range(0, 10, 2))


# codes the game draws as its own symbols (alpha, up/down triangles, circles, box, cross):
# keep the original glyphs
KEEP = set(b';<>^`{|}~') | {0x5C, 0x7F}


def patches(elf):
    o = F14 - VA_TO_FILE
    data = b''.join(bytes(elf[o + 70 * (ch - 0x20):o + 70 * (ch - 0x1f)]) if ch in KEEP else encode(glyph(ch))
                    for ch in range(FIRST, LAST + 1))
    return [(F14, None, data, 'ANK 10x14 font: ASCII glyphs (Lucida Console 13 bold, drop shadow)')]


def preview(path, scale=4):
    from PIL import Image
    elf = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'work/source/SLPS_252.70'), 'rb').read()
    lv = {0: (30, 40, 90), 1: (10, 10, 20), 2: (120, 120, 140), 3: (235, 235, 235)}
    o = F14 - VA_TO_FILE
    def old(ch):
        b = elf[o + 70 * (ch - 0x20):o + 70 * (ch - 0x1f)]
        return [[(b[y * 5 + x // 2] & 15) if x & 1 else (b[y * 5 + x // 2] >> 4) for x in range(10)] for y in range(14)]
    sh = Image.new('RGB', (16 * 11, 12 * 15), (60, 60, 60))
    for k, ch in enumerate(range(0x20, 0x80)):
        for part, g in enumerate((old(ch), old(ch) if ch in KEEP else glyph(ch))):
            im = Image.new('RGB', (10, 14))
            for y in range(14):
                for x in range(10):
                    im.putpixel((x, y), lv.get(g[y][x], (255, 0, 255)))
            sh.paste(im, ((k % 16) * 11, ((k // 16) * 2 + part) * 15))
    sh.resize((sh.size[0] * scale, sh.size[1] * scale), Image.NEAREST).save(path)


if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        preview(sys.argv[2])
