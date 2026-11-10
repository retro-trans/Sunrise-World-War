"""PS2 movies (MOVIE.AFS / MOVIE2.AFS): MPEG program stream with an IPU video stream.

Container: 2048-byte MPEG-PS packs; video = private stream 1 (0xBD) packets whose payload
concatenates to a raw "ipum" stream (header 'ipum', u32 size, u16 width, u16 height,
u32 frames; then intra-only frames, decodable by ffmpeg's ipu decoder).

  py -3.11 tools/ipu.py list                      movie names, archive, size
  py -3.11 tools/ipu.py extract NAME OUT_DIR      NAME.pss + NAME.ipu (raw video)
  py -3.11 tools/ipu.py info FILE.pss             pack / stream summary
"""
import collections, os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, 'Sunrise World War (Japan).iso')
MOVIE_TABLE = 0x2247E4          # 12 bytes per movie: name pointer, size, 0 (index from 1)


def movies():
    """[(name, size, archive name, index in archive)] in table order."""
    from disasm import Elf
    import iso9660, afs
    e = Elf()
    tab = []
    for i in range(1, 4000):
        p = e.u32(MOVIE_TABLE + 12 * i)
        if not 0x200000 < p < 0x300000:
            break
        tab.append((e.cstr(p), e.u32(MOVIE_TABLE + 12 * i + 4)))
    iso = iso9660.ISO(ORIG)
    out = []; k = 0
    for an in ('MOVIE.AFS', 'MOVIE2.AFS'):
        x = [r for p, r in iso.walk() if r['name'] == an][0]
        a = afs.AFS(iso.f, x['lba'] * 2048)
        for j in range(len(a.entries)):
            name, size = tab[k]
            assert a.entries[j][1] == size, (name, a.entries[j], size)
            out.append((name, size, an, j)); k += 1
    return out


def read_movie(name):
    import iso9660, afs
    for n, size, an, j in movies():
        if n == name:
            iso = iso9660.ISO(ORIG)
            x = [r for p, r in iso.walk() if r['name'] == an][0]
            return afs.AFS(iso.f, x['lba'] * 2048).read(j)
    raise KeyError(name)


def packets(d):
    """[(pack offset, stream id, sub id, payload offset, payload length)] for every PES
    packet. Private stream 1 carries a sub-stream byte? -> reported as sub (None if not)."""
    out = []; pos = 0
    while pos + 4 <= len(d):
        code = d[pos:pos + 4]
        if code == b'\x00\x00\x01\xba':
            if d[pos + 4] >> 6 == 1:                    # MPEG-2 pack header
                stuff = d[pos + 13] & 7
                pos += 14 + stuff
            else:                                       # MPEG-1
                pos += 12
            continue
        if code == b'\x00\x00\x01\xb9':                 # program end
            pos += 4; continue
        if code[:3] != b'\x00\x00\x01':
            pos += 1; continue
        sid = code[3]
        ln = struct.unpack('>H', d[pos + 4:pos + 6])[0]
        body = pos + 6
        if sid in (0xBB, 0xBE, 0xBF):                   # system header, padding, private 2
            out.append((pos, sid, None, body, ln)); pos = body + ln; continue
        hl = d[body + 2]
        po = body + 3 + hl
        out.append((pos, sid, None, po, body + ln - po))
        pos = body + ln
    return out


VIDEO_SUB = bytes([0xFF, 0xC0, 0, 0])   # private-1 sub-header: video (IPU)
AUDIO_SUB = bytes([0xFF, 0x90, 0, 0])   # audio (SPU ADPCM)


def video_stream(d):
    """(raw ipum bytes, [(payload offset, length)] of the video bytes in each packet;
    the 4-byte sub-header is not part of the stream)"""
    chunks = [(po + 4, ln - 4) for _, sid, _, po, ln in packets(d)
              if sid == 0xBD and d[po:po + 4] == VIDEO_SUB]
    raw = b''.join(d[po:po + ln] for po, ln in chunks)
    return raw, chunks


def info(path):
    d = open(path, 'rb').read()
    ps = packets(d)
    c = collections.Counter(p[1] for p in ps)
    print({hex(k): v for k, v in c.items()}, 'packs', d.count(b'\x00\x00\x01\xba'), 'size', len(d))
    raw, chunks = video_stream(d)
    print('private-1 payload', len(raw), 'head', raw[:16].hex(' '))
    if raw[:4] == b'ipum':
        size, w, h, n = struct.unpack('<IHHI', raw[4:16])
        print('ipum size', size, 'w', w, 'h', h, 'frames', n)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'list':
        for m in movies():
            print(*m)
    elif cmd == 'extract':
        name, out = sys.argv[2], sys.argv[3]
        os.makedirs(out, exist_ok=True)
        d = read_movie(name)
        open(os.path.join(out, name), 'wb').write(d)
        raw, _ = video_stream(d)
        open(os.path.join(out, name[:-4] + '.ipu'), 'wb').write(raw)
        print(name, len(d), 'video', len(raw))
    elif cmd == 'info':
        info(sys.argv[2])
