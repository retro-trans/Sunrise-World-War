"""English redraws of text sprites (PAL_/IMG_/CEL_ members in RESOURCE packs).

Spec: work/translation/gfx/gfx_text.json  {"rows": [{rid, jp, en, ...options}]}
  en        English; "\\n" for two lines
  bg        "fill" (opaque plate: rebuild the plate under the text, default),
            "span" (shaped plate: per row, the commonest colour over the text span),
            "rows" (each row takes the colour of column `plate_x`),
            "inpaint" (picture behind the text: OpenCV inpainting; `thresh`, `glyph_hsv`,
            `grow`), "plate" (uniform plate: the box takes the colour at `plate_from` [x, y]) or
            "clear" (text on transparency: erase every pixel of the box)
  box       [x0, y0, x1, y1] area to rewrite (sprite pixels); default: whole sprite
            minus `margin`; the Japanese is found inside it
  keep      [x0, y0, x1, y1] area never touched (icons)
  erase     "clear" mode: area wiped when it differs from the text box
  font      legacy size-group key; all lettering uses the generated atlas
  image     finished, native-size PNG under work/translation/gfx (optional)
  size      font px (default: fits the Japanese text height and the box)
  fill / stroke   RGB lists (default: sampled from the Japanese glyphs)
  gradient  [[r,g,b] top, [r,g,b] bottom] vertical gradient for the text fill
  stroke_w  outline width (default 1)
  protect   [[x0, y0, x1, y1], ...] restored from the original after the background step
  plate_tint [r, g, b, alpha] blend a plate colour over the box after the background step
  labels    [{box, en, ...}] several labels on one sprite (maps); each may override options
  hstretch  2 when the sprite is displayed twice as wide as stored (episode cards)
  shadow    [dx, dy] inpaint mode: also erase the glyphs' drop shadow
  gap       line gap as a fraction of the font size (default 0.1)
  line_align "left" to left-align the lines of a two-line text (default centred)
  keep_palette  keep the member's palette; unchanged pixels stay, changed ones remap
            to the nearest colour (pictures: no re-quantising)
  group     name of a size group (default: same bg/size/font/box); false = no group
  rotate    90 for vertical tabs (text reads bottom to top)
  align     "center" (default) / "left" / "right"

Output: same sprite size, same pieces, new palette (quantised to the original 16/256
colours). `build_members()` returns {rid: bytes}; every pack holding the rid gets it.

  py -3.11 tools/gfx_text.py preview OUT.png [RID ...]   before/after sheet
  py -3.11 tools/gfx_text.py check                         spec sanity
"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
import gfx
import gfx_lettering

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, 'work/translation/gfx/gfx_text.json')


def load():
    return json.load(open(SPEC, encoding='utf-8'))['rows']


def dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]) + abs(a[3] - b[3])


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def text_mask_fill(im, box, keep):
    """Per-row plate reference from the box's side columns; mask of pixels that differ."""
    x0, y0, x1, y1 = box
    px = im.load(); W, H = im.size
    mask = set(); refs = {}
    for y in range(y0, y1):
        left = [px[x, y] for x in range(x0, min(x0 + 3, x1))]
        right = [px[x, y] for x in range(max(x1 - 3, x0), x1)]
        refs[y] = (left[len(left) // 2], right[len(right) // 2])
        for x in range(x0, x1):
            if keep and keep[0] <= x < keep[2] and keep[1] <= y < keep[3]:
                continue
            t = (x - x0) / max(1, x1 - x0 - 1)
            ref = tuple(int(refs[y][0][k] * (1 - t) + refs[y][1][k] * t) for k in range(4))
            if dist(px[x, y], ref) > 90:
                mask.add((x, y))
    return mask, refs


def plate_rebuild(im, box, refs, keep):
    """Fill the box with each row's left->right interpolation, keeping dither-like noise
    from the original side columns."""
    x0, y0, x1, y1 = box
    px = im.load()
    for y in range(y0, y1):
        a, b = refs[y]
        for x in range(x0 + 3, x1 - 3):
            if keep and keep[0] <= x < keep[2] and keep[1] <= y < keep[3]:
                continue
            t = (x - x0) / max(1, x1 - x0 - 1)
            px[x, y] = tuple(int(a[k] * (1 - t) + b[k] * t) for k in range(4))


REFS = {}
THRESH = [110]
SW = [1]
LINE_ALIGN = ['center']
GAP = [0.1]


def text_mask_span(im, box, keep):
    """Shaped plates: per row, the most common colour (binned) is the plate; pixels far
    from it are text. Returns mask and per-row spans."""
    x0, y0, x1, y1 = box
    px = im.load(); mask = set()
    for y in range(y0, y1):
        bins = {}
        for x in range(x0, x1):
            c = px[x, y]
            if c[3] < 100:
                continue
            k = (c[0] >> 5, c[1] >> 5, c[2] >> 5)
            bins.setdefault(k, []).append(c)
        if not bins:
            continue
        mode = max(bins.values(), key=len)
        ref = tuple(sum(c[k] for c in mode) // len(mode) for k in range(4))
        REFS[y] = ref
        for x in range(x0, x1):
            if keep and keep[0] <= x < keep[2] and keep[1] <= y < keep[3]:
                continue
            c = px[x, y]
            if c[3] >= 100 and dist(c, ref) > THRESH[0]:
                mask.add((x, y))
    return mask


def span_rebuild(im, mask, box):
    """Per row: interpolate between the plate pixels just outside the text span."""
    px = im.load()
    rows = {}
    for x, y in mask:
        rows.setdefault(y, []).append(x)
    # grow the span a little to swallow anti-aliased edges
    for y, xs in rows.items():
        lo, hi = max(box[0], min(xs) - 1), min(box[2] - 1, max(xs) + 1)
        ref = REFS[y]
        for x in range(lo, hi + 1):
            if px[x, y][3] >= 100:
                px[x, y] = ref[:3] + (px[x, y][3],)
    # rows inside the text block with no mask pixels keep their plate


def colours(im, mask):
    if not mask:
        return (255, 255, 255), (20, 20, 20)
    px = im.load()
    cs = sorted((px[x, y] for x, y in mask if px[x, y][3] > 100), key=lum)
    if not cs:
        return (255, 255, 255), (20, 20, 20)
    hi = cs[len(cs) * 2 // 3:]; lo = cs[:max(1, len(cs) // 4)]
    avg = lambda L: tuple(sum(c[k] for c in L) // len(L) for k in range(3))
    return avg(hi), avg(lo)


def render_text(text, size, fill, stroke, sw, fill2=None, scale2=1.0):
    lines = [gfx_lettering.render_line(line, size if i == 0 else max(7, int(size * scale2)),
                                      fill2 if i and fill2 else fill, stroke, sw)
             for i, line in enumerate(text.split('\n'))]
    w = max(line.width for line in lines)
    gap = max(0, int(size * GAP[0]))
    im = Image.new('RGBA', (w, sum(line.height for line in lines) + gap * (len(lines) - 1)))
    y = 0
    for line in lines:
        x = 0 if LINE_ALIGN[0] == 'left' else (w - line.width) // 2
        im.alpha_composite(line, (x, y))
        y += line.height + gap
    return im


PROBE = []          # (avail_w, avail_h, target_h) of the last fits, for group sizing


def fit_text(text, avail_w, avail_h, target_h, fill, stroke, size=None, fill2=None, scale2=1.0, squeeze=0.72):
    """Largest size whose height fits and whose width fits with at most 28% squeeze."""
    PROBE.append((avail_w, avail_h, target_h))
    sizes = [size] if size else list(range(max(9, int(target_h * 1.6)), 6, -1))
    for s in sizes:
        im = render_text(text, s, fill, stroke, SW[0], fill2, scale2)
        if (im.height > avail_h or (not size and im.height > target_h * 1.25 + 2)) and s != sizes[-1]:
            continue
        k = avail_w / im.width
        if k >= squeeze or s == sizes[-1]:
            bounds = (max(1, min(avail_w, im.width)), max(1, min(avail_h, im.height)))
            return im if im.size == bounds else im.resize(bounds, Image.LANCZOS)
    return im


# ---------------------------------------------------------------------------
# Group sizing: sprites of one menu share one font size (long words are squeezed
# horizontally, at most to GROUP_SQUEEZE). A row joins the group named by `group`, or by
# default the group of sprites with the same background mode, height, font and box.
GROUP_SQUEEZE = 0.62
_GROUP_SIZE = {}


def group_key(row):
    if row.get('image') or row.get('size') or row.get('labels') or row.get('hstretch') or row.get('group') is False:
        return None
    if row.get('group'):
        return row['group']
    W, H = gfx.compose(row['rid'])[0].size
    bg = row.get('bg', 'fill')
    width = None if bg == 'clear' else W        # transparent labels: same height = one group
    box = () if bg == 'clear' else tuple(row.get('box') or ())
    return (bg, width, H, row.get('font'), box, bool(row.get('keep')))


def _max_size(row):
    """Largest font size at which this row's text fits its box with the group squeeze."""
    PROBE.clear()
    _redraw(dict(row), gfx.compose(row['rid'])[0])
    if not PROBE:
        return None
    aw, ah, th = PROBE[-1]
    for sz in range(max(9, int(th * 1.6)), 6, -1):
        im = render_text(row['en'], sz, [255, 255, 255], [0, 0, 0], row.get('stroke_w', 1),
                         row.get('fill2'), row.get('scale2', 1.0))
        if im.size[1] > min(ah + 1, th * 1.25 + 2):
            continue
        if aw / im.size[0] >= row.get('squeeze', GROUP_SQUEEZE):
            return sz
    return 7


def resolve_groups(rows):
    groups = {}
    for r in rows:
        k = group_key(r) if r.get('en') else None
        if k is not None:
            groups.setdefault(k, []).append(r)
    for k, rs in groups.items():
        if len(rs) < 2:
            continue
        sizes = [x for x in (_max_size(r) for r in rs) if x]
        if sizes:
            for r in rs:
                _GROUP_SIZE[r['rid']] = min(sizes)
    return _GROUP_SIZE


def redraw(row):
    """(original canvas, redrawn canvas, origin, cells, image blocks). A row with
    `labels` ([{box, en, ...overrides}]) redraws each label in turn on the same sprite."""
    canvas, origin, cs, imgs = gfx.compose(row['rid'])
    if row.get('image'):
        with Image.open(os.path.join(os.path.dirname(SPEC), row['image'])) as replacement:
            if replacement.size != canvas.size:
                raise ValueError(f"sprite {row['rid']}: expected {canvas.size}, got {replacement.size}")
            return canvas, replacement.convert('RGBA'), origin, cs, imgs
    if not _GROUP_SIZE:
        resolve_groups(load())
    if row['rid'] in _GROUP_SIZE and not row.get('size'):
        row = dict(row, size=_GROUP_SIZE[row['rid']], squeeze=0.0)
    parts = [dict(row, **lb) for lb in row['labels']] if row.get('labels') else [row]
    for p in parts:
        p.pop('labels', None)
    k = row.get('hstretch', 1)
    W, H = canvas.size
    if k == 1:
        im = canvas
        for p in parts:
            im = _redraw(p, im)[0]
        return canvas, im, origin, cs, imgs
    # sprite shown k times wider than stored (episode cards, maps: 320 px drawn on 640):
    # draw on a stretched copy, squeeze back, keep the original pixels outside the boxes
    big = canvas.resize((W * k, H), Image.LANCZOS)
    for p in parts:
        b = p['box']; p['box'] = [b[0] * k, b[1], b[2] * k, b[3]]
        if p.get('protect'):
            p['protect'] = [[q[0] * k, q[1], q[2] * k, q[3]] for q in p['protect']]
        big = _redraw(p, big)[0]
    done = big.resize((W, H), Image.LANCZOS)
    out = canvas.copy()
    for p in parts:
        b = [p['box'][0] // k, p['box'][1], -(-p['box'][2] // k), p['box'][3]]
        out.paste(done.crop(tuple(b)), (b[0], b[1]))
    return canvas, out, origin, cs, imgs


def _redraw(row, canvas):
    im = canvas.copy()
    W, H = im.size
    SW[0] = row.get('stroke_w', 1)
    LINE_ALIGN[0] = row.get('line_align', 'center')
    GAP[0] = row.get('gap', 0.1)
    m = row.get('margin', 0 if row.get('bg') == 'clear' else 3)
    box = tuple(row.get('box') or (m, m, W - m, H - m))
    keep = row.get('keep')
    bg = row.get('bg', 'fill')
    if bg == 'clear':
        px = im.load()
        eb = row.get('erase', box)       # area wiped (default: the text box)
        mask = {(x, y) for x in range(eb[0], eb[2]) for y in range(eb[1], eb[3]) if px[x, y][3] > 0
                and not (keep and keep[0] <= x < keep[2] and keep[1] <= y < keep[3])}
        fill, stroke = colours(im, mask)
        for x, y in mask:
            px[x, y] = (0, 0, 0, 0)
    elif bg == 'inpaint':
        # illustrated plates: glyph mask = pixels far from a blurred copy or in the glyph
        # colour ranges, dilated; OpenCV Telea inpainting rebuilds the art underneath
        import numpy as np, cv2
        a = np.array(im)
        x0, y0, x1, y1 = box
        rgb = a[:, :, :3].astype(np.int16)
        blur = cv2.GaussianBlur(a[:, :, :3], (0, 0), 3).astype(np.int16)
        diff = np.abs(rgb - blur).sum(axis=2)
        hsv = cv2.cvtColor(a[:, :, :3], cv2.COLOR_RGB2HSV)
        m = (diff > row.get('thresh', 90))
        for lo, hi in row.get('glyph_hsv', []):
            m |= cv2.inRange(hsv, np.array(lo, np.uint8), np.array(hi, np.uint8)) > 0
        box_m = np.zeros(m.shape, bool); box_m[y0:y1, x0:x1] = True
        m &= box_m
        if row.get('shadow'):          # drop shadow offset down-right of the glyphs
            dx, dy = row['shadow']
            sh = np.zeros_like(m)
            for k in range(1, max(dx, dy) + 1):
                sx, sy = min(k, dx), min(k, dy)
                sh[sy:, sx:] |= m[:m.shape[0] - sy, :m.shape[1] - sx]
            m |= sh & box_m
        m = cv2.dilate(m.astype(np.uint8) * 255, np.ones((3, 3), np.uint8), iterations=row.get('grow', 2))
        m[~box_m] = 0
        ys, xs = np.nonzero(m)
        mask = set(zip(xs.tolist(), ys.tolist()))
        fill, stroke = colours(im, mask)
        out = cv2.inpaint(np.ascontiguousarray(a[:, :, :3]), m, 5, cv2.INPAINT_TELEA)
        a[:, :, :3] = out
        im = Image.fromarray(a, 'RGBA')
    elif bg == 'rows':
        # per row, the box takes the colour of column plate_x (vertical gradients)
        px = im.load(); cx = row['plate_x']
        mask = set()
        for y in range(box[1], box[3]):
            ref = px[cx, y]
            for x in range(box[0], box[2]):
                if dist(px[x, y], ref) > 90:
                    mask.add((x, y))
        fill, stroke = colours(im, mask)
        for y in range(box[1], box[3]):
            ref = px[cx, y]
            for x in range(box[0], box[2]):
                if px[x, y][3] > 0:
                    px[x, y] = ref
    elif bg == 'plate':
        # uniform plate: fill the box with the colour at plate_from
        px = im.load(); ref = px[tuple(row['plate_from'])]
        mask = {(x, y) for x in range(box[0], box[2]) for y in range(box[1], box[3]) if dist(px[x, y], ref) > 90}
        fill, stroke = colours(im, mask)
        for x in range(box[0], box[2]):
            for y in range(box[1], box[3]):
                px[x, y] = ref
    elif bg == 'span':
        THRESH[0] = row.get('thresh', 110)
        mask = text_mask_span(im, box, keep)
        fill, stroke = colours(im, mask)
        span_rebuild(im, mask, box)
    else:
        mask, refs = text_mask_fill(im, box, keep)
        fill, stroke = colours(im, mask)
        plate_rebuild(im, box, refs, keep)
    if row.get('plate_tint'):          # rebuild a translucent label plate over the box
        r_, g_, b_, a_ = row['plate_tint']
        im = im.copy()
        px = im.load()
        for x in range(box[0], box[2]):
            for y in range(box[1], box[3]):
                c = px[x, y]
                px[x, y] = (int(c[0] * (1 - a_) + r_ * a_), int(c[1] * (1 - a_) + g_ * a_),
                            int(c[2] * (1 - a_) + b_ * a_), c[3])
    if row.get('protect'):            # areas restored from the original (markers inside a box)
        im = im.copy()
        for pb in row['protect']:
            im.paste(canvas.crop(tuple(pb)), (pb[0], pb[1]))
    fill = row.get('fill', fill); stroke = row.get('stroke', stroke)
    if mask:
        ys = [p[1] for p in mask]; xs = [p[0] for p in mask]
        jbox = (min(xs), min(ys), max(xs) + 1, max(ys) + 1)
    else:
        jbox = box
    rot = row.get('rotate', 0)
    aw, ah = (box[2] - box[0] - 2, box[3] - box[1] - 2)
    if keep:      # text goes beside the icon
        if keep[2] <= box[0] + (box[2] - box[0]) // 2:
            aw = box[2] - keep[2] - 3
    th = (jbox[3] - jbox[1]) if not rot else (jbox[2] - jbox[0])
    lines = row['en'].count('\n') + 1
    if rot:
        aw, ah = ah, aw
    t = fit_text(row['en'], aw, ah, max(8, th // lines if lines > 1 else th), fill, stroke, row.get('size'),
                 row.get('fill2'), row.get('scale2', 1.0), row.get('squeeze', 0.6 if bg == 'clear' else 0.72))
    if row.get('gradient'):
        import numpy as np
        top, bot = row['gradient']
        ta = np.array(t).astype(np.float32)
        h = ta.shape[0]
        f = np.array(row.get('fill', fill), np.float32)
        for y in range(h):
            k = y / max(1, h - 1)
            col = np.array(top, np.float32) * (1 - k) + np.array(bot, np.float32) * k
            # pixels close to the fill colour take the gradient, the outline stays
            near = np.abs(ta[y, :, :3] - f).sum(axis=1) < 120
            ta[y, near, :3] = col
        t = Image.fromarray(ta.clip(0, 255).astype(np.uint8), 'RGBA')
    if rot:
        t = t.rotate(rot, expand=True)
    tw, tht = t.size
    left = keep[2] + 1 if keep and keep[2] <= box[0] + (box[2] - box[0]) // 2 else box[0]
    al = row.get('align', 'center')
    if al == 'left':
        x = left + 1
    elif al == 'right':
        x = box[2] - tw - 1
    else:
        x = left + (box[2] - left - tw) // 2
    y = box[1] + (box[3] - box[1] - tht) // 2
    im.alpha_composite(t, (max(0, x), max(0, y)))
    return (im,)


def keep_palette_image(d, pal, before, after):
    """'P' image using the member's own palette: unchanged pixels keep their colour,
    changed pixels take the nearest palette colour (pictures keep their quality)."""
    import numpy as np
    cols = np.array([list(c) for c in gfx.palette(d, pal)], np.int32)       # display order
    a0 = np.array(before.convert('RGBA'), np.int32); a1 = np.array(after.convert('RGBA'), np.int32)
    H, W = a1.shape[:2]
    flat = a1.reshape(-1, 4)
    idx = np.zeros(len(flat), np.int64)
    # exact matches first (all unchanged pixels), then nearest colour
    key = lambda a: (a[:, 0] << 24) | (a[:, 1] << 16) | (a[:, 2] << 8) | a[:, 3]
    lut = {}
    for i, k in enumerate(key(cols).tolist()):
        lut.setdefault(k, i)
    ks = key(flat).tolist()
    miss = []
    for i, k in enumerate(ks):
        j = lut.get(k)
        if j is None:
            miss.append(i)
        else:
            idx[i] = j
    if miss:
        m = flat[miss][:, None, :] - cols[None, :, :]
        idx[miss] = (np.abs(m[:, :, :3]).sum(axis=2) + np.abs(m[:, :, 3]) * 2).argmin(axis=1)
    q = Image.new('P', (W, H))
    q.frombytes(idx.astype(np.uint8).tobytes())
    return q


def encode(rid, im, origin, cs, imgs, before=None):
    """New member bytes: same blocks, new palette + indices (or 32-bit pixels). With
    `before` (the original canvas) the palette is kept and only changed pixels remap."""
    d = bytearray(gfx.member(rid))
    bs = gfx.blocks(d)
    pal = next((b for b in bs if b['magic'] == 'PAL_'), None)
    ox, oy = origin
    if pal and before is not None:
        src = keep_palette_image(bytes(d), pal, before, im)
    elif pal:
        n = pal['w'] * pal['h']
        q = im.quantize(colors=n, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        cols = q.getpalette(rawmode='RGBA')[:4 * n]
        cols += [0] * (4 * n - len(cols))
        o = pal['off'] + 0x80
        for i in range(n):
            r, g, b, a = cols[4 * i:4 * i + 4]
            pos = gfx.csm1(i) if n == 256 else i
            d[o + 4 * pos:o + 4 * pos + 4] = bytes((r, g, b, (a + 1) // 2))
        src = q
    else:
        src = im
    for c in cs:
        b = imgs[c['img']]
        if b['type'] not in gfx.IMG_BPP:
            continue
        piece = src.crop((c['x0'] + ox, c['y0'] + oy, c['x0'] + ox + b['w'], c['y0'] + oy + b['h']))
        o = b['off'] + 0x80
        bpp = gfx.IMG_BPP[b['type']]
        cw, ch = c['x1'] - c['x0'], c['y1'] - c['y0']
        if bpp == 32:
            raw = piece.convert('RGBA').tobytes()
            out = bytearray()
            for i in range(0, len(raw), 4):
                out += bytes((raw[i], raw[i + 1], raw[i + 2], (raw[i + 3] + 1) // 2))
            for yy in range(min(ch, b['h'])):
                rowb = out[4 * b['w'] * yy:4 * b['w'] * yy + 4 * min(cw, b['w'])]
                d[o + 4 * b['w'] * yy:o + 4 * b['w'] * yy + len(rowb)] = rowb
            continue
        idx = piece.tobytes()          # 'P' image: one index per pixel
        for yy in range(min(ch, b['h'])):
            for xx in range(min(cw, b['w'])):
                v = idx[yy * b['w'] + xx]
                k = yy * b['w'] + xx
                if bpp == 8:
                    d[o + k] = v
                else:
                    cur = d[o + k // 2]
                    d[o + k // 2] = (cur & 0x0F) | (v << 4) if k & 1 else (cur & 0xF0) | v
    return bytes(d)


def build_members(log=print):
    out = {}
    for row in load():
        if not row.get('en'):
            continue
        canvas, im, origin, cs, imgs = redraw(row)
        out[row['rid']] = encode(row['rid'], im, origin, cs, imgs, canvas if row.get('keep_palette') else None)
    log(f'  text graphics: {len(out)} sprites redrawn (work/translation/gfx/gfx_text.json)')
    return out


def preview(path, rids=None, scale=2):
    rows = [r for r in load() if r.get('en') and (not rids or r['rid'] in rids)]
    tiles = []
    for r in rows:
        canvas, im, origin, cs, imgs = redraw(r)
        # show the encoded result (palette + pieces), not just the drawing
        enc = encode(r['rid'], im, origin, cs, imgs, canvas if r.get('keep_palette') else None)
        after = gfx.compose(d=enc)[0]
        tiles.append((r['rid'], canvas, after))
    W = 1400; x = y = rowh = 0; place = []
    for rid, a, b in tiles:
        w = a.size[0] * scale * 2 + 10; h = a.size[1] * scale + 12
        if x + w > W:
            x = 0; y += rowh + 6; rowh = 0
        place.append((rid, a, b, x, y)); x += w + 14; rowh = max(rowh, h)
    sh = Image.new('RGBA', (W, y + rowh + 6), (40, 50, 70, 255)); dr = ImageDraw.Draw(sh)
    for rid, a, b, x, y in place:
        A = a.resize((a.size[0] * scale, a.size[1] * scale), Image.NEAREST)
        B = b.resize((b.size[0] * scale, b.size[1] * scale), Image.NEAREST)
        sh.alpha_composite(A, (x, y + 12)); sh.alpha_composite(B, (x + A.size[0] + 10, y + 12))
        dr.text((x, y), str(rid), fill=(255, 255, 0, 255))
    sh.save(path)
    return len(place)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'preview':
        print(preview(sys.argv[2], [int(x) for x in sys.argv[3:]] or None), 'sprites')
    elif cmd == 'check':
        rows = load()
        bad = [r['rid'] for r in rows if r.get('en') and any(ord(c) > 126 for c in r['en'].replace('\n', ''))]
        print(len(rows), 'rows;', 'non-ASCII:', bad or 'none')


OCC = os.path.join(ROOT, 'work/source/gfx_occurrences.json')


def occurrences(rids):
    """{rid: [pack file index, ...]} for every pack holding a byte-identical copy."""
    import glob
    from packs import members
    cache = json.load(open(OCC)) if os.path.exists(OCC) else {}
    want = [r for r in rids if str(r) not in cache]
    if want:
        ref = {r: gfx.member(r) for r in want}
        found = {r: [] for r in want}
        for p in sorted(glob.glob(os.path.join(gfx.RES, '*.bin'))):
            d = open(p, 'rb').read()
            fi = int(os.path.basename(p).split('_')[0])
            for m in members(d):
                if m['rid'] in ref and d[m['off']:m['off'] + m['size']] == ref[m['rid']]:
                    found[m['rid']].append(fi)
        cache.update({str(k): v for k, v in found.items()})
        json.dump(cache, open(OCC, 'w'), indent=0)
    return {r: cache[str(r)] for r in rids}
