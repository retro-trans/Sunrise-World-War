"""Extract every ATMB table from RESOURCE.AFS packs into work/source/text/*.json.

Dry run by default: verifies table and codec round trips. --write saves the JSON
(Japanese, local only: work/source/ is git-ignored)."""
import argparse, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from packs import pack_files, members
from textcodec import decode, encode, parse_table, build_table

OUT = 'work/source/text'

def tables():
    for p in pack_files():
        data = open(p, 'rb').read()
        fi = int(os.path.basename(p)[:4])
        for m in members(data):
            blob = data[m['off']:m['off'] + m['size']]
            if blob[:4] == b'ATMB':
                yield fi, m, blob

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    inv = []
    for fi, m, blob in tables():
        name = '%04d_%05d' % (fi, m['rid'])
        raw = parse_table(blob)
        assert build_table(raw) == blob, name
        rows = []
        for i, r in enumerate(raw):
            t = decode(r)
            assert encode(t) == r, (name, i)
            rows.append(dict(id=i, jp=t, size=len(r), sha256=hashlib.sha256(r).hexdigest()[:16]))
        inv.append(dict(table=name, file=fi, rid=m['rid'], rows=len(rows), bytes=len(blob),
                        unique=len(set(raw)), sha256=hashlib.sha256(blob).hexdigest()))
        if a.write:
            os.makedirs(OUT, exist_ok=True)
            json.dump(dict(table=name, rows=rows), open(f'{OUT}/{name}.json', 'w', encoding='utf-8'),
                      ensure_ascii=False, indent=1)
    for t in inv:
        print(t['table'], t['rows'], t['bytes'], t['unique'])
    print('tables', len(inv), 'rows', sum(t['rows'] for t in inv))
    if a.write:
        json.dump(inv, open('work/source/text_inventory.json', 'w'), indent=1)
    else:
        print('DRY RUN: round trips verified; --write saves work/source/text')

if __name__ == '__main__':
    main()
