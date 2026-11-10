"""ELF string translations: work/translation/en/elf_strings.json

{"rows": [{"va": "0x2d1288", "jp": "...", "en": "...", "group": "...", "status": "..."}]}

  py -3.11 tools/elfstrings_build.py template [--write]   (re)create the rows file, keeping
        existing en; name-table strings get en from the glossary
  py -3.11 tools/elfstrings_build.py check               dry-run allocation report

Allocation (build time):
  * fits its own slot (string + NUL + zero padding up to the next string) -> in place;
  * otherwise, if every reference is a data pointer word -> moved to free space and the
    pointers rewritten. Free space = unused tails of slots whose string got shorter or
    moved, plus unreferenced library functions (tools/deadcode.py list below);
  * strings referenced from code (lui + addiu/ori) move only to free space with the same
    upper half, and each low-half instruction is rewritten; otherwise reported.
"""
import collections, json, os, re, struct, sys
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, 'work/translation/en/elf_strings.json')
VA_TO_FILE = 0xFF000
DATA_RANGES = [(0x216180, 0x2B8094), (0x2B8100, 0x2E8CB8), (0x2EA800, 0x2F0BA4)]
# unreferenced code (tools/deadcode.py), outside the VWF/debug patch region
DEAD = [(0x1E9C58, 0x1EA65C), (0x175DF0, 0x1769D4), (0x1DEC98, 0x1DF360), (0x15C458, 0x15CAF0),
        (0x1333E0, 0x133920), (0x1EA688, 0x1EAB78), (0x1A01C8, 0x1A066C), (0x1E7010, 0x1E74B0)]
JP = re.compile('[぀-ヿ一-鿿！-～]')


def u32(elf, va):
    return struct.unpack_from('<I', elf, va - VA_TO_FILE)[0]


