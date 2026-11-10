"""Squad (deck) names in saga3_ene_deck_data (0x2668F8): 312-byte entries, s32 id at +0
(-1 ends the table), name at +4 as char[24]. Id 2 "1st Mech Squad" is the player's
starting squad (copied into the save); the rest are enemy, Mission and Versus squads.

English: work/translation/en/deck_names.json {"rows": [{jp, en, notes}]} (23 bytes max).

  py -3.11 tools/deck_names.py check
"""
import json, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN = os.path.join(ROOT, 'work/translation/en/deck_names.json')
TABLE, STRIDE, FIELD = 0x2668F8, 0x138, 24
VA_TO_FILE = 0xFF000


def entries(elf):
    out = []; a = TABLE
    while True:
        i = struct.unpack_from('<i', elf, a - VA_TO_FILE)[0]
        if i == -1:
            return out
        raw = elf[a + 4 - VA_TO_FILE:a + 4 + FIELD - VA_TO_FILE]
        out.append((i, a + 4, raw.split(b'\0')[0].decode('cp932')))
        a += STRIDE


def load():
    return {r['jp']: r for r in json.load(open(EN, encoding='utf-8'))['rows']}


def problems():
    out = []
    for r in load().values():
        en = r.get('en') or ''
        if not en.isascii() or len(en) > FIELD - 1:
            out.append(f'{r["jp"]!r}: {en!r} ({len(en)} bytes)')
    return out


def patches(elf):
    tr = load(); ps = []
    for i, va, jp in entries(elf):
        en = (tr.get(jp) or {}).get('en')
        if en:
            ps.append((va, None, en.encode('ascii').ljust(FIELD, b'\0'), f'squad name {i}'))
    return ps


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        p = problems()
        print('\n'.join(p) or 'ok', len(load()), 'names')
