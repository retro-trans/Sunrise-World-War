"""Contact sheet of composed sprites: loaded in a savestate, or a list of member ids.

  py -3.11 tools/gfx_gallery.py OUT.png --state STATE.p2s
  py -3.11 tools/gfx_gallery.py OUT.png --rids 6941,6954
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageDraw
import gfx


def sheet(rids, out, width=1400, scale=1):
    tiles = []
    for rid in rids:
        try:
            r = gfx.compose(rid)
        except Exception as e:      # noqa: BLE001 - catalogue tool, skip odd members
            continue
        if r and r[0].size[0] > 0 and r[0].size[1] > 0:
            im = r[0]
            if scale != 1:
                im = im.resize((im.size[0] * scale, im.size[1] * scale), Image.NEAREST)
            tiles.append((rid, im))
    x = y = rowh = 0; place = []
    for rid, im in tiles:
        w, h = max(im.size[0], 40), im.size[1] + 12
        if x + w > width:
            x = 0; y += rowh + 6; rowh = 0
        place.append((rid, im, x, y)); x += w + 8; rowh = max(rowh, h)
    sh = Image.new('RGBA', (width, y + rowh + 6), (40, 50, 70, 255)); dr = ImageDraw.Draw(sh)
    for rid, im, x, y in place:
        sh.alpha_composite(im.convert('RGBA'), (x, y + 12)); dr.text((x, y), str(rid), fill=(255, 255, 0, 255))
    sh.save(out)
    return len(place)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--state'); ap.add_argument('--rids')
    ap.add_argument('--scale', type=int, default=1)
    a = ap.parse_args()
    if a.state:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dbg'))
        from sstate import State
        import gfx_find
        seen = set(); rids = []
        for r in gfx_find.loaded(bytes(State(a.state).ee()), {b'PAL_', b'IMG_'}):
            if r['ram'] not in seen:
                seen.add(r['ram']); rids.append(r['rid'])
    else:
        rids = [int(x) for x in a.rids.split(',')]
    print(sheet(rids, a.out, scale=a.scale), 'sprites')
