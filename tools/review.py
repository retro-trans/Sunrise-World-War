"""Three-stage review (BASE_RULES: accuracy -> editorial -> proofread) over the drafts.

  py -3.11 tools/review.py export STAGE              write review files for every unit
  py -3.11 tools/review.py check STAGE UNIT          validate UNIT.out.json (edits fit, controls)
  py -3.11 tools/review.py apply STAGE [--write]     apply every UNIT.out.json to the drafts
  py -3.11 tools/review.py groups STAGE N            print agent groups of ~N source chars

Units: dialogue slices (dlg_*), library slices (lib_*) and the non-name executable
strings (elf_0, elf_1; glossary names are fixed by script, not reviewed). Files live in
work/translation/review/<stage>/ (local only, they hold Japanese):

  UNIT.json      {unit, table, kind, stage, rows: [...]}   (current English from the drafts)
    dialogue rows: {id, items: [{k, speaker, jp, en}], notes}
    library rows:  {id, jp, en, notes}
    elf rows:      {id (= va), group, jp, en, notes}
  UNIT.out.json  {"examined": N, "edits": [{"id", "k"?, "en", "reason"}],
                  "flags": [{"id", "k"?, "stage"?, "note"}]}

`apply` writes the edits into work/translation/en/*.json, sets status to the stage on
every row of an applied unit, appends "[STAGE] reason" to the row notes and logs every
edit to work/translation/review/<stage>/_applied.json. Run tools/term_fixes.py after.
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import layout, segments as sg
from translations import source_rows, check_row

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EN = os.path.join(ROOT, 'work/translation/en')
SL = os.path.join(ROOT, 'work/translation/slices')
RV = os.path.join(ROOT, 'work/translation/review')
STAGES = ('accuracy', 'editorial', 'proofread')
ELF_UNITS = 2


def draft(table):
    return json.load(open(os.path.join(EN, table + '.json'), encoding='utf-8'))


def units():
    for p in sorted(glob.glob(os.path.join(SL, 'dlg_*.json'))):
        if not p.endswith('.out.json'):
            yield os.path.basename(p)[:-5], 'dialogue'
    for p in sorted(glob.glob(os.path.join(SL, 'lib_*.json'))):
        if not p.endswith('.out.json'):
            yield os.path.basename(p)[:-5], 'library'
    for k in range(ELF_UNITS):
        yield f'elf_{k}', 'elf'


def elf_rows():
    rows = [r for r in draft('elf_strings')['rows'] if r.get('en') and not r['group'].startswith('names:')]
    rows.sort(key=lambda r: (r['group'], int(r['va'], 16)))
    return rows


def build_unit(unit, kind, stage):
    if kind == 'elf':
        rows = elf_rows()
        k = int(unit.split('_')[1]); n = (len(rows) + ELF_UNITS - 1) // ELF_UNITS
        part = rows[k * n:(k + 1) * n]
        return dict(unit=unit, table='elf_strings', kind=kind, stage=stage,
                    rows=[dict(id=r['va'], group=r['group'], jp=r['jp'], en=r['en'], notes=r.get('notes', ''))
                          for r in part])
    sl = json.load(open(os.path.join(SL, unit + '.json'), encoding='utf-8'))
    cur = {r['id']: r for r in draft(sl['table'])['rows']}
    out = []
    for r in sl['rows']:
        d = cur.get(r['id'])
        if not d:
            continue
        if kind == 'library':
            out.append(dict(id=r['id'], jp=r['jp'], en=d['en'], notes=d.get('notes', '')))
        else:
            segs = d.get('segments') or []
            sp = r.get('speakers') or [''] * len(segs)
            out.append(dict(id=r['id'], notes=d.get('notes', ''),
                            items=[dict(k=k, speaker=sp[k] if k < len(sp) else '', jp=s['jp'], en=s.get('en', ''))
                                   for k, s in enumerate(segs)]))
    return dict(unit=unit, table=sl['table'], kind=kind, stage=stage, rows=out)


def export(stage):
    d = os.path.join(RV, stage); os.makedirs(d, exist_ok=True)
    n = 0
    for unit, kind in units():
        u = build_unit(unit, kind, stage)
        json.dump(u, open(os.path.join(d, unit + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        n += 1
    print(f'{stage}: {n} units in {os.path.relpath(d, ROOT)}')


CTRL = re.compile(r'%[0-9Rtzb]|\{[^}]*\}')


def edit_problems(u, e, src_cache):
    """Problems for one edit, evaluated on the row with the edit applied."""
    en = e.get('en')
    if not isinstance(en, str) or not en.strip():
        return ['empty en']
    if any(ord(c) > 126 and c not in '■●★☆♪\n' for c in en):
        return [f'non-ASCII: {en[:40]!r}']
    rows = {r['id']: r for r in u['rows']}
    r = rows.get(e.get('id'))
    if r is None:
        return [f'unknown id {e.get("id")}']
    if '\\n' in en:
        return ['literal backslash-n (use a real line break)']
    if u['kind'] == 'elf':
        if CTRL.findall(en) != CTRL.findall(r['en']):
            return ['control codes (%R, %n...) differ from the current English']
        return []
    if u['kind'] == 'library':
        jp = src_cache(u['table'])[r['id']]['jp']
        en2, p, _ = layout.library_layout(en)
        err = check_row(jp, en2)
        return p + ([err] if err else [])
    k = e.get('k')
    if not isinstance(k, int) or not 0 <= k < len(r['items']):
        return [f'bad segment index {k}']
    if en.startswith('\n') or en.endswith('\n') or '\n\n' in en:
        return ['leading/trailing newline or blank line']
    jp = r['items'][k]['jp']
    if '/' in en and '/' not in jp and '／' not in jp and u['table'] != '2271_06810':
        return ['"/" used as a line break (the game prints it); use a real newline']
    return []


def row_problems(u, rid, items_en, src_cache):
    """Fit/control check of a whole dialogue row after all its edits."""
    jp = src_cache(u['table'])[rid]['jp']
    probs = []
    if u['table'] not in layout.NOT_DIALOGUE:
        for k, e in enumerate(items_en):
            n = sum(len(layout.wrap(ln, layout.DIALOGUE_LIMIT, 26, 0))
                    if layout.text_width(ln, 26) > layout.DIALOGUE_LIMIT else 1 for ln in e.split('\n'))
            if n > layout.DIALOGUE_LINES:
                probs.append(f'segment {k}: {n} lines > {layout.DIALOGUE_LINES}')
    err = check_row(jp, sg.join(jp, items_en))
    if err:
        probs.append(err)
    return probs


def _src():
    cache = {}
    def get(table):
        if table not in cache:
            cache[table] = source_rows(table)
        return cache[table]
    return get


def check(stage, unit, quiet=False):
    d = os.path.join(RV, stage)
    u = json.load(open(os.path.join(d, unit + '.json'), encoding='utf-8'))
    o = json.load(open(os.path.join(d, unit + '.out.json'), encoding='utf-8'))
    src = _src(); bad = 0
    edits = o.get('edits', [])
    for e in edits:
        for p in edit_problems(u, e, src):
            bad += 1; print(f'id {e.get("id")} k {e.get("k")}: {p}')
    if u['kind'] == 'dialogue':
        rows = {r['id']: r for r in u['rows']}
        touched = {}
        for e in edits:
            r = rows.get(e.get('id'))
            if r is None or not isinstance(e.get('k'), int) or not 0 <= e['k'] < len(r['items']):
                continue
            touched.setdefault(r['id'], [it['en'] for it in r['items']])[e['k']] = e['en']
        for rid, items in touched.items():
            for p in row_problems(u, rid, items, src):
                bad += 1; print(f'id {rid}: {p}')
    ex = o.get('examined')
    total = sum(len(r['items']) for r in u['rows']) if u['kind'] == 'dialogue' else len(u['rows'])
    if not quiet or bad:
        print(f'{unit} [{stage}]: {len(edits)} edits, {len(o.get("flags", []))} flags, '
              f'examined {ex} of {total}, {bad} problems')
    if ex != total:
        print(f'{unit}: examined count {ex} != {total}')
        bad += 1
    return bad


def apply(stage, write):
    d = os.path.join(RV, stage)
    drafts = {}; log = []; bad_units = []
    for p in sorted(glob.glob(os.path.join(d, '*.out.json'))):
        unit = os.path.basename(p)[:-9]
        if check(stage, unit, quiet=True):
            bad_units.append(unit); continue
        u = json.load(open(os.path.join(d, unit + '.json'), encoding='utf-8'))
        o = json.load(open(p, encoding='utf-8'))
        t = drafts.setdefault(u['table'], draft(u['table']))
        key = 'va' if u['kind'] == 'elf' else 'id'
        byid = {r[key]: r for r in t['rows']}
        dups = {}
        if u['kind'] != 'elf':
            for r in json.load(open(os.path.join(SL, unit + '.json'), encoding='utf-8'))['rows']:
                dups[r['id']] = r.get('dups', [])
        for r in u['rows']:
            for rid in [r['id']] + dups.get(r['id'], []):
                if rid in byid:
                    byid[rid]['status'] = stage
        for e in o.get('edits', []):
            for rid in [e['id']] + dups.get(e['id'], []):
                row = byid[rid]
                if u['kind'] == 'dialogue':
                    old = row['segments'][e['k']].get('en'); row['segments'][e['k']]['en'] = e['en']
                else:
                    old = row['en']; row['en'] = e['en']
                if e.get('reason') and rid == e['id']:
                    tag = f'[{stage}' + (f' {e["k"]}' if 'k' in e else '') + f'] {e["reason"]}'
                    row['notes'] = (row.get('notes', '') + ' | ' + tag).strip(' |')
            log.append(dict(unit=unit, id=e['id'], k=e.get('k'), old=old, new=e['en'], reason=e.get('reason', '')))
    print(f'{stage}: {len(log)} edits from {len(glob.glob(os.path.join(d, "*.out.json"))) - len(bad_units)} units;'
          f' skipped (failing check): {bad_units}')
    if write:
        for table, t in drafts.items():
            json.dump(t, open(os.path.join(EN, table + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        json.dump(log, open(os.path.join(d, '_applied.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('WRITTEN')
    else:
        print('DRY RUN: --write applies')


def groups(stage, size):
    d = os.path.join(RV, stage)
    gs = []; cur = []; n = 0
    for unit, kind in units():
        u = json.load(open(os.path.join(d, unit + '.json'), encoding='utf-8'))
        c = sum(len(it['jp']) for r in u['rows'] for it in r['items']) if kind == 'dialogue' else \
            sum(len(r['jp']) for r in u['rows'])
        if cur and (n + c > size or kind != cur[-1][1]):
            gs.append(cur); cur = []; n = 0
        cur.append((unit, kind)); n += c
    gs.append(cur)
    out = [[u for u, _ in g] for g in gs]
    json.dump(out, open(os.path.join(d, '_groups.json'), 'w'), indent=0)
    for i, g in enumerate(out):
        print(i, ' '.join(g))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'export':
        export(sys.argv[2])
    elif cmd == 'check':
        sys.exit(1 if check(sys.argv[2], sys.argv[3]) else 0)
    elif cmd == 'apply':
        apply(sys.argv[2], '--write' in sys.argv)
    elif cmd == 'groups':
        groups(sys.argv[2], int(sys.argv[3]))
