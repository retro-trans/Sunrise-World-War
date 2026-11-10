"""English short ("omit") names: name tables chara/mch/ship field +8 (half-width kana).

Shown by *GetOmitName: unit / pilot / ship lists (deck edit, shop, battle select),
battle board labels. Drawn in an ANK font (fixed width, one cell per byte), so the
English may use up to the longest Japanese short name of its table (LIMIT bytes).

  py -3.11 tools/short_names.py draft [--write]   propose English, add rows to elf_strings.json
  py -3.11 tools/short_names.py todo              rows still without English

Draft rules (per unique string address):
  1. the display name (+4) English if it fits, else the full name (+0) English if it fits;
  2. ships: the display name without "-class";
  3. characters: the word span of the display/full English that best matches the kana
     reading (title dropped: "Professor Rondo" -> "Rondo");
  4. otherwise left empty for hand translation (`todo`).
"""
import difflib, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NT = os.path.join(ROOT, 'work/source/name_tables.json')
ES = os.path.join(ROOT, 'work/translation/en/elf_strings.json')
LIMIT = {'chara': 11, 'mch': 16, 'ship': 14}
GROUP = 'names:{}+8'

KANA = {}
_rows = """a i u e o|ka ki ku ke ko|sa shi su se so|ta chi tsu te to|na ni nu ne no|ha hi fu he ho|ma mi mu me mo|ya - yu - yo|ra ri ru re ro|wa - - - wo"""
_ks = ['アイウエオ', 'カキクケコ', 'サシスセソ', 'タチツテト', 'ナニヌネノ', 'ハヒフヘホ', 'マミムメモ', 'ヤ_ユ_ヨ', 'ラリルレロ', 'ワ___ヲ']
for kana, roms in zip(_ks, _rows.split('|')):
    for k, r in zip(kana, roms.split()):
        if k != '_':
            KANA[k] = r
for k, r in zip('ガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポ',
                'ga gi gu ge go za ji zu ze zo da ji zu de do ba bi bu be bo pa pi pu pe po'.split()):
    KANA[k] = r
KANA.update({'ン': 'n', 'ヴ': 'vu', 'ァ': 'a', 'ィ': 'i', 'ゥ': 'u', 'ェ': 'e', 'ォ': 'o', 'ャ': 'ya', 'ュ': 'yu', 'ョ': 'yo'})


def romaji(s):
    s = unicodedata.normalize('NFKC', s)
    out = ''
    for i, c in enumerate(s):
        if c == 'ッ':
            out += '-'
        elif c == 'ー':
            out += out[-1:] if out else ''
        elif c in 'ャュョ' and out.endswith('i'):
            out = out[:-1] + KANA[c]
        elif c in 'ァィゥェォ' and out:
            out = out[:-1] + KANA[c]
        elif c in KANA:
            if out.endswith('-'):
                out = out[:-1] + KANA[c][0]
            out += KANA[c]
        elif c.isascii() and c.isalnum():
            out += c.lower()
    return out


def squash(s):
    s = s.lower().replace('l', 'r').replace('v', 'b').replace('th', 's').replace('c', 'k')
    return re.sub(r'[^a-z0-9]', '', s)


def best_span(kana, english):
    words = english.split()
    r = squash(romaji(kana))
    best = (0, '')
    for i in range(len(words)):
        for j in range(i + 1, min(len(words), i + 3) + 1):
            cand = ' '.join(words[i:j])
            sc = difflib.SequenceMatcher(None, r, squash(cand)).ratio()
            if sc > best[0]:
                best = (sc, cand)
    return best


def proposals():
    nt = json.load(open(NT, encoding='utf-8'))
    es = {r['va']: r for r in json.load(open(ES, encoding='utf-8'))['rows']}
    en = lambda f: (es.get(f['va']) or {}).get('en') or ''
    out = {}
    for t in LIMIT:
        for r in nt[t]:
            if '+8' not in r or '+4' not in r:
                continue
            va, jp = r['+8']['va'], r['+8']['jp']
            e4, e0 = en(r['+4']), en(r.get('+0', r['+4']))
            lim = LIMIT[t]
            prop, how = '', ''
            if t == 'chara':
                sc, span = max(best_span(jp, e4), best_span(jp, e0))
                if e4 and len(e4) <= lim:
                    prop, how = e4, 'display name'
                elif sc >= 0.6 and len(span) <= lim:
                    prop, how = span, f'name span ({sc:.2f})'
            else:
                for cand, h in ((e4, 'display name'), (e0, 'full name'),
                                (re.sub(r'-class$', '', e4), 'class name')):
                    if cand and len(cand) <= lim:
                        prop, how = cand, h; break
            num = re.search(r'([0-9]+)$', unicodedata.normalize('NFKC', jp))
            if prop and num and not prop.endswith(num.group(1)):
                prop, how = '', ''          # numbered variants (soldier 1/2/3): by hand
            cur = out.get(va)
            if cur is None or (not cur['en'] and prop):
                out[va] = dict(va=va, jp=jp, en=prop, group=GROUP.format(t), how=how, display=e4, full=e0, table=t)
    return out


def draft(write):
    ps = proposals()
    d = json.load(open(ES, encoding='utf-8'))
    have = {r['va']: r for r in d['rows']}
    n = 0
    for va, p in ps.items():
        r = have.get(va)
        if r is None:
            r = dict(va=va, jp=p['jp'], en='', group=p['group'], status='draft', skip=False, notes='')
            d['rows'].append(r); have[va] = r
        if not r.get('en') and p['en']:
            r['en'] = p['en']; r['notes'] = f'[short name] from {p["how"]}'; n += 1
    print(len(ps), 'short names;', n, 'filled;', sum(1 for p in ps.values() if not have[p['va']].get('en')), 'left')
    if write:
        json.dump(d, open(ES, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('WRITTEN')


def todo():
    es = {r['va']: r for r in json.load(open(ES, encoding='utf-8'))['rows']}
    for va, p in proposals().items():
        if not (es.get(va) or {}).get('en'):
            print(f'{p["table"]} {va} {p["jp"]} | {p["display"]} | {p["full"]}')


if __name__ == '__main__':
    {'draft': lambda: draft('--write' in sys.argv), 'todo': todo}[sys.argv[1]]()
