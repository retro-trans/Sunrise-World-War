"""Disassemble SLPS_252.70 by symbol name or address range (capstone, MIPS64 LE)."""
import sys, struct, bisect
import capstone
sys.path.insert(0, __import__('os').path.dirname(__file__))
from elfsyms import load_symbols

ELF = 'work/source/SLPS_252.70'

class Elf:
    def __init__(self, path=ELF):
        self.d = open(path, 'rb').read()
        phoff = struct.unpack_from('<I', self.d, 0x1c)[0]
        phnum = struct.unpack_from('<H', self.d, 0x2c)[0]
        self.segs = [struct.unpack_from('<8I', self.d, phoff + i * 32) for i in range(phnum)]
        self.syms = load_symbols(path)
        self.addr = [s[0] for s in self.syms]
        self.byname = {s[3]: s for s in self.syms}

    def off(self, va):
        for t, o, v, p, fs, ms, fl, al in self.segs:
            if v <= va < v + fs:
                return o + va - v
        return None

    def read(self, va, n):
        o = self.off(va)
        return self.d[o:o + n]

    def u32(self, va):
        return struct.unpack('<I', self.read(va, 4))[0]

    def name_at(self, va):
        i = bisect.bisect_right(self.addr, va) - 1
        if i >= 0:
            v, s, t, n = self.syms[i]
            if va == v: return n
            if va < v + max(s, 1): return f'{n}+{va - v:#x}'
        return None

    def cstr(self, va, enc='cp932'):
        o = self.off(va)
        if o is None: return None
        e = self.d.index(b'\0', o)
        return self.d[o:e].decode(enc, 'replace')

def disasm(elf, start, size):
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS64 + capstone.CS_MODE_LITTLE_ENDIAN)
    code = elf.read(start, size)
    out = []
    for i in md.disasm(code, start):
        note = ''
        if i.mnemonic in ('jal', 'j', 'beq', 'bne', 'b', 'bnez', 'beqz', 'bal') and i.op_str:
            try:
                tgt = int(i.op_str.split(',')[-1].strip(), 16)
                n = elf.name_at(tgt)
                if n: note = '  ; ' + n
            except ValueError:
                pass
        lab = elf.byname.get(elf.name_at(i.address)) if False else None
        if elf.name_at(i.address) and '+' not in elf.name_at(i.address):
            out.append(f'{elf.name_at(i.address)}:')
        out.append(f'  {i.address:08x}: {i.bytes.hex()}  {i.mnemonic:8s} {i.op_str}{note}')
    return out

if __name__ == '__main__':
    elf = Elf()
    a = sys.argv[1]
    if a in elf.byname:
        v, s, t, n = elf.byname[a]
        size = int(sys.argv[2], 0) if len(sys.argv) > 2 else s
    else:
        v, size = int(a, 0), int(sys.argv[2], 0)
    print('\n'.join(disasm(elf, v, size)))
