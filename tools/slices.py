"""Make translation slices and merge results.

  py -3.11 tools/slices.py library [--size 80]   -> work/translation/slices/lib_<table>_<k>.json
  py -3.11 tools/slices.py merge PATTERN         merge *.out.json into work/translation/en/<table>.json
  py -3.11 tools/slices.py check SLICE           validate SLICE.out.json (controls, layout limits)
  py -3.11 tools/slices.py dialogue [N]          -> dlg_<table>_<k>.json (~N segments each)
  py -3.11 tools/slices.py speakers PATTERN      add per-segment speaker names to dialogue slices
  py -3.11 tools/slices.py glossary PATTERN      write <slice>.glossary.tsv
  py -3.11 tools/slices.py merge-dialogue PATTERN

A slice lists unique source rows (duplicates are recorded in `dups` and receive the same
translation on merge). Agents write <slice>.out.json: {"rows": [{"id", "en", "notes"}]}.
"""
import glob, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work/source/text')
SL = os.path.join(ROOT, 'work/translation/slices')
EN = os.path.join(ROOT, 'work/translation/en')


def library(size):
    for table in ('1271_02471', '1271_10345'):
        rows = json.load(open(os.path.join(SRC, table + '.json'), encoding='utf-8'))['rows']
        first = {}; dups = {}
        for r in rows:
            if r['id'] == 0:
                continue                      # placeholder / narrator row
            k = r['jp']
            if k in first:
                dups.setdefault(first[k], []).append(r['id'])
            else:
                first[k] = r['id']
        uniq = [r for r in rows if r['id'] in first.values()]
        for k in range(0, len(uniq), size):
            part = uniq[k:k + size]
            name = f'lib_{table}_{k // size}'
            json.dump(dict(slice=name, table=table, rows=[dict(id=r['id'], jp=r['jp'], dups=dups.get(r['id'], []))
                                                          for r in part]),
                      open(os.path.join(SL, name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
            print(name, len(part), 'rows', part[0]['id'], '-', part[-1]['id'])


def merge(pattern):
    by_table = {}
    for p in sorted(glob.glob(os.path.join(SL, pattern + '.out.json'))):
        sl = json.load(open(p.replace('.out.json', '.json'), encoding='utf-8'))
        out = {r['id']: r for r in json.load(open(p, encoding='utf-8'))['rows']}
        t = by_table.setdefault(sl['table'], {})
        for r in sl['rows']:
            o = out.get(r['id'])
            if not o or not o.get('en'):
                continue
            for rid in [r['id']] + r.get('dups', []):
                t[rid] = dict(en=o['en'], notes=o.get('notes', ''), status=o.get('status', 'draft'))
    for table, upd in by_table.items():
        path = os.path.join(EN, table + '.json')
        src = json.load(open(os.path.join(SRC, table + '.json'), encoding='utf-8'))['rows']
        cur = {r['id']: r for r in json.load(open(path, encoding='utf-8'))['rows']} if os.path.exists(path) else {}
        for rid, v in upd.items():
            cur[rid] = dict(id=rid, jp=src[rid]['jp'], **v)
        json.dump(dict(table=table, rows=[cur[k] for k in sorted(cur)]), open(path, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'{table}: merged {len(upd)} rows ({len(cur)} drafted)')


def slice_glossary(pattern):
    """Write <slice>.glossary.tsv: glossary entries whose jp occurs in the slice."""
    g = [e for e in json.load(open(os.path.join(ROOT, 'work/glossary/glossary.json'), encoding='utf-8'))['entries']
         if e.get('en') and len(e['jp']) >= 2]
    g.sort(key=lambda e: -len(e['jp']))
    for p in sorted(glob.glob(os.path.join(SL, pattern + '.json'))):
        if p.endswith('.out.json'):
            continue
        sl = json.load(open(p, encoding='utf-8'))
        text = '\n'.join(r['jp'] if 'jp' in r else '\n'.join(r['segments']) for r in sl['rows'])
        hits = [e for e in g if e['jp'] in text]
        with open(p[:-5] + '.glossary.tsv', 'w', encoding='utf-8') as f:
            f.write('jp\ten\tkind\tconfidence\n')
            for e in hits:
                f.write(f"{e['jp']}\t{e['en']}\t{e.get('kind', '')}\t{e.get('confidence', e.get('status', ''))}\n")
        print(os.path.basename(p), len(hits), 'glossary names')


def check(name):
    sys.path.insert(0, os.path.dirname(__file__))
    import layout
    from translations import check_row
    sl = json.load(open(os.path.join(SL, name + '.json'), encoding='utf-8'))
    out = json.load(open(os.path.join(SL, name + '.out.json'), encoding='utf-8'))['rows']
    if sl['rows'] and 'segments' in sl['rows'][0]:
        from translations import source_rows
        srows = source_rows(sl['table'])
        src = {r['id']: srows[r['id']]['jp'] for r in sl['rows']}
    else:
        src = {r['id']: r['jp'] for r in sl['rows']}
    bad = 0; seen = set()
    for r in out:
        seen.add(r['id'])
        en = r.get('en') or ('x' if r.get('segments') else '')
        probs = []
        if not en:
            probs.append('empty')
        elif 'segments' in r:
            probs += check_dialogue(sl['table'], src[r['id']], r)
        elif sl['table'] in layout.LIBRARY:
            en2, p, n = layout.library_layout(en)
            probs += p
            e = check_row(src[r['id']], en2)
            if e: probs.append(e)
        if probs:
            bad += 1; print(f'row {r["id"]}: ' + ' | '.join(probs))
    missing = [i for i in src if i not in seen]
    print(f'{name}: {len(out)} rows, {bad} with problems, missing {missing}')
    return bad + len(missing)


def check_dialogue(table, jp, r):
    """Segment count, ASCII, page fit (dialogue tables) and control order for one row."""
    import layout, segments as sg
    from translations import check_row
    probs = []
    segs = r['segments']
    want = len(sg.segments(jp))
    if len(segs) != want:
        return [f'{len(segs)} segments, source has {want}']
    for k, e in enumerate(segs):
        if not e or not e.strip():
            probs.append(f'segment {k} empty')
        elif any(ord(c) > 126 and c not in '■●★☆♪' for c in e):
            probs.append(f'segment {k} non-ASCII: {e[:40]!r}')
        elif '\\n' in e:
            probs.append(f'segment {k} has a literal backslash-n')
        elif e.startswith('\n') or e.endswith('\n') or '\n\n' in e:
            probs.append(f'segment {k} has leading/trailing/blank-line newlines')
    if probs:
        return probs
    if table not in layout.NOT_DIALOGUE:
        for k, e in enumerate(segs):
            n = sum(len(layout.wrap(ln, layout.DIALOGUE_LIMIT, 26, 0)) if layout.text_width(ln, 26) > layout.DIALOGUE_LIMIT
                    else 1 for ln in e.split('\n'))
            if n > layout.DIALOGUE_LINES:
                probs.append(f'segment {k}: {n} lines > {layout.DIALOGUE_LINES}: {e[:50]!r}')
        if probs:
            return probs
    en = sg.join(jp, segs)
    if table not in layout.NOT_DIALOGUE:
        en, p = layout.dialogue_layout(en)
        probs += p
    err = check_row(jp, en)
    if err:
        probs.append(err)
    return probs


def speakers(pattern):
    """Add `speakers` to dialogue slice rows: per segment, the English name of the
    character in the page's ＄ / ％ header (low 10 bits = chara index), from the chara name table."""
    import re, segments as sg
    from translations import source_rows
    nt = json.load(open(os.path.join(ROOT, 'work/source/name_tables.json'), encoding='utf-8'))['chara']
    es = {r['va']: r.get('en') for r in json.load(open(os.path.join(EN, 'elf_strings.json'), encoding='utf-8'))['rows']}
    name = {c['index']: es.get(c['+0']['va']) or f"chara {c['index']}" for c in nt}
    hdr = re.compile(r'\{C:819([03])([0-9A-Fa-f]{4})\}')
    for p in sorted(glob.glob(os.path.join(SL, pattern + '.json'))):
        if p.endswith('.out.json'):
            continue
        sl = json.load(open(p, encoding='utf-8'))
        src = source_rows(sl['table'])
        hits = 0
        for r in sl['rows']:
            parts, idx = sg.split(src[r['id']]['jp'])
            sp = []
            for i in idx:
                who = ''
                for j in range(i - 1, -1, -1):
                    if re.fullmatch(r'\n{2,}', parts[j]):
                        break
                    m = hdr.fullmatch(parts[j])
                    if m:
                        cid = int.from_bytes(bytes.fromhex(m.group(2)), 'little') & 0x3FF   # high bits: face/pose
                        who = name.get(cid, f'chara {cid}')
                        break
                sp.append(who); hits += bool(who)
            r['speakers'] = sp
        json.dump(sl, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(os.path.basename(p), hits, 'segments with a speaker')


def dialogue(target):
    """Slices of ~target segments per table, whole rows only, unique rows (duplicates
    are listed in dups). Slice row: {id, segments: [jp...], dups}."""
    sys.path.insert(0, os.path.dirname(__file__))
    import segments as sg, layout, re
    jp = re.compile('[぀-ヿ一-鿿]')
    made = 0
    for p in sorted(glob.glob(os.path.join(SRC, '*.json'))):
        t = json.load(open(p, encoding='utf-8')); table = t['table']
        if table in layout.LIBRARY:
            continue
        first = {}; dups = {}; rows = []
        for r in t['rows']:
            segs = sg.segments(r['jp'])
            if not any(jp.search(s) for s in segs):
                continue
            if r['jp'] in first:
                dups.setdefault(first[r['jp']], []).append(r['id']); continue
            first[r['jp']] = r['id']
            rows.append(dict(id=r['id'], segments=segs))
        cur = []; n = 0; k = 0
        for r in rows + [None]:
            if r is None or (n + len(r['segments']) > target and cur):
                for x in cur:
                    x['dups'] = dups.get(x['id'], [])
                if cur:
                    name = f'dlg_{table}_{k:02d}'
                    json.dump(dict(slice=name, table=table, rows=cur), open(os.path.join(SL, name + '.json'), 'w',
                              encoding='utf-8'), ensure_ascii=False, indent=1)
                    made += 1; k += 1
                cur = []; n = 0
                if r is None:
                    break
            cur.append(r); n += len(r['segments'])
    print('dialogue slices:', made)


def merge_dialogue(pattern):
    by_table = {}
    for p in sorted(glob.glob(os.path.join(SL, pattern + '.out.json'))):
        sl = json.load(open(p.replace('.out.json', '.json'), encoding='utf-8'))
        out = {r['id']: r for r in json.load(open(p, encoding='utf-8'))['rows']}
        t = by_table.setdefault(sl['table'], {})
        for r in sl['rows']:
            o = out.get(r['id'])
            if not o:
                continue
            segs = [dict(jp=j, en=e) for j, e in zip(r['segments'], o.get('segments', []))]
            for rid in [r['id']] + r.get('dups', []):
                t[rid] = dict(segments=segs, notes=o.get('notes', ''), status=o.get('status', 'draft'))
    for table, upd in by_table.items():
        path = os.path.join(EN, table + '.json')
        cur = {r['id']: r for r in json.load(open(path, encoding='utf-8'))['rows']} if os.path.exists(path) else {}
        for rid, v in upd.items():
            cur[rid] = dict(id=rid, **v)
        json.dump(dict(table=table, rows=[cur[k] for k in sorted(cur)]), open(path, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'{table}: merged {len(upd)} rows')


if __name__ == '__main__':
    if sys.argv[1] == 'check':
        sys.exit(1 if check(sys.argv[2]) else 0)
    if sys.argv[1] == 'library':
        library(int(sys.argv[sys.argv.index('--size') + 1]) if '--size' in sys.argv else 80)
    elif sys.argv[1] == 'dialogue':
        dialogue(int(sys.argv[2]) if len(sys.argv) > 2 else 400)
    elif sys.argv[1] == 'merge-dialogue':
        merge_dialogue(sys.argv[2])
    elif sys.argv[1] == 'speakers':
        speakers(sys.argv[2])
    elif sys.argv[1] == 'glossary':
        slice_glossary(sys.argv[2])
    elif sys.argv[1] == 'merge':
        merge(sys.argv[2])