def references(elf, targets):
    """{target: {'data': [word VAs], 'code': [(lo VA, op)]}}"""
    t = set(targets); out = collections.defaultdict(lambda: {'data': [], 'code': []})
    for lo, hi in DATA_RANGES:
        for a in range(lo, hi - 3, 4):
            w = u32(elf, a)
            if w in t:
                out[w]['data'].append(a)
    o0 = 0x100000 - VA_TO_FILE; hi = {}
    for k in range(0, 0x114FB4, 4):
        w = struct.unpack_from('<I', elf, o0 + k)[0]
        op = w >> 26; rt = (w >> 16) & 31; rs = (w >> 21) & 31; imm = w & 0xFFFF
        if op == 0x0F:
            hi[rt] = imm << 16
        elif op in (0x09, 0x19, 0x0D) and rs in hi:
            v = (hi[rs] | imm) if op == 0x0D else (hi[rs] + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xFFFFFFFF
            if v in t:
                out[v]['code'].append((0x100000 + k, op))
    return out


# .data / .sdata are writable: zero bytes after a string there may be live variables, so a
# string in them gets only its own bytes (or its buffer size) and its tail is never reused.
WRITABLE = [(0x216180, 0x2B80AC), (0x2E8D00, 0x2F0BA4)]
BUFFERS = {0x266158: 32}        # townName: char[32], initial text "Unnamed Town" (strcpy target)


SDATA = (0x2E8D00, 0x2F0BA4)  # .lit4 + .sdata
GP = 0x2F0CF0
_SDATA_REFS = {}
_GP_REFS = {}


def writable(va):
    return any(a <= va < b for a, b in WRITABLE)


def sdata_refs(elf):
    """Every .lit4/.sdata address the program names: gp-relative operands, lui+lo pairs
    and pointer words in the data sections."""
    key = len(elf)
    if key in _SDATA_REFS:
        return _SDATA_REFS[key]
    used = set(); gp_used = set()
    o0 = 0x100000 - VA_TO_FILE; hi = {}
    for k in range(0, 0x114FB4, 4):
        w = struct.unpack_from('<I', elf, o0 + k)[0]
        op = w >> 26; rt = (w >> 16) & 31; rs = (w >> 21) & 31; imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        if op == 0x0F:
            hi[rt] = imm << 16
        elif rs == 28 and op in (0x09, 0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x28, 0x29, 0x2B,
                                 0x31, 0x35, 0x37, 0x39, 0x3D, 0x3F, 0x1E, 0x1F):
            used.add((GP + simm) & 0xFFFFFFFF); gp_used.add((GP + simm) & 0xFFFFFFFF)
        elif rs in hi and op in (0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B, 0x31, 0x39):
            used.add((hi[rs] | imm) if op == 0x0D else (hi[rs] + simm) & 0xFFFFFFFF)
    for lo, hi_ in DATA_RANGES:
        for a in range(lo, hi_ - 3, 4):
            used.add(u32(elf, a))
    _SDATA_REFS[key] = used = {u for u in used if SDATA[0] <= u < SDATA[1]}
    _GP_REFS[key] = gp_used
    return used


def gp_refs(elf):
    """addresses named gp-relatively (these references cannot be rewritten by a move)"""
    sdata_refs(elf)
    return _GP_REFS[len(elf)]


def slot_size(elf, va):
    """bytes available at va: string, NUL and following zero padding (to the next
    non-zero byte), capped at the 4-byte boundary before it. Writable sections: the
    string and its NUL only (or the known buffer size)."""
    o = va - VA_TO_FILE
    e = elf.index(b'\0', o)
    n = e + 1
    if writable(va):
        if va in BUFFERS:
            return BUFFERS[va]
        if not SDATA[0] <= va < SDATA[1]:
            return n - o
        # .sdata: small objects, all reached gp-relative; zeros up to the next referenced
        # address (or non-zero byte) are alignment padding between string literals
        used = sdata_refs(elf)
        while n < len(elf) and elf[n] == 0 and n - o < 64 and (n + VA_TO_FILE) not in used:
            n += 1
        return n - o
    while n < len(elf) and elf[n] == 0 and n - o < 4096:
        n += 1
    return n - o


def load_rows():
    if not os.path.exists(PATH):
        return []
    return json.load(open(PATH, encoding='utf-8'))['rows']


def allocate(elf, rows, log=print, extra=None, reserved=()):
    """extra: [(key, bytes)] data blobs (no references) placed in the free space left after
    the strings; returns (patches, {key: va}) when given. Reserved spans start at DEAD
    region boundaries and reduce the space available to strings and data blobs."""
    todo = [r for r in rows if r.get('en')]
    if not todo and extra is None:
        return []
    vas = [int(r['va'], 16) for r in todo]
    refs = references(elf, vas)
    patches = []; free = []          # free = [start, end) spans
    placed = {}; overflow = []
    for r, va in zip(todo, vas):
        b = r['en'].encode('cp932') + b'\0'
        slot = slot_size(elf, va)
        if len(b) <= slot:
            placed[va] = va
            patches.append((va, None, b + bytes(slot - len(b)), 'string ' + r['va']))
            if slot - len(b) >= 4 and not writable(va):
                free.append([va + len(b), va + slot])
        else:
            overflow.append((r, va, b, slot))
    reserved_ends = dict(reserved)
    for a, b_ in DEAD:
        free.append([reserved_ends.get(a, a), b_])
    gpr = gp_refs(elf)
    for r, va, b, slot in overflow:
        rf = refs.get(va, {'data': [], 'code': []})
        if va in gpr:
            log(f'  !! ELF string {r["va"]} ({len(b)} > slot {slot}) is reached gp-relative; must fit in place')
            continue
        need_hi = None
        if rf['code']:
            need_hi = (va + 0x8000) >> 16
        spot = None
        for f in sorted(free, key=lambda s: s[1] - s[0]):
            if f[1] - f[0] < len(b):
                continue
            if need_hi is not None and (((f[0] + 0x8000) >> 16) != need_hi or ((f[0] + len(b) + 0x8000) >> 16) != need_hi
                                        or any(op == 0x0D and (f[0] >> 16) != (va >> 16) for _, op in rf['code'])):
                continue
            spot = f; break
        if spot is None:
            log(f'  !! ELF string {r["va"]} ({len(b)} > slot {slot}) has no space'
                f'{" with the same upper half (code-referenced)" if need_hi is not None else ""}')
            continue
        new = spot[0]; spot[0] += (len(b) + 3) & ~3
        patches.append((new, None, b, f'moved string {r["va"]} -> {new:#x}'))
        patches.append((va, None, bytes(slot), f'cleared old slot {r["va"]}'))
        free.append([va, va + slot]) if not rf['code'] and not writable(va) else None
        for site in rf['data']:
            patches.append((site, None, struct.pack('<I', new), f'pointer {site:#x} -> {new:#x}'))
        for site, op in rf['code']:
            w = u32(elf, site)
            patches.append((site, None, struct.pack('<I', (w & 0xFFFF0000) | (new & 0xFFFF)), f'lo {site:#x} -> {new:#x}'))
        placed[va] = new
    log(f'  ELF strings: {len(todo)} translated, {len(todo) - len(overflow)} in place, '
        f'{sum(1 for r, va, b, s in overflow if va in placed)} moved, '
        f'{sum(1 for r, va, b, s in overflow if va not in placed)} without space')
    # cleared old slots must not overwrite strings moved into them
    order = [p for p in patches if p[3].startswith('cleared')] + [p for p in patches if not p[3].startswith('cleared')]
    if extra is None:
        return order
    where = {}
    for key, b in sorted(extra, key=lambda kb: -len(kb[1])):
        spot = next((f for f in sorted(free, key=lambda s: s[1] - s[0]) if f[1] - f[0] >= len(b)), None)
        if spot is None:
            raise ValueError(f'no free ELF space for {key!r} ({len(b)} bytes)')
        where[key] = spot[0]; spot[0] += (len(b) + 3) & ~3
        order.append((where[key], None, b, f'data {key}'))
    log(f'  extra data: {len(extra)} blobs, {sum(len(b) for _, b in extra)} bytes; '
        f'free left {sum(max(0, f[1] - f[0]) for f in free)} bytes')
    return order, where


def patches(elf, log=print):
    return allocate(bytes(elf), load_rows(), log)


def template(write):
    sys.path.insert(0, ROOT + '/tools')
    from disasm import Elf
    e = Elf()
    ss = json.load(open(os.path.join(ROOT, 'work/source/elf_strings.json'), encoding='utf-8'))
    nt = json.load(open(os.path.join(ROOT, 'work/source/name_tables.json'), encoding='utf-8'))
    names = {}
    for tn, rows in nt.items():
        for r in rows:
            for f, v in r.items():
                if f.startswith('+'):
                    names[int(v['va'], 16)] = f'names:{tn}{f}'
    gl = {}
    gp = os.path.join(ROOT, 'work/glossary/glossary.json')
    if os.path.exists(gp):
        for g in json.load(open(gp, encoding='utf-8'))['entries']:
            if g.get('en'):
                gl[g['jp']] = g['en']
    old = {r['va']: r for r in load_rows()}
    out = []
    for s in ss:
        if not s['refs'] or not JP.search(s['jp']):
            continue
        va = s['va']
        grp = names.get(va) or re.sub(r'\+0x[0-9a-f]+$', '', e.name_at(int(s['ref_sites'][0], 16)) or '?')
        r = dict(va=hex(va), jp=s['jp'], en='', group=grp, status='')
        if hex(va) in old and old[hex(va)].get('en'):
            r.update(en=old[hex(va)]['en'], status=old[hex(va)].get('status', ''))
        elif grp.startswith('names:') and s['jp'].strip() in gl:
            r.update(en=gl[s['jp'].strip()], status='glossary')
        out.append(r)
    print(len(out), 'rows;', sum(1 for r in out if r['en']), 'with en')
    if write:
        json.dump(dict(rows=out), open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    if sys.argv[1] == 'template':
        template('--write' in sys.argv)
    elif sys.argv[1] == 'check':
        elf = open(os.path.join(ROOT, 'work/source/SLPS_252.70'), 'rb').read()
        ps = allocate(elf, load_rows())
        print(len(ps), 'patch items')
