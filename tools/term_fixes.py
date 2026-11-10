"""Apply work/glossary/term_fixes.json to drafts and the glossary (BASE_RULES: names are
fixed by script, after agent edits).

  py -3.11 tools/term_fixes.py            dry run: counts and sample changes
  py -3.11 tools/term_fixes.py --write
"""
import glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = json.load(open(os.path.join(ROOT, 'work/glossary/term_fixes.json'), encoding='utf-8'))


def _ws(pat):
    """a literal space in a pattern also matches a line break (names wrap across lines)"""
    return pat.replace(' ', r'[ ' + chr(92) + 'n]')


def fix(s, counts):
    for pat, rep, _ in F['fixes']:
        def sub(m, rep=rep):
            out = m.expand(rep)
            if chr(10) in m.group(0) and ' ' in out:      # keep the line break near where it was
                k = m.group(0).index(chr(10))
                spaces = [i for i, c in enumerate(out) if c == ' ']
                j = min(spaces, key=lambda i: abs(i - k))
                out = out[:j] + chr(10) + out[j + 1:]
            return out
        s, n = re.subn(_ws(pat), sub, s)
        counts[pat] = counts.get(pat, 0) + n
    return s


def main():
    write = '--write' in sys.argv
    counts = {}; samples = []
    for p in glob.glob(os.path.join(ROOT, 'work/translation/en/*.json')):
        if p.endswith('.en.json'):
            continue
        d = json.load(open(p, encoding='utf-8'))
        for r in d.get('rows', []):
            if r.get('en'):
                new = fix(r['en'], counts)
                if r.get('jp') and '通称' in r['jp'] and '■通称■' in r['jp']:
                    for a, b, _ in F['header_fixes']:
                        new = new.replace(a, b)
                if new != r['en'] and len(samples) < 8:
                    samples.append((os.path.basename(p), r.get('id', r.get('va'))))
                r['en'] = new
            for sg in r.get('segments') or []:
                if sg.get('en'):
                    new = fix(sg['en'], counts)
                    if new != sg['en'] and len(samples) < 40:
                        samples.append((os.path.basename(p), r.get('id'), sg['en'][:70], new[:70]))
                    sg['en'] = new
        if write:
            json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    gp = os.path.join(ROOT, 'work/glossary/glossary.json')
    g = json.load(open(gp, encoding='utf-8'))
    for e in g['entries']:
        if e.get('en'):
            e['en'] = fix(e['en'], counts)
    if write:
        json.dump(g, open(gp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k, v in counts.items():
        if v:
            print(f'{v:5d}  {k}')
    for x in samples:
        print('  ', x)
    print('WRITTEN' if write else 'DRY RUN: --write applies')


if __name__ == '__main__':
    main()
