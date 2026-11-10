"""Offline reader for PCSX2 .p2s savestates (zip; members zstd-compressed, method 93).

  ee   = State(path).ee()        # 32 MiB main RAM (index = EE physical address)
  png  = State(path).screenshot()
  gs   = State(path).member('GS.bin')

usage:
  py -3.11 tools/dbg/sstate.py shot  STATE.p2s out.png
  py -3.11 tools/dbg/sstate.py dump  STATE.p2s ADDR SIZE      (hex)
  py -3.11 tools/dbg/sstate.py diff  A.p2s B.p2s [START END]  (EE RAM word diff)
"""
import sys, zipfile, struct
import zstandard


class State:
    def __init__(self, path):
        self.path = path
        self.z = zipfile.ZipFile(path)
        self._cache = {}

    def member(self, name):
        if name in self._cache:
            return self._cache[name]
        info = self.z.getinfo(name)
        if info.compress_type in (0, 8):
            data = self.z.read(name)
        else:
            with open(self.path, 'rb') as f:
                f.seek(info.header_offset)
                h = f.read(30)
                n, m = struct.unpack_from('<HH', h, 26)
                f.seek(info.header_offset + 30 + n + m)
                raw = f.read(info.compress_size)
            data = zstandard.ZstdDecompressor().decompress(raw, max_output_size=info.file_size)
        self._cache[name] = data
        return data

    def ee(self):
        return self.member('eeMemory.bin')

    def screenshot(self):
        return self.member('Screenshot.png')


def main():
    cmd = sys.argv[1]
    if cmd == 'shot':
        open(sys.argv[3], 'wb').write(State(sys.argv[2]).screenshot())
    elif cmd == 'dump':
        a = int(sys.argv[3], 16); n = int(sys.argv[4], 16)
        d = State(sys.argv[2]).ee()[a & 0x1FFFFFF:(a & 0x1FFFFFF) + n]
        for i in range(0, len(d), 16):
            print('%08X  %s' % (a + i, d[i:i + 16].hex(' ')))
    elif cmd == 'diff':
        A = State(sys.argv[2]).ee(); B = State(sys.argv[3]).ee()
        s = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0
        e = int(sys.argv[5], 16) if len(sys.argv) > 5 else len(A)
        for i in range(s, e, 4):
            if A[i:i + 4] != B[i:i + 4]:
                print('%08X  %08X -> %08X' % (i, struct.unpack_from('<I', A, i)[0], struct.unpack_from('<I', B, i)[0]))


if __name__ == '__main__':
    main()
