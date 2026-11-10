"""Minimal ISO9660 reader for the 2048-byte/sector image."""
import struct, sys

SECTOR = 2048

class ISO:
    def __init__(self, path):
        self.f = open(path, 'rb')
        pvd = self.read_sectors(16, 1)
        assert pvd[1:6] == b'CD001', pvd[:8]
        self.system_id = pvd[8:40].decode('ascii', 'replace').strip()
        self.volume_id = pvd[40:72].decode('ascii', 'replace').strip()
        self.volume_blocks = struct.unpack('<I', pvd[80:84])[0]
        self.root = self._parse_rec(pvd[156:156 + 34])

    def read_sectors(self, lba, count):
        self.f.seek(lba * SECTOR)
        return self.f.read(count * SECTOR)

    def read_file(self, rec):
        self.f.seek(rec['lba'] * SECTOR)
        return self.f.read(rec['size'])

    @staticmethod
    def _parse_rec(b):
        ln = b[0]
        lba = struct.unpack('<I', b[2:6])[0]
        size = struct.unpack('<I', b[10:14])[0]
        flags = b[25]
        nl = b[32]
        name = b[33:33 + nl]
        return dict(len=ln, lba=lba, size=size, flags=flags, rawname=name,
                    name=name.decode('ascii', 'replace'), isdir=bool(flags & 2))

    def listdir(self, rec):
        data = self.read_sectors(rec['lba'], (rec['size'] + SECTOR - 1) // SECTOR)
        out, pos = [], 0
        while pos < len(data):
            ln = data[pos]
            if ln == 0:
                pos = (pos // SECTOR + 1) * SECTOR
                continue
            r = self._parse_rec(data[pos:pos + ln])
            r['recoff'] = rec['lba'] * SECTOR + pos
            pos += ln
            if r['rawname'] in (b'\x00', b'\x01'):
                continue
            r['name'] = r['name'].split(';')[0]
            out.append(r)
        return out

    def walk(self, rec=None, path=''):
        rec = rec or self.root
        for r in self.listdir(rec):
            p = path + '/' + r['name']
            if r['isdir']:
                yield p, r
                yield from self.walk(r, p)
            else:
                yield p, r

if __name__ == '__main__':
    iso = ISO(sys.argv[1])
    print(iso.system_id, '|', iso.volume_id, '| blocks', iso.volume_blocks)
    for p, r in iso.walk():
        print(f"{r['lba']:8d} {r['size']:10d} {'D' if r['isdir'] else ' '} {p}")
