"""List functions with no references (jal/j targets, data words, lui+addiu pairs)
and report the largest contiguous unreferenced runs in .text."""
import sys, os, struct, collections
sys.path.insert(0, os.path.dirname(__file__))
from disasm import Elf

def referenced(elf):
    ref = collections.Counter()
    o0 = elf.off(0x100000); n = 0x114fb4
    hi = {}
    for k in range(0, n, 4):
        w = struct.unpack_from('<I', elf.d, o0 + k)[0]
        op = w >> 26
        if op in (2, 3):
            ref[(0x100000 & 0xF0000000) | ((w & 0x3FFFFFF) << 2)] += 1
        rt = (w >> 16) & 31; rs = (w >> 21) & 31; imm = w & 0xFFFF
        if op == 0x0F:
            hi[rt] = imm << 16
        elif op in (0x09, 0x19) and rs in hi:
            ref[(hi[rs] + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xFFFFFFFF] += 1
        elif op == 0x0D and rs in hi:
            ref[hi[rs] | imm] += 1
    for seg in elf.segs:
        o, v, fs = seg[1], seg[2], seg[4]
        if v == 0x100000: continue
        for k in range(0, fs - 3, 4):
            ref[struct.unpack_from('<I', elf.d, o + k)[0]] += 1
    return ref

if __name__ == '__main__':
    elf = Elf()
    ref = referenced(elf)
    funcs = [s for s in elf.syms if s[2] == 2 and 0x100000 <= s[0] < 0x214fb4 and s[1]]
    dead = [f for f in funcs if ref[f[0]] == 0]
    runs = []; cur = []
    for f in funcs:
        if ref[f[0]] == 0:
            if cur and cur[-1][0] + cur[-1][1] < f[0] - 8:
                runs.append(cur); cur = []
            cur.append(f)
        else:
            if cur: runs.append(cur); cur = []
    if cur: runs.append(cur)
    runs.sort(key=lambda r: -(r[-1][0] + r[-1][1] - r[0][0]))
    print('functions', len(funcs), 'unreferenced', len(dead), 'bytes', sum(f[1] for f in dead))
    for r in runs[:25]:
        print(f'{r[0][0]:08x}-{r[-1][0]+r[-1][1]:08x} {r[-1][0]+r[-1][1]-r[0][0]:6x}', ' '.join(f[3] for f in r)[:150])
