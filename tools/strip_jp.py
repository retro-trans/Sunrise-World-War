"""Write commit-safe copies of translation drafts: work/translation/en/<table>.en.json
with the Japanese `jp` field removed (AGENTS.md: Japanese script never goes to git).

  py -3.11 tools/strip_jp.py            dry run
  py -3.11 tools/strip_jp.py --write
  py -3.11 tools/strip_jp.py --check    fail if any .en.json is stale or holds kana/kanji
"""
import glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, 'work/translation/en')
GFX_DRAFT = os.path.join(ROOT, 'work/translation/gfx/gfx_text.json')
JP = re.compile('[぀-ヿ一-鿿]')


# translator notes quote source words; the committed copy keeps a marker instead
JP_RUN = re.compile('[぀-ヿ一-鿿　-〿＀-￯「」『』…～]+')


def stripped(path):
    t = json.load(open(path, encoding='utf-8'))
    for r in t.get('rows', []):
        r.pop('jp', None)
        for sg in r.get('segments') or []:
            sg.pop('jp', None)
        if r.get('notes'):
            r['notes'] = JP_RUN.sub('[jp]', r['notes'])
    return json.dumps(t, ensure_ascii=False, indent=1)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    bad = 0
    drafts = glob.glob(os.path.join(DRAFTS, '*.json'))
    if os.path.isfile(GFX_DRAFT):
        drafts.append(GFX_DRAFT)
    for p in sorted(drafts):
        if p.endswith('.en.json'):
            continue
        out = p[:-5] + '.en.json'
        s = stripped(p)
        kana = len(JP.findall(s))
        if mode == '--check':
            if not os.path.exists(out) or open(out, encoding='utf-8').read() != s:
                print('stale:', out); bad += 1
            if kana:
                print(f'note: {out} keeps {kana} Japanese characters (names/UI terms only are allowed)')
        elif mode == '--write':
            open(out, 'w', encoding='utf-8').write(s)
            print('wrote', os.path.relpath(out, ROOT), f'({kana} JP chars remain: names/UI terms)')
        else:
            print('would write', os.path.relpath(out, ROOT))
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
