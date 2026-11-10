"""Build a test ISO: work/output/v<VERSION>/Sunrise World War EN v<VERSION>.iso

  py -3.11 tools/build.py 0.1.0            dry run (report what would change)
  py -3.11 tools/build.py 0.1.0 --write    write ISO + manifest (refuses existing folder)

Options: --no-vwf, --no-monitor (input/frame monitor for tools/dbg), --source-text
(ignore translations; VWF/monitor only), --dev (patch work/output/dev/SWW_dev.iso in
place: ELF + every slack pack; the ISO is fully written the first time).

Layout: every pack holding text (ATMB) and the font pack get a fixed TOC slot of
2x size + 64 KiB, so all builds share one AFS layout and a dev build rewrites only
those packs. The game reads the size cached in the ELF, not the TOC size.

Steps: ELF patches (tools/vwf.py, guarded by expected bytes) -> translated ATMB rows
(work/translation/en/<table>.json, field "en") re-encoded with tools/textcodec.py ->
pack rebuild (tools/packs.rebuild) -> pfr size table in the ELF (0x2163F4 + 12*id)
-> RESOURCE.AFS + ISO (tools/isobuild.py).
"""
import argparse, glob, hashlib, json, os, struct, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import vwf, translations
from packs import pack_files, members, rebuild
from textcodec import encode, parse_table, build_table, decode
import isobuild, elfstrings_build, town_strings, gfx_text, ank_font, deck_names, movie_subtitles

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELF_SRC = os.path.join(ROOT, 'work/source/SLPS_252.70')
PFR_TABLE = 0x2163F4        # pfrGetDataInfoAdd: base + 12 * pack id; +8 = size
VA_TO_FILE = 0xFF000        # both PT_LOADs: file offset = va - 0xFF000


def slack_packs(files):
    """Pack indices that get AFS slack: every pack with an ATMB member + the font pack
    (from work/source/text_inventory.json, written by tools/extract_text.py)."""
    inv = json.load(open(os.path.join(ROOT, 'work/source/text_inventory.json')))
    return {vwf.FONT_PACK_FILE} | {t['file'] for t in inv}


