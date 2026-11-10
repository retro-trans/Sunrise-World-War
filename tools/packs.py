"""RESOURCE.AFS pack format: 16-byte header (pack id, member count, 0, 0), then a
chain of member records. Each record starts with (res id, data offset from record,
data size, record size); the next record follows at record + record size. resEntry
registers the record pointer by res id; resGetPtr returns record + data offset."""
import struct, glob, os, json

SRC = 'work/source/RESOURCE'

def members(data):
    out = []
    pos = 0x10
    while pos + 16 <= len(data):
        rid, off, size, asz = struct.unpack_from('<IIII', data, pos)
        if rid == 0xFFFFFFFF:
            break
        out.append(dict(rid=rid, rec=pos, off=pos + off, size=size, asize=asz))
        if asz == 0:
            break
        pos += asz
    return out

def pack_files():
    return sorted(glob.glob(os.path.join(SRC, '*.bin')))

def build_index():
    idx = {}
    for p in pack_files():
        d = open(p, 'rb').read()
        pid, grp = struct.unpack_from('<II', d, 0)
        fi = int(os.path.basename(p).split('_')[0])
        for m in members(d):
            magic = d[m['off']:m['off'] + 4]
            idx.setdefault(m['rid'], dict(file=fi, pack_id=pid, group=grp, off=m['off'], size=m['size'],
                                 magic=magic.hex()))
    return idx

if __name__ == '__main__':
    idx = build_index()
    json.dump(idx, open('work/source/resource_index.json', 'w'), indent=0)
    import collections
    c = collections.Counter(bytes.fromhex(v['magic']) for v in idx.values())
    print(len(idx), 'members')
    for k, n in c.most_common(40): print(k, n)


def rebuild(data, replace):
    """Rebuild a pack, replacing member data by res id ({rid: bytes}). Layout rules
    (verified byte-identical on all 4,861 original packs): record = rid, data offset,
    data size, record size + 0xFF fill; data starts at the first 64-byte boundary at
    least 0x20 past the record; the next record starts at (data end & ~15) + 16 with
    0xFF fill; the pack ends with the last record."""
    ms = members(data)
    out = bytearray(data[:0x10])
    for m in ms:
        body = replace.get(m['rid'], data[m['off']:m['off'] + m['size']])
        rec = len(out)
        off = 0x20
        while (rec + off) % 64:
            off += 0x10
        end = rec + off + len(body)
        nxt = (end & ~15) + 16
        out += struct.pack('<IIII', m['rid'], off, len(body), nxt - rec)
        out += b'\xff' * (off - 0x10)
        out += body
        out += b'\xff' * (nxt - end)
    return bytes(out)
