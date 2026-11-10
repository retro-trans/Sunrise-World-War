"""Write the executable changes between two builds into the running game (PINE).

  py -3.11 tools/dbg/hotpatch.py OLD_ELF NEW_ELF --run

For testing a new build inside a savestate made with an older one (debug_tools_guide
step 6). Only the loaded image is patched: data the game already copied (e.g. town
house names) changes only when the game builds it again. Writes data first and the
code entry points (any word in .text, below 0x210000) last.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pine

VA_TO_FILE = 0xFF000


def runs(a, b):
    out = []; i = 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and (a[j] != b[j] or a[j:j + 8] != b[j:j + 8]):
                j += 1
            out.append((i + VA_TO_FILE, b[i:j])); i = j
        else:
            i += 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('old'); ap.add_argument('new'); ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    old, new = open(a.old, 'rb').read(), open(a.new, 'rb').read()
    assert len(old) == len(new), 'builds differ in size'
    rs = runs(old, new)
    rs.sort(key=lambda r: r[0] < 0x210000)          # data/patch region first, .text hooks last
    print(f'{len(rs)} runs, {sum(len(d) for _, d in rs)} bytes')
    if not a.run:
        print('dry run: --run writes them'); return
    p = pine.Pine()
    for va, data in rs:
        p.write(va, data)
    bad = [hex(va) for va, data in rs if p.read(va, len(data)) != data]
    print('written; verify mismatches:', bad or 'none')


if __name__ == '__main__':
    main()
