"""Extract build inputs from a local disc and restore editable translation files."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from afs import AFS
from iso9660 import ISO, SECTOR
from packs import build_index


SOURCE = Path('work/source')
TRANSLATION = Path('work/translation')
ORIGINAL_ELF_SHA256 = '027f6e3d202995e94ab253c04479b27648313c2deacc8e9dfe70e4cc0384af9c'
VA_TO_FILE = 0xFF000


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_missing(path, data):
    if path.exists():
        return
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_bytes(data)
    temp.replace(path)


def restore_drafts(elf):
    for copy in sorted(TRANSLATION.rglob('*.en.json')):
        draft = copy.with_name(copy.name.removesuffix('.en.json') + '.json')
        if draft.exists():
            continue
        data = read_json(copy)
        if 'table' in data:
            originals = read_json(SOURCE / 'text' / (data['table'] + '.json'))['rows']
            for row in data['rows']:
                row['jp'] = originals[row['id']]['jp']
        for row in data['rows']:
            if 'source_va' in row:
                offset = int(row['source_va'], 16) - VA_TO_FILE
                end = offset + row['source_size'] if 'source_size' in row else elf.index(b'\0', offset)
                row['jp'] = elf[offset:end].split(b'\0', 1)[0].decode('cp932')
        write_missing(draft, json.dumps(data, ensure_ascii=False, indent=1).encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', type=Path, nargs='?', default=Path('Sunrise World War (Japan).iso'))
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    if not Path('tools/prepare_source.py').is_file():
        parser.error('run this command from the repository root')

    disc = ISO(args.iso)
    with disc.f:
        files = dict(disc.walk())
        elf = disc.read_file(files['/SLPS_252.70'])
        if hashlib.sha256(elf).hexdigest() != ORIGINAL_ELF_SHA256:
            parser.error('expected the original Japanese SLPS-25270 executable')
        archive = AFS(disc.f, files['/RESOURCE.AFS']['lba'] * SECTOR)
        if len(archive.entries) != 4861:
            parser.error('unexpected RESOURCE.AFS entry count')
        print(f'{args.iso}: verified original ELF and {len(archive.entries)} resource packs')
        if not args.write:
            print('Use --write to extract files and restore missing drafts.')
            return

        pack_dir = SOURCE / 'RESOURCE'
        pack_dir.mkdir(parents=True, exist_ok=True)
        elf_path = SOURCE / 'SLPS_252.70'
        if elf_path.exists() and elf_path.read_bytes() != elf:
            parser.error(f'{elf_path} differs from the original disc')
        write_missing(elf_path, elf)
        for index, (_, size) in enumerate(archive.entries):
            pack = pack_dir / f'{index:04d}_{index:04d}.bin'
            if pack.exists():
                if pack.stat().st_size != size:
                    parser.error(f'{pack} has an unexpected size')
                continue
            data = archive.read(index)
            if len(data) != size:
                parser.error(f'ISO ended inside resource pack {index}')
            write_missing(pack, data)

    index_path = SOURCE / 'resource_index.json'
    if not index_path.exists():
        write_missing(index_path, json.dumps(build_index()).encode('utf-8'))
    if not (SOURCE / 'text_inventory.json').exists():
        subprocess.run([sys.executable, 'tools/extract_text.py', '--write'], check=True)
    restore_drafts(elf)
    print('Ready for tools/fitcheck.py and tools/build.py.')


if __name__ == '__main__':
    main()
