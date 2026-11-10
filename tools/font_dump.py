"""Render the game's ROM font glyph sets (pack 0002) to PNGs in work/ui/font/."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from packs import members
from PIL import Image

PACK = 'work/source/RESOURCE/0002_0002.bin'

def res(rid):
    d = open(PACK, 'rb').read()
    for m in members(d):
        if m['rid'] == rid:
            return d[m['off']:m['off'] + m['size']]
    raise KeyError(rid)

def glyphs4(data, w, h, n):
    bpg = w * h // 2
    out = []
    for g in range(n):
        b = data[g * bpg:(g + 1) * bpg]
        px = [(b[k // 2] >> (4 * (k & 1))) & 15 for k in range(w * h)]
        out.append(px)
    return out

def sheet(gl, w, h, cols, path, scale=3):
    rows = (len(gl) + cols - 1) // cols
    img = Image.new('L', (cols * (w + 1), rows * (h + 1)), 40)
    p = img.load()
    for i, g in enumerate(gl):
        ox, oy = (i % cols) * (w + 1), (i // cols) * (h + 1)
        for k, v in enumerate(g):
            p[ox + k % w, oy + k // w] = 60 + v * 13 if v else 0
    img.resize((img.width * scale, img.height * scale), Image.NEAREST).save(path)

if __name__ == '__main__':
    a26 = res(0x2858)
    sheet(glyphs4(a26, 12, 24, 96), 12, 24, 16, 'work/ui/font/ascii26.png')
    k26 = res(0x285f)
    sheet(glyphs4(k26, 12, 24, 64), 12, 24, 16, 'work/ui/font/kana26_halfwidth.png')
    a22 = res(0x2855)
    print('22px ascii bytes', len(a22), len(a22) / 96)
    import collections
    print('26 ascii nibble histogram', sorted(collections.Counter(v for g in glyphs4(a26, 12, 24, 96) for v in g).items()))
