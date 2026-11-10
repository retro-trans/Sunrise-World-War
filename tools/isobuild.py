"""Rebuild RESOURCE.AFS and write a new ISO.

RESOURCE.AFS is written contiguously in index order (2048-aligned, TOC area 0x9800 as
shipped), because CRI ADXF partitions are opened by name and read via the AFS TOC.
Files after it on disc (MUSIC.AFS, VOICE.AFS) are shifted to follow it when it grows.
Their ISO9660 directory records (LE/BE extent + size) and the PVD volume size are
updated. The ELF is replaced in place (same size required). The UDF bridge is not
updated: the PS2 cdrom0: driver and PCSX2 use ISO9660.
"""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
from iso9660 import ISO, SECTOR

ORIG = 'Sunrise World War (Japan).iso'
TOC_AREA = 0x9800


def afs_layout(slots):
    """slots[i] = TOC size of member i (>= its data; the game reads only the size
    cached in the ELF pfr table, so a larger TOC size is reserved slack). Returns
    the member offsets within the AFS and the AFS size."""
    offs = []; pos = TOC_AREA
    for s in slots:
        offs.append(pos)
        pos = (pos + s + SECTOR - 1) // SECTOR * SECTOR
    return offs, pos


def write_afs(o, slots, blob):
    """Stream an AFS to file object o. blob(i) -> bytes (len <= slots[i])."""
    start = o.tell()
    offs, end = afs_layout(slots)
    hdr = bytearray(b'AFS\x00' + struct.pack('<I', len(slots)))
    for off, s in zip(offs, slots):
        hdr += struct.pack('<II', off, s)
    hdr += bytes(TOC_AREA - len(hdr))
    o.write(hdr)
    for i, s in enumerate(slots):
        b = blob(i)
        assert len(b) <= s, (i, len(b), s)
        o.write(b); o.write(bytes(s - len(b) + (-s) % SECTOR))
    assert o.tell() - start == end
    return end


def _set_extent(f, recoff, lba, size):
    f.seek(recoff + 2)
    f.write(struct.pack('<I', lba) + struct.pack('>I', lba) + struct.pack('<I', size) + struct.pack('>I', size))


def write_iso(out_path, elf_bytes, afs_slots, afs_blob, orig=ORIG, log=print):
    iso = ISO(orig)
    files = {p: r for p, r in iso.walk() if not r['isdir']}
    res = files['/RESOURCE.AFS']
    elf = files['/SLPS_252.70']
    assert len(elf_bytes) == elf['size'], 'ELF size must not change'
    later = sorted([r for r in files.values() if r['lba'] > res['lba']], key=lambda r: r['lba'])
    first_end = res['lba'] * SECTOR
    for r in files.values():
        if r['lba'] < res['lba']:
            assert r['lba'] * SECTOR + r['size'] <= first_end
    src = iso.f
    with open(out_path, 'wb') as o:
        src.seek(0)
        left = first_end
        while left:
            chunk = src.read(min(left, 64 << 20)); o.write(chunk); left -= len(chunk)
        afs_size = write_afs(o, afs_slots, afs_blob)
        o.write(bytes((-o.tell()) % SECTOR))
        moves = [(res, res['lba'], afs_size)]
        for r in later:
            lba = o.tell() // SECTOR
            src.seek(r['lba'] * SECTOR)
            left = r['size']
            while left:
                chunk = src.read(min(left, 64 << 20)); o.write(chunk); left -= len(chunk)
            o.write(bytes((-o.tell()) % SECTOR))
            moves.append((r, lba, r['size']))
        tail_lba = iso.volume_blocks
        orig_end = max(r['lba'] * SECTOR + r['size'] for r in files.values())
        orig_end = (orig_end + SECTOR - 1) // SECTOR
        pad = tail_lba - orig_end           # keep the original trailing padding
        o.write(bytes(pad * SECTOR))
        vol = o.tell() // SECTOR
    with open(out_path, 'r+b') as o:
        o.seek(elf['lba'] * SECTOR); o.write(elf_bytes)
        for r, lba, size in moves:
            _set_extent(o, r['recoff'], lba, size)
            log(f"  {r['name']:14s} LBA {r['lba']:8d} -> {lba:8d}  size {r['size']:11d} -> {size:11d}")
        o.seek(16 * SECTOR + 80); o.write(struct.pack('<I', vol) + struct.pack('>I', vol))
    log(f'  volume blocks {iso.volume_blocks} -> {vol}')
    return vol


def patch_iso(iso_path, elf_bytes, afs_slots, blobs, log=print):
    """Dev mode: rewrite the ELF and the given AFS members ({index: bytes}) in place in
    an ISO previously written with the same afs_slots layout."""
    iso = ISO(iso_path)
    files = {p: r for p, r in iso.walk() if not r['isdir']}
    res, elf = files['/RESOURCE.AFS'], files['/SLPS_252.70']
    assert len(elf_bytes) == elf['size']
    iso.f.seek(res['lba'] * SECTOR + 8)
    toc = struct.unpack('<%dI' % (2 * len(afs_slots)), iso.f.read(8 * len(afs_slots)))
    offs, _ = afs_layout(afs_slots)
    assert list(toc[0::2]) == offs and list(toc[1::2]) == list(afs_slots), 'dev ISO layout differs; do a full build'
    iso.f.close()
    with open(iso_path, 'r+b') as o:
        o.seek(elf['lba'] * SECTOR); o.write(elf_bytes)
        for i, b in sorted(blobs.items()):
            assert len(b) <= afs_slots[i], (i, len(b), afs_slots[i])
            o.seek(res['lba'] * SECTOR + offs[i]); o.write(b)
            log(f'  dev: member {i:04d} rewritten ({len(b)} / slot {afs_slots[i]})')
