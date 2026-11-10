"""Which RESOURCE image members are loaded in a savestate's EE RAM.

  py -3.11 tools/gfx_find.py STATE.p2s [--kinds P3TL,PAL_,IMG_]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dbg'))
from sstate import State
import gfx


def loaded(ee, kinds):
    idx = gfx.index(); cache = {}; out = []
    for rid, v in idx.items():
        if bytes.fromhex(v['magic'])[:4] not in kinds or v['size'] < 256:
            continue
        if v['file'] not in cache:
            cache[v['file']] = open(gfx.pack_path(v['file']), 'rb').read()
        d = cache[v['file']]
        # probe: the first 48-byte window (from the middle on, then from the start) with
        # some variety; mostly flat images (dark cards) need a later window
        probe = None
        for start in list(range(v['size'] // 2, v['size'] - 48, 997)) + list(range(0x80, v['size'] // 2, 997)):
            w = d[v['off'] + start:v['off'] + start + 48]
            if len(set(w)) >= 6:
                probe, rel = w, start; break
        if probe is None:
            continue
        at = ee.find(probe)
        if at >= 0:
            out.append(dict(rid=int(rid), file=v['file'], kind=bytes.fromhex(v['magic'])[:4].decode(),
                            size=v['size'], ram=hex(at - rel)))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('state'); ap.add_argument('--kinds', default='P3TL,PAL_,IMG_')
    a = ap.parse_args()
    ee = State(a.state).ee()
    for r in loaded(bytes(ee), {k.encode() for k in a.kinds.split(',')}):
        print(r)