def patch_elf(elf, va, old, new, why, log):
    o = va - VA_TO_FILE
    cur = bytes(elf[o:o + len(new)])
    if old is not None and cur != old:
        raise ValueError(f'unexpected bytes at {va:08x} for {why}: {cur.hex()}')
    elf[o:o + len(new)] = new
    log(f'  ELF {va:08x} +{len(new):5d}  {why}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('version')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--no-vwf', action='store_true')
    ap.add_argument('--no-monitor', action='store_true')
    ap.add_argument('--source-text', action='store_true')
    ap.add_argument('--dev', action='store_true')
    ap.add_argument('--preview', action='store_true', help='library preview hook (title Gallery)')
    a = ap.parse_args()
    ver = a.version.lstrip('v')
    outdir = os.path.join(ROOT, 'work/output', 'v' + ver)
    if a.write and os.path.exists(outdir):
        raise SystemExit(f'{outdir} exists; use a fresh version')
    log_lines = []
    def log(s=''):
        print(s); log_lines.append(s)

    elf = bytearray(open(ELF_SRC, 'rb').read())
    log(f'Build v{ver}  ({"WRITE" if a.write else "DRY RUN"})')
    for va, old, new, why in vwf.patches(elf, monitor=not a.no_monitor, vwf=not a.no_vwf,
                                          tag=('v' + ver).encode()):
        patch_elf(elf, va, old, new, why, log)
    if not a.no_vwf:
        for va, old, new, why in ank_font.patches(bytes(elf)):
            patch_elf(elf, va, old, new, why, log)
    if a.preview:
        for va, old, new, why in vwf.preview_patches():
            patch_elf(elf, va, old, new, why, log)

    files = pack_files()
    replace = {}     # file index -> {rid: bytes}
    if not a.no_vwf:
        d = open(files[vwf.FONT_PACK_FILE], 'rb').read()
        mm = {m['rid']: d[m['off']:m['off'] + m['size']] for m in members(d)}
        g22, g26 = vwf.font_members(mm[vwf.FONT22_RID], mm[vwf.FONT26_RID])
        replace.setdefault(vwf.FONT_PACK_FILE, {}).update({vwf.FONT22_RID: g22, vwf.FONT26_RID: g26})
        log('  font: proportional ASCII glyphs for 22px/26px sets (pack 0002)')

    stats = dict(tables=0, rows=0)
    if not a.source_text:
        for name, rows, raw in translations.load_tables(log):
            fi, rid = int(name[:4]), int(name[5:])
            replace.setdefault(fi, {})[rid] = build_table(raw)
            stats['tables'] += 1; stats['rows'] += rows
        sprites = gfx_text.build_members(log)
        occ = gfx_text.occurrences(list(sprites))
        for rid, data in sprites.items():
            for fi in occ[rid]:
                replace.setdefault(fi, {})[rid] = data
        ps, where = elfstrings_build.allocate(bytes(elf), elfstrings_build.load_rows(), log,
                                              extra=town_strings.blobs(), reserved=movie_subtitles.RESERVED)
        ps += deck_names.patches(bytes(elf))
        for va, old, new, why in ps + town_strings.patches(where, log):
            patch_elf(elf, va, old, new, why, lambda s: None)
        with open(ELF_SRC, 'rb') as source:
            for va, old, new, why in movie_subtitles.patches(source.read()):
                patch_elf(elf, va, old, new, why, log)

    sizes = [os.path.getsize(p) for p in files]
    slack = slack_packs(files)
    slots = [(2 * sz + 0x10000 + 2047) // 2048 * 2048 if i in slack else sz for i, sz in enumerate(sizes)]
    changed = {}
    for fi, rep in sorted(replace.items()):
        d = open(files[fi], 'rb').read()
        nd = rebuild(d, rep)
        pid = struct.unpack_from('<I', d, 0)[0]
        so = PFR_TABLE + 12 * pid + 8 - VA_TO_FILE
        assert struct.unpack_from('<I', elf, so)[0] == len(d)
        struct.pack_into('<I', elf, so, len(nd))
        sizes[fi] = len(nd)
        if len(nd) > slots[fi]:
            raise ValueError(f'pack {fi} ({len(nd)}) exceeds its AFS slot ({slots[fi]})')
        changed[fi] = nd
        log(f'  pack {fi:04d} id {pid:4d}: {len(d)} -> {len(nd)} bytes ({len(nd) - len(d):+d}), members {sorted(hex(r) for r in rep)}')
    log(f"  translated tables {stats['tables']}, rows {stats['rows']}")

    manifest = dict(version=ver, time=time.strftime('%Y-%m-%dT%H:%M:%S'), vwf=not a.no_vwf,
                    monitor=not a.no_monitor, preview=a.preview, source_text=a.source_text, stats=stats,
                    opening_subtitles=not a.source_text,
                    opening_romaji=not a.source_text and movie_subtitles.ROMAJI_FILE.is_file(),
                    elf_sha256=hashlib.sha256(elf).hexdigest(),
                    packs={f'{fi:04d}': dict(size=len(b), sha256=hashlib.sha256(b).hexdigest()) for fi, b in changed.items()})
    if not a.write:
        log('DRY RUN: --write builds the ISO'); return
    dev_iso = os.path.join(ROOT, 'work/output/dev/SWW_dev.iso')
    if a.dev and os.path.exists(dev_iso):
        open(dev_iso, 'r+b').close()      # fails early if the emulator still has it open
    os.makedirs(outdir)
    def blob(i):
        return changed[i] if i in changed else open(files[i], 'rb').read()
    t = time.time()
    if a.dev:
        iso_path = os.path.join(ROOT, 'work/output/dev/SWW_dev.iso')
        manifest['iso'] = 'work/output/dev/SWW_dev.iso (dev, patched in place)'
    else:
        iso_path = os.path.join(outdir, f'Sunrise World War EN v{ver}.iso')
    if a.dev and os.path.exists(iso_path):
        # slack packs, plus changed packs that still fit their original slot (graphics)
        extra = sorted(i for i in changed if i not in slack and len(changed[i]) <= slots[i])
        isobuild.patch_iso(iso_path, bytes(elf), slots, {i: blob(i) for i in sorted(slack) + extra}, log=lambda s: None)
        log(f'  dev ISO patched in place: ELF + {len(slack)} slack packs + {len(extra)} other changed packs')
    else:
        os.makedirs(os.path.dirname(iso_path), exist_ok=True)
        manifest['volume_blocks'] = isobuild.write_iso(iso_path, bytes(elf), slots, blob,
                                                       orig=os.path.join(ROOT, isobuild.ORIG), log=log)
    log(f'  wrote {iso_path} in {time.time() - t:.0f}s')
    open(os.path.join(outdir, 'SLPS_252.70'), 'wb').write(elf)
    if not a.source_text:
        srt_name = 'Destination.en-romaji.srt' if manifest['opening_romaji'] else 'Destination.en.srt'
        with open(os.path.join(outdir, srt_name), 'w', encoding='utf-8') as subtitles:
            subtitles.write(movie_subtitles.srt())
    json.dump(manifest, open(os.path.join(outdir, 'manifest.json'), 'w'), indent=1)
    open(os.path.join(outdir, 'build.log'), 'w', encoding='utf-8').write('\n'.join(log_lines) + '\n')


if __name__ == '__main__':
    main()
