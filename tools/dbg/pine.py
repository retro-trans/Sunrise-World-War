"""PINE IPC client for the project's portable PCSX2.

PINE gives memory read/write, savestate save/load and status. It has no CPU
breakpoints or registers. The project's input/preview monitors do not add them.

Port: env SWW_PINE_PORT (default 28027, set in work/emulator/pcsx2/inis/PCSX2.ini).
"""
import os, socket, struct, time

PORT = int(os.environ.get('SWW_PINE_PORT', '28027'))

READ8, READ16, READ32, READ64 = 0, 1, 2, 3
WRITE8, WRITE16, WRITE32, WRITE64 = 4, 5, 6, 7
VERSION, SAVESTATE, LOADSTATE, TITLE, ID, UUID, GAMEVER, STATUS = 8, 9, 10, 11, 12, 13, 14, 15
STATUS_NAMES = {0: 'running', 1: 'paused', 2: 'shutdown'}
MAX_BATCH = 0x8000  # bytes of reply per batch, well under PINE's 650 KiB buffer


class Pine:
    def __init__(self, port=PORT, timeout=10.0):
        self.s = socket.create_connection(('127.0.0.1', port), timeout=timeout)
        self.s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def close(self):
        self.s.close()

    def _recv(self, n):
        buf = bytearray()
        while len(buf) < n:
            c = self.s.recv(n - len(buf))
            if not c:
                raise ConnectionError('PINE closed')
            buf += c
        return bytes(buf)

    def _call(self, payload):
        self.s.sendall(struct.pack('<I', len(payload) + 4) + payload)
        size = struct.unpack('<I', self._recv(4))[0]
        body = self._recv(size - 4)
        if body[0] != 0:
            raise IOError('PINE command failed')
        return body[1:]

    # --- memory -----------------------------------------------------------
    def read32(self, addr):
        return struct.unpack('<I', self._call(struct.pack('<BI', READ32, addr)))[0]

    def write32(self, addr, v):
        self._call(struct.pack('<BII', WRITE32, addr, v & 0xFFFFFFFF))

    def read8(self, addr):
        return self._call(struct.pack('<BI', READ8, addr))[0]

    def write8(self, addr, v):
        self._call(struct.pack('<BIB', WRITE8, addr, v & 0xFF))

    def read(self, addr, size):
        """Read size bytes using batched 64-bit reads (addr need not be aligned)."""
        start = addr & ~7
        end = (addr + size + 7) & ~7
        out = bytearray()
        a = start
        while a < end:
            n = min((end - a) // 8, MAX_BATCH // 8)
            payload = b''.join(struct.pack('<BI', READ64, a + 8 * k) for k in range(n))
            r = self._call(payload)
            out += r[:8 * n]
            a += 8 * n
        return bytes(out[addr - start:addr - start + size])

    def write(self, addr, data):
        """Write bytes; aligned middle part with 64-bit writes, edges byte-wise."""
        data = bytes(data)
        ops = []
        i = 0
        while i < len(data):
            a = addr + i
            if a % 8 == 0 and len(data) - i >= 8:
                ops.append(struct.pack('<BIQ', WRITE64, a, struct.unpack_from('<Q', data, i)[0])); i += 8
            elif a % 4 == 0 and len(data) - i >= 4:
                ops.append(struct.pack('<BII', WRITE32, a, struct.unpack_from('<I', data, i)[0])); i += 4
            else:
                ops.append(struct.pack('<BIB', WRITE8, a, data[i])); i += 1
            if len(ops) >= 2000:
                self._call(b''.join(ops)); ops = []
        if ops:
            self._call(b''.join(ops))

    # --- emulator ---------------------------------------------------------
    def status(self):
        return STATUS_NAMES.get(struct.unpack('<I', self._call(bytes([STATUS])))[0], '?')

    def _string(self, op):
        r = self._call(bytes([op]))
        n = struct.unpack_from('<I', r)[0]
        return r[4:4 + n].rstrip(b'\0').decode('utf-8', 'replace')

    def title(self):
        return self._string(TITLE)

    def game_id(self):
        return self._string(ID)

    def save_state(self, slot):
        self._call(bytes([SAVESTATE, slot]))

    def load_state(self, slot):
        self._call(bytes([LOADSTATE, slot]))


def connect(retries=60, delay=1.0):
    last = None
    for _ in range(retries):
        try:
            return Pine()
        except OSError as e:
            last = e
            time.sleep(delay)
    raise ConnectionError('cannot reach PINE on port %d: %s' % (PORT, last))
