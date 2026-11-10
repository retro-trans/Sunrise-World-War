"""Translation coverage: per table, rows / segments with English, and Japanese characters
that would remain in the built rows (debug_tools_guide step 8, text side).

  py -3.11 tools/coverage.py [--write]     (--write saves docs/coverage.json)

Built rows are produced exactly as tools/build.py does (translations.load_tables), then
scanned for kana/kanji. The ELF side reports elf_strings.json rows with English.
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import translations
from textcodec import decode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JP = re.compile('[぀-ヿ一-鿿]')


def main():
    inv = json.load(open(os.path.join(ROOT, 'work/source/text_inventory.json')))
    built = {name: raw for name, n, raw in translations.load_tables(lambda s: None, strict=False)}
    rep = []; tot_src = tot_left = 0
    for t in inv:
        name = t['table']
        src = translations.source_rows(name)
        raw = built.get(name) or [None] * len(src)
        done = left = srcjp = 0
        for r, b in zip(src, raw):
            j = len(JP.findall(r['jp']))
            srcjp += j
            if b is not None:
                k = len(JP.findall(decode(b)))
                left += k
                done += k < j
            else:
                left += j
        rep.append(dict(table=name, pack=t.get('pack'), rows=len(src), rows_translated=done,
                        jp_chars=srcjp, jp_chars_left=left))
        tot_src += srcjp; tot_left += left
    for r in rep:
        pct = 100 * (1 - r['jp_chars_left'] / r['jp_chars']) if r['jp_chars'] else 100
        print(f"{r['table']} {r['pack'] or '':16s} rows {r['rows_translated']:5d}/{r['rows']:5d}  {pct:5.1f}%")
    print(f'TOTAL Japanese characters translated: {100 * (1 - tot_left / tot_src):.2f}% '
          f'({tot_src - tot_left} of {tot_src})')
    es = json.load(open(os.path.join(ROOT, 'work/translation/en/elf_strings.json'), encoding='utf-8'))['rows']
    print(f"ELF strings with English: {sum(1 for r in es if r.get('en'))} of {len(es)}")
    if '--write' in sys.argv:
        json.dump(dict(tables=rep, total_jp=tot_src, left_jp=tot_left,
                       elf=dict(rows=len(es), translated=sum(1 for r in es if r.get('en')))),
                  open(os.path.join(ROOT, 'docs/coverage.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
