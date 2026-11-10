"""Find jal/j callers of a function in SLPS_252.70 .text."""
import sys, struct
sys.path.insert(0, __import__('os').path.dirname(__file__))
from disasm import Elf

def callers(elf, target):
    out = []
    t0, o0, s0 = 0x100000, elf.off(0x100000), 0x114fb4
    word = (target >> 2) & 0x3FFFFFF
    for i in range(0, s0, 4):
        w = struct.unpack_from('<I', elf.d, o0 + i)[0]
        if (w >> 26) in (2, 3) and (w & 0x3FFFFFF) == word:
            out.append(t0 + i)
    return out

if __name__ == '__main__':
    elf = Elf()
    for a in sys.argv[1:]:
        t = elf.byname[a][0] if a in elf.byname else int(a, 0)
        print(a)
        for c in callers(elf, t):
            print(f'  {c:08x} {elf.name_at(c)}')
