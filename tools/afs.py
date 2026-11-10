"""CRI AFS archive reader (works on a file object + base offset)."""
import struct

class AFS:
    def __init__(self, f, base=0):
        self.f, self.base = f, base
        f.seek(base)
        hdr = f.read(8)
        assert hdr[:4] == b'AFS\x00', hdr
        n = struct.unpack('<I', hdr[4:8])[0]
        toc = f.read(8 * (n + 1))
        self.entries = [struct.unpack('<II', toc[i*8:i*8+8]) for i in range(n)]
        self.names = [None] * n
        nt_off, nt_size = struct.unpack('<II', toc[n*8:n*8+8])
        if nt_off == 0:  # name table pointer may sit just before first file
            f.seek(base + self.entries[0][0] - 8)
            nt_off, nt_size = struct.unpack('<II', f.read(8))
        if nt_off and nt_size == n * 48:
            f.seek(base + nt_off)
            nt = f.read(nt_size)
            for i in range(n):
                e = nt[i*48:i*48+48]
                self.names[i] = e[:32].split(b'\0')[0].decode('ascii', 'replace')
        self.nt = (nt_off, nt_size)

    def read(self, i):
        off, size = self.entries[i]
        self.f.seek(self.base + off)
        return self.f.read(size)
