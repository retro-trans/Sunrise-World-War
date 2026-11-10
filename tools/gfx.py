"""Textures in RESOURCE packs: P3TL lists of P3TX images (and PAL_ pictures).

P3TL: 'P3TL', 8, count, 0, then `count` P3TX entries back to back.
P3TX: 'P3TX', size (entry = 8 + size bytes), psm (0x13 PSMT8 / 0x14 PSMT4), width, height,
      0, flags, 0; palette (256 / 16 RGBA words, alpha 0x80 = opaque; PSMT8 palettes use the
      GS CSM1 order), then width*height pixels (8 or 4 bits, low nibble first).

  py -3.11 tools/gfx.py png RID OUT_DIR          every P3TX of a member as PNG
  py -3.11 tools/gfx.py info RID
"""
import glob, json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from packs import members

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, 'work/source/RESOURCE')
_IDX = None


def index():
    global _IDX
    if _IDX is None:
        _IDX = json.load(open(os.path.join(ROOT, 'work/source/resource_index.json')))
    return _IDX


def pack_path(fi):
    return glob.glob(os.path.join(RES, f'{fi:04d}_*.bin'))[0]


def member(rid):
    v = index()[str(rid)]
    d = open(pack_path(v['file']), 'rb').read()
    return d[v['off']:v['off'] + v['size']]


def csm1(i):
    """palette index -> position in the CSM1-ordered palette (swap bits 3 and 4)"""
    return (i & ~0x18) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)


def p3tx_list(d):
    """[(offset, psm, w, h, flags)] for a P3TL member"""
    assert d[:4] == b'P3TL', d[:4]
    n = struct.unpack_from('<I', d, 8)[0]
    out = []; pos = 16
    for _ in range(n):
        while d[pos:pos + 4] != b'P3TX':        # entries are padded to 16 bytes
            pos += 4
        size, psm, w, h, _, flags = struct.unpack_from('<6I', d, pos + 4)
        out.append(dict(off=pos, psm=psm, w=w, h=h, flags=flags, size=size))
        pos += 8 + size
    return out


