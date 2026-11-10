"""Check drafts without building: control order, encodability and layout limits.

  py -3.11 tools/fitcheck.py [TABLE ...]     (default: every draft)
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import layout
from translations import DRAFTS, source_rows, check_row
import segments


def check(table):
    t = json.load(open(os.path.join(DRAFTS, table + '.json'), encoding='utf-8'))
    src = source_rows(table)
    n = bad = 0
    for r in t['rows']:
        en = r.get('en')
        if not en and r.get('segments') and any(x.get('en') for x in r['segments']):
            en = segments.join(src[r['id']]['jp'], [x.get('en') for x in r['segments']])
        if not en:
            continue
        n += 1
        probs = []
        if table not in layout.NOT_DIALOGUE:
            en, p = layout.dialogue_layout(en)
            probs += p
        if table in layout.LIBRARY:
            en, p, lines = layout.library_layout(en)
            probs += p
        err = check_row(src[r['id']]['jp'], en)
        if err:
            probs.append(err)
        if probs:
            bad += 1
            print(f'{table} row {r["id"]}: ' + ' | '.join(probs))
    print(f'{table}: {n} drafted rows, {bad} with problems')
    return bad


if __name__ == '__main__':
    tables = sys.argv[1:] or [os.path.basename(p)[:-5] for p in sorted(glob.glob(os.path.join(DRAFTS, '*.json')))
                              if not p.endswith('.en.json') and os.path.basename(p) not in ('elf_strings.json', 'town_strings.json', 'deck_names.json')]
    sys.exit(1 if sum(check(t) for t in tables) else 0)
