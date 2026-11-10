"""Scan binary data for Shift-JIS text runs (full + half width)."""
import re, sys

def is_lead(b): return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF
def is_trail(b): return 0x40 <= b <= 0xFC and b != 0x7F

def runs(data, min_dbcs=3):
    """Yield (offset, bytes) of runs containing >= min_dbcs double-byte chars."""
    i, n = 0, len(data)
    while i < n:
        j, dbcs = i, 0
        while j < n:
            b = data[j]
            if is_lead(b) and j + 1 < n and is_trail(data[j+1]):
                # restrict to plausible text rows (0x81-0x84 symbols/kana, 0x88-0x9F/0xE0-0xEA kanji)
                if b in (0x85, 0x86, 0x87) or b > 0xEA: break
                dbcs += 1; j += 2
            elif 0x20 <= b < 0x7F or 0xA1 <= b <= 0xDF or b in (0x0A, 0x0D):
                j += 1
            else:
                break
        if dbcs >= min_dbcs:
            yield i, data[i:j]
            i = j
        else:
            i = max(j, i + 1)

if __name__ == '__main__':
    import os
    tot = 0
    for path in sys.argv[1:]:
        d = open(path, 'rb').read()
        rs = list(runs(d))
        c = sum(len(r) for _, r in rs)
        if rs:
            print(f'{os.path.basename(path)}\t{len(rs)}\t{c}')