def decode(d, t):
    """RGBA bytes (w*h*4) of one P3TX"""
    w, h, psm = t['w'], t['h'], t['psm']
    o = t['off'] + 0x20
    ncol = 256 if psm == 0x13 else 16
    pal = [d[o + 4 * k:o + 4 * k + 4] for k in range(ncol)]
    if psm == 0x13:
        pal = [pal[csm1(i)] for i in range(256)]
    pal = [bytes((c[0], c[1], c[2], min(255, c[3] * 2))) for c in pal]
    px = o + 4 * ncol
    out = bytearray()
    if psm == 0x13:
        for i in range(w * h):
            out += pal[d[px + i]]
    else:
        for i in range(w * h):
            b = d[px + i // 2]
            out += pal[(b >> 4) if i & 1 else (b & 15)]
    return bytes(out)


def to_png(d, t, path):
    from PIL import Image
    Image.frombytes('RGBA', (t['w'], t['h']), decode(d, t)).save(path)



# ---------------------------------------------------------------------------
# Sprite members: chain of 0x80-byte-header blocks (magic, block size, ...):
#   PAL_ (+0x10 = 0x11, +0x14 w,h of the CLUT: 8x2 = 16 colours, 16x16 = 256)
#   IMG_ (+0x10 type: 1 = 32-bit, 8 = 8-bit, 9 = 4-bit; +0x14 u16 w, u16 h)
#   CEL_ (cell layout), END_
IMG_BPP = {1: 32, 8: 8, 9: 4}


def blocks(d):
    out = []; pos = 0
    while pos + 16 <= len(d):
        mg = d[pos:pos + 4]; size = struct.unpack_from('<I', d, pos + 4)[0]
        b = dict(magic=mg.decode('latin1'), off=pos, size=size)
        if mg in (b'IMG_', b'PAL_'):
            b['type'] = struct.unpack_from('<I', d, pos + 0x10)[0]
            b['w'], b['h'] = struct.unpack_from('<HH', d, pos + 0x14)
        out.append(b)
        if size == 0 or mg == b'END_':
            break
        pos += size
    return out


def palette(d, pal):
    n = pal['w'] * pal['h']
    o = pal['off'] + 0x80
    cols = [d[o + 4 * k:o + 4 * k + 4] for k in range(n)]
    if n == 256:
        cols = [cols[csm1(i)] for i in range(256)]
    return [bytes((c[0], c[1], c[2], min(255, c[3] * 2))) for c in cols]


def decode_img(d, img, pal):
    w, h, bpp = img['w'], img['h'], IMG_BPP[img['type']]
    o = img['off'] + 0x80
    out = bytearray()
    if bpp == 32:
        for i in range(w * h):
            c = d[o + 4 * i:o + 4 * i + 4]
            out += bytes((c[0], c[1], c[2], min(255, c[3] * 2)))
    elif bpp == 8:
        for i in range(w * h):
            out += pal[d[o + i]]
    else:
        for i in range(w * h):
            b = d[o + i // 2]
            out += pal[(b >> 4) if i & 1 else (b & 15)]
    return bytes(out)


def sprite_pngs(rid, outdir, scale=1):
    from PIL import Image
    d = member(rid); bs = blocks(d)
    pal = next((b for b in bs if b['magic'] == 'PAL_'), None)
    cols = palette(d, pal) if pal else None
    n = 0
    for k, b in enumerate(bs):
        if b['magic'] == 'IMG_' and b['type'] in IMG_BPP:
            im = Image.frombytes('RGBA', (b['w'], b['h']), decode_img(d, b, cols))
            if scale != 1:
                im = im.resize((b['w'] * scale, b['h'] * scale), Image.NEAREST)
            im.save(os.path.join(outdir, f'{rid}_{k:02d}_{b["w"]}x{b["h"]}.png')); n += 1
    return n


def cells(d, bs=None):
    """CEL_ records: [{img: block index among IMG_, x0, y0, x1, y1}] (sprite coordinates,
    origin at the sprite centre). Record: 16-byte tag, u32 image, (u max, v max), colour,
    4 vertices of (s, t, q, 0) + (x, y, z, 1) floats."""
    bs = bs or blocks(d)
    c = next((b for b in bs if b['magic'] == 'CEL_'), None)
    if not c:
        return []
    n = struct.unpack_from('<I', d, c['off'] + 8)[0]
    out = []
    for k in range(n):
        r = c['off'] + 0x10 + 0xC0 * k
        img = struct.unpack_from('<I', d, r + 0x10)[0]
        xs, ys = [], []
        for v in range(4):
            x, y = struct.unpack_from('<ff', d, r + 0x50 + 0x20 * v)
            xs.append(x); ys.append(y)
        out.append(dict(rec=r, img=img, x0=round(min(xs)), y0=round(min(ys)), x1=round(max(xs)), y1=round(max(ys))))
    return out


def compose(rid=None, d=None):
    """(PIL image of the whole sprite, origin (ox, oy), cells, image blocks)"""
    from PIL import Image
    d = d if d is not None else member(rid)
    bs = blocks(d)
    pal = next((b for b in bs if b['magic'] == 'PAL_'), None)
    cols = palette(d, pal) if pal else None
    imgs = [b for b in bs if b['magic'] == 'IMG_']
    cs = cells(d, bs)
    if not cs:
        return None
    x0 = min(c['x0'] for c in cs); y0 = min(c['y0'] for c in cs)
    x1 = max(c['x1'] for c in cs); y1 = max(c['y1'] for c in cs)
    canvas = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
    for c in cs:
        b = imgs[c['img']]
        if b['type'] not in IMG_BPP:
            continue
        im = Image.frombytes('RGBA', (b['w'], b['h']), decode_img(d, b, cols))
        im = im.crop((0, 0, c['x1'] - c['x0'], c['y1'] - c['y0']))
        canvas.alpha_composite(im, (c['x0'] - x0, c['y0'] - y0))
    return canvas, (-x0, -y0), cs, imgs


if __name__ == '__main__':
    cmd = sys.argv[1]
    rid = int(sys.argv[2])
    if cmd == 'info':
        d = member(rid)
        if d[:4] == b'P3TL':
            for i, t in enumerate(p3tx_list(d)):
                print(i, t)
        else:
            for b in blocks(d):
                print(b)
            for c in cells(d):
                print(c)
    elif cmd == 'png':
        os.makedirs(sys.argv[3], exist_ok=True)
        d = member(rid)
        if d[:4] == b'P3TL':
            for i, t in enumerate(p3tx_list(d)):
                to_png(d, t, os.path.join(sys.argv[3], f'{rid}_{i:02d}.png'))
        else:
            r = compose(rid)
            if r:
                r[0].save(os.path.join(sys.argv[3], f'{rid}.png'))
            else:
                sprite_pngs(rid, sys.argv[3])
