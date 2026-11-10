"""ELF symbol table dump for SLPS_252.70."""
import struct, sys

def load_symbols(path):
    d = open(path, 'rb').read()
    e_shoff = struct.unpack_from('<I', d, 0x20)[0]
    shnum, shstr = struct.unpack_from('<HH', d, 0x30)
    secs = [struct.unpack_from('<10I', d, e_shoff + i * 40) for i in range(shnum)]
    so = secs[shstr][4]
    name = lambda off, base: d[base + off:d.index(b'\0', base + off)].decode('ascii', 'replace')
    bynm = {name(s[0], so): s for s in secs}
    st, sr = bynm['.symtab'], bynm['.strtab']
    syms = []
    for i in range(st[5] // 16):
        nm, val, size, info, other, shndx = struct.unpack_from('<IIIBBH', d, st[4] + i * 16)
        if nm:
            syms.append((val, size, info & 0xF, name(nm, sr[4])))
    return sorted(syms)

if __name__ == '__main__':
    for v, s, t, n in load_symbols(sys.argv[1]):
        print(f'{v:08x} {s:6x} {t} {n}')
