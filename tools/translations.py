"""Load translation drafts: work/translation/en/<table>.json

{"table": "1271_02471", "rows": [{"id": 5, "jp": "...", "en": "...", "status": "..."}]}

Rows without a non-empty "en" keep their source bytes. Every "en" must keep the
source row's control records ({C:..}) in the same order; layout is checked by
tools/fitcheck.py. Returns raw ATMB row lists ready for textcodec.build_table.
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from textcodec import encode, decode, controls, parse_table
import layout, segments

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work/source/text')
DRAFTS = os.path.join(ROOT, 'work/translation/en')


def source_rows(table):
    return json.load(open(os.path.join(SRC, table + '.json'), encoding='utf-8'))['rows']


def raw_rows(table):
    """Original raw bytes of every row, from the pack (exact)."""
    from packs import pack_files, members
    fi, rid = int(table[:4]), int(table[5:])
    d = open(pack_files()[fi], 'rb').read()
    for m in members(d):
        if m['rid'] == rid:
            return parse_table(d[m['off']:m['off'] + m['size']])
    raise KeyError(table)


def check_row(src_text, en):
    sc, ec = controls(src_text), controls(en)
    if sc != ec:
        return f'control mismatch: {sc} vs {ec}'
    if '\\n' in en and '\\n' not in src_text:
        return 'literal backslash-n (would print as text; use a real line break)'
    try:
        en.encode('cp932')
    except UnicodeEncodeError as e:
        return f'not encodable: {e}'
    return None


def load_tables(log=print, strict=True):
    for path in sorted(glob.glob(os.path.join(DRAFTS, '*.json'))):
        if path.endswith('.en.json') or os.path.basename(path) in ('elf_strings.json', 'town_strings.json', 'deck_names.json'):
            continue
        t = json.load(open(path, encoding='utf-8'))
        name = t['table']
        raw = raw_rows(name)
        src = source_rows(name)
        n = 0; errs = []
        for r in t['rows']:
            en = r.get('en')
            if not en and r.get('segments'):
                segs = [x.get('en') for x in r['segments']]
                if not any(segs):
                    continue
                try:
                    en = segments.join(src[r['id']]['jp'], segs)
                except ValueError as e:
                    errs.append((r['id'], str(e))); continue
            if not en:
                continue
            if name not in layout.NOT_DIALOGUE:
                en, probs = layout.dialogue_layout(en)
                if probs:
                    errs.append((r['id'], '; '.join(probs))); continue
            if name in layout.LIBRARY:
                en, probs, _ = layout.library_layout(en)
                if probs:
                    errs.append((r['id'], '; '.join(probs))); continue
            err = check_row(src[r['id']]['jp'], en)
            if err:
                errs.append((r['id'], err)); continue
            raw[r['id']] = encode(en)
            n += 1
        if errs:
            for i, e in errs[:20]:
                log(f'  !! {name} row {i}: {e}')
            if strict:
                raise ValueError(f'{name}: {len(errs)} rows failed checks')
        if n:
            yield name, n, raw
