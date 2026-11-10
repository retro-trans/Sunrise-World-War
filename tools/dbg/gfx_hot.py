"""Write redrawn sprites (tools/gfx_text.py) over their copies in the running game's RAM.

  py -3.11 tools/dbg/gfx_hot.py --run [RID ...]
Finds each original member in EE RAM (savestate read through PINE) and overwrites it.
Only for previews: textures already uploaded to video memory change when redrawn."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import pine, gfx, gfx_text

ap = argparse.ArgumentParser(); ap.add_argument('rids', nargs='*', type=int); ap.add_argument('--run', action='store_true')
a = ap.parse_args()
p = pine.Pine()
ee = p.read(0, 32 << 20)
new = gfx_text.build_members(lambda s: None)
n = 0
for rid, data in new.items():
    if a.rids and rid not in a.rids:
        continue
    old = gfx.member(rid)
    at = ee.find(old)
    while at >= 0:
        if a.run:
            p.write(at, data)
        n += 1
        at = ee.find(old, at + 1)
print(n, 'copies', 'written' if a.run else 'found (dry run)')
