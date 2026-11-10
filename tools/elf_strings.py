"""Catalog NUL-terminated Shift-JIS strings in SLPS_252.70 data sections and count
pointer references to each (data words + lui/addiu or lui/ori pairs in .text).
Accepts the whole encoding (ASCII, half-width kana, double-byte)."""
import sys, os, struct, json, collections
sys.path.insert(0, os.path.dirname(__file__))
from disasm import Elf

DATA_RANGES = [(0x216180, 0x2b8094), (0x2b8100, 0x2e8cb8), (0x2ea800, 0x2f0ba4)]

def valid_sjis(b):
    i = 0; dbcs = 0
    while i < len(b):
        c = b[i]
        if 0x20 <= c < 0x7F or c in (9, 10, 13) or 0xA1 <= c <= 0xDF:
            i += 1
        elif (0x81 <= c <= 0x9F or 0xE0 <= c <= 0xFC) and i + 1 < len(b) and 0x40 <= b[i+1] <= 0xFC and b[i+1] != 0x7F:
            i += 2; dbcs += 1
        else:
            return -1
    return dbcs

def scan(elf):
    out = []
    for lo, hi in DATA_RANGES:
        o0 = elf.off(lo); d = elf.d[o0:o0 + hi - lo]
        i = 0
        while i < len(d):
            if d[i] == 0:
                i += 1; continue
            e = d.find(b'\0', i)
            if e < 0: break
            s = d[i:e]
            n = valid_sjis(s)
            if n > 0 or (n == 0 and (i % 4 == 0) and len(s) >= 2 and False):
                try:
                    txt = s.decode('cp932')
                    out.append(dict(va=lo + i, size=len(s), jp=txt))
                except UnicodeDecodeError:
                    pass
            i = e + 1
    return out

def refs(elf, targets):
    """Count references: aligned data words and lui+addiu/ori pairs in .text."""
    tset = set(targets); cnt = collections.Counter(); where = collections.defaultdict(list)
    for lo, hi in DATA_RANGES:
        o0 = elf.off(lo)
        for a in range(lo, hi - 3, 4):
            w = struct.unpack_from('<I', elf.d, o0 + a - lo)[0]
            if w in tset:
                cnt[w] += 1; where[w].append(a)
    o0 = elf.off(0x100000); n = 0x114fb4
    hi = {}
    for k in range(0, n, 4):
        w = struct.unpack_from('<I', elf.d, o0 + k)[0]
        op = w >> 26; rt = (w >> 16) & 31; rs = (w >> 21) & 31; imm = w & 0xFFFF
        if op == 0x0F:
            hi[rt] = (imm << 16, k)
        elif op in (0x09, 0x0D, 0x19) and rs in hi and k - hi[rs][1] < 0x80:
            v = hi[rs][0] + (imm - 0x10000 if (imm & 0x8000 and op != 0x0D) else imm)
            v &= 0xFFFFFFFF
            if v in tset:
                cnt[v] += 1; where[v].append(0x100000 + k)
    return cnt, where

if __name__ == '__main__':
    elf = Elf()
    ss = scan(elf)
    cnt, where = refs(elf, [s['va'] for s in ss])
    for s in ss:
        s['refs'] = cnt[s['va']]; s['ref_sites'] = [hex(x) for x in where[s['va']][:8]]
    json.dump(ss, open('work/source/elf_strings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    jp = [s for s in ss if any(ord(c) > 0x7F for c in s['jp'])]
    print('strings', len(ss), 'with JP', len(jp), 'JP referenced', sum(1 for s in jp if s['refs']))
