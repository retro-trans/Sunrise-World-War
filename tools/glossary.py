"""Glossary DB: work/glossary/*.json (merged view: glossary.json).

  py -3.11 tools/glossary.py seed [--write]   seed from the game's ELF name tables,
        importing researched entries from the sibling Sunrise Eiyuutan / Eiyuutan 2
        glossaries where the Japanese matches (sources are carried over).
  py -3.11 tools/glossary.py merge [--write]  fold work/glossary/research_*.json into
        glossary.json (research wins over imports for en; changes of an imported
        spelling are listed for review and recorded in the entry notes)
  py -3.11 tools/glossary.py stats
  py -3.11 tools/glossary.py lookup TEXT      entries whose jp occurs in TEXT (UTF-8 file or string)

Entry: {jp, en, kind, series?, nickname?, gender?, personality?, position?,
        sources: [...], notes?, status: imported|drafted|researched|unresolved,
        refs: ["chara:12:+0", ...]}
Do not infer gender from a name: gender is filled only from a cited source.
"""
import argparse, glob, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GDIR = os.path.join(ROOT, 'work/glossary')
MAIN = os.path.join(GDIR, 'glossary.json')
SIBLINGS = [os.path.join(ROOT, '../Sunrise Eiyuutan 2/work/glossary/glossary.json')] + \
    sorted(glob.glob(os.path.join(ROOT, '../Sunrise Eiyuutan/work/glossary/*.json')))
KIND = dict(chara='character', mch='machine', ship='ship', dev='ship equipment', skill='skill', eve='key item')


def norm(s):
    return unicodedata.normalize('NFKC', s).replace(' ', '').replace('・', '').replace('･', '')


def sibling_entries():
    out = {}
    for p in SIBLINGS:
        try:
            d = json.load(open(p, encoding='utf-8'))
        except Exception:
            continue
        items = d.get('entries') if isinstance(d, dict) and 'entries' in d else d
        if isinstance(items, dict):
            items = list(items.values()) if all(isinstance(v, dict) for v in items.values()) else \
                [dict(jp=k, en=v) for k, v in items.items() if isinstance(v, str)]
        for e in items or []:
            if isinstance(e, dict) and e.get('jp') and e.get('en'):
                e = dict(e)
                e.setdefault('sources', [])
                e['_from'] = os.path.relpath(p, os.path.dirname(ROOT))
                out.setdefault(norm(e['jp']), e)
    return out


def load():
    if not os.path.exists(MAIN):
        return []
    return json.load(open(MAIN, encoding='utf-8'))['entries']


def save(entries):
    os.makedirs(GDIR, exist_ok=True)
    json.dump(dict(schema=1, policy='wiki spelling wins over corpus; gender only from cited sources',
                   entries=entries), open(MAIN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def seed(write):
    tables = json.load(open(os.path.join(ROOT, 'work/source/name_tables.json'), encoding='utf-8'))
    sib = sibling_entries()
    entries = {norm(e['jp']): e for e in load()}
    added = imported = 0
    for tname, rows in tables.items():
        for r in rows:
            for f, v in r.items():
                if not f.startswith('+'):
                    continue
                jp = v['jp'].strip()
                if not jp or jp in ('なし', 'ナシ', 'NULL', 'ＮＵＬＬ'):
                    continue
                if tname in ('dev', 'skill', 'eve') and f not in ('+0',):
                    continue
                k = norm(jp)
                ref = f'{tname}:{r["index"]}:{f}'
                if k in entries:
                    if ref not in entries[k].setdefault('refs', []):
                        entries[k]['refs'].append(ref)
                    continue
                e = dict(jp=jp, en='', kind=KIND[tname], status='unresolved', sources=[], refs=[ref])
                s = sib.get(k)
                if s:
                    for key in ('en', 'nickname', 'gender', 'personality', 'position', 'series', 'notes'):
                        if s.get(key):
                            e[key] = s[key]
                    e['sources'] = list(s.get('sources', [])) + ['sibling:' + s['_from']]
                    e['status'] = 'imported'
                    imported += 1
                entries[k] = e
                added += 1
    print(f'entries {len(entries)} (new {added}, imported from siblings {imported})')
    if write:
        save(list(entries.values()))
    else:
        print('DRY RUN: --write saves work/glossary/glossary.json')


def merge(write):
    entries = {norm(e['jp']): e for e in load()}
    changed = []; added = 0; updated = 0
    for p in sorted(glob.glob(os.path.join(GDIR, 'research_*.json'))):
        for r in json.load(open(p, encoding='utf-8')):
            if not r.get('jp') or not r.get('en'):
                continue
            k = norm(r['jp'])
            e = entries.get(k)
            if e is None:
                e = entries[k] = dict(jp=r['jp'], refs=[]); added += 1
            old = e.get('en')
            if old and old != r['en'] and e.get('status') == 'imported':
                changed.append((r['jp'], old, r['en'], os.path.basename(p)))
                e['notes'] = (e.get('notes', '') + f' | research changed imported "{old}" -> "{r["en"]}"').strip(' |')
            for key in ('en', 'kind', 'series', 'nickname', 'gender', 'personality', 'position', 'confidence'):
                if r.get(key):
                    e[key] = r[key]
            if r.get('notes'):
                e['notes'] = (e.get('notes', '') + ' | ' + r['notes']).strip(' |') if r['notes'] not in e.get('notes', '') else e.get('notes')
            e['sources'] = list(dict.fromkeys(e.get('sources', []) + r.get('sources', [])))
            e['status'] = 'researched'
            e.setdefault('research', os.path.basename(p))
            updated += 1
    print(f'merged {updated} research rows ({added} new entries)')
    for c in changed:
        print('  changed imported spelling:', c[1], '->', c[2], f'({c[3]})')
    if write:
        save(list(entries.values()))
    else:
        print('DRY RUN: --write saves')


def stats():
    import collections
    es = load()
    c = collections.Counter((e['kind'], e['status']) for e in es)
    for k, v in sorted(c.items()):
        print(k, v)


def lookup(text):
    if os.path.exists(text):
        text = open(text, encoding='utf-8').read()
    for e in sorted(load(), key=lambda e: -len(e['jp'])):
        if e['jp'] in text and e.get('en'):
            print(f"{e['jp']}\t{e['en']}\t{e['kind']}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['seed', 'merge', 'stats', 'lookup'])
    ap.add_argument('arg', nargs='?')
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'seed':
        seed(a.write)
    elif a.cmd == 'merge':
        merge(a.write)
    elif a.cmd == 'stats':
        stats()
    else:
        lookup(a.arg)
