"""Town/map script strings (efile scripts in SLPS_252.70) and their English.

Scripts: efile_tbl (0x226d38) -> 95 script files in the ELF data area. A string argument in
the bytecode is token 0x00 + NUL-terminated text; _exp_func stores its address in the
argument block (0x266128 + 4*i) and advances by strlen+1, so the text cannot change length.
At run time tools/vwf.py SCRIPT_STR hook swaps the stored pointer for the English one
(lookup by the string's address).

  py -3.11 tools/town_strings.py dump        write work/source/town_strings.json (local, Japanese)
  py -3.11 tools/town_strings.py template    (re)create work/translation/en/town_strings.json
"""
import json, os, re, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'work/source/town_strings.json')
EN = os.path.join(ROOT, 'work/translation/en/town_strings.json')
EFILE_TBL = 0x226d38


def sjis_run(d, o):
    """Length of a plausible text string at d[o:] ending in NUL, or 0."""
    i = o
    while i < len(d) and d[i]:
        c = d[i]
        if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef:
            if i + 1 >= len(d) or not (0x40 <= d[i + 1] <= 0xfc) or d[i + 1] == 0x7f:
                return 0
            i += 2
        elif 0x20 <= c < 0x7f or 0xa1 <= c <= 0xdf:
            i += 1
        else:
            return 0
    if i == o or i >= len(d):
        return 0
    try:
        d[o:i].decode('cp932')
    except UnicodeDecodeError:
        return 0
    return i - o


def efiles(elf):
    out = []
    i = 0
    while True:
        p = elf.u32(EFILE_TBL + 4 * i)
        if not 0x260000 <= p < 0x2c0000:
            break
        out.append(p); i += 1
    return out


def dump():
    from disasm import Elf
    e = Elf()
    files = efiles(e)
    bounds = sorted(set(files))
    rows = []
    for n, p in enumerate(files):
        nxt = min([b for b in bounds if b > p] or [p + 0x4000])
        cnt = struct.unpack('<H', e.read(p, 2))[0]
        code = p + cnt * 4 + 2
        d = e.read(code, nxt - code)
        o = 0
        while o < len(d) - 1:
            if d[o] == 0 and (L := sjis_run(d, o + 1)) >= 2 and any(c >= 0x80 for c in d[o + 1:o + 1 + L]):
                va = code + o + 1
                rows.append(dict(va=hex(va), efile=n, name=e.name_at(p), jp=d[o + 1:o + 1 + L].decode('cp932'),
                                 size=L, prev=d[max(0, o - 3):o].hex(), next=d[o + 2 + L:o + 5 + L].hex()))
                o += L + 1
            else:
                o += 1
    json.dump(rows, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(files), 'efiles,', len(rows), 'strings,', len({r['jp'] for r in rows}), 'distinct ->', os.path.relpath(SRC, ROOT))


# ---------------------------------------------------------------------------
# Run-time hook. _exp_func (0x17fac0) on a string argument:
#     17fb0c lw v0, 0x158(gp) ; 17fb10 move a0, v0 ; 17fb14 jal strlen ; 17fb18 sw v0, (s0)
# The jal goes to SCRIPT_STR instead: djb2 hash of the text, binary search in TABLE
# (sorted u32 hash, u32 English pointer); on a hit the English pointer replaces the one
# the delay slot stored in the argument block (s0). Then it tail-calls strlen on the
# original text, so the script pointer still advances past the Japanese bytes.
STRLEN = 0x204A9C
HOOK_AT = 0x17FB14
SCRIPT_STR = 0x210700
TABLE = 0x210780
REGION_END = 0x21137C
LIMIT = {'house': 31, 'town': 31, 'exit': 31, 'map': 40}   # 32-byte strcpy targets; map marks keep the pointer


def djb2(b):
    h = 5381
    for c in b:
        h = (h * 33 + c) & 0xFFFFFFFF
    return h


def load():
    return json.load(open(EN, encoding='utf-8'))['rows']


def problems(rows=None):
    rows = rows or load()
    out = []
    for r in rows:
        en = r.get('en') or ''
        if not en:
            continue
        if any(ord(c) > 126 or ord(c) < 32 for c in en):
            out.append(f'{r["jp"]!r}: non-ASCII English')
        lim = min(LIMIT[k] for k in r['kinds'])
        if len(en) > lim:
            out.append(f'{en!r}: {len(en)} bytes > {lim} ({"/".join(r["kinds"])})')
    return out


def blobs():
    return [(r['jp'], r['en'].encode('ascii') + b'\0') for r in load() if r.get('en')]


def hook_fn(n):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dbg'))
    from mips import Asm, move, addiu, lbu, sll, addu, srl, sltu, lw, sw, j, la, NOP
    a = Asm(SCRIPT_STR)
    a(move('t0', 'a0'), addiu('v1', 'zero', 5381))
    a.label('hash')
    a(lbu('t1', 0, 't0'))
    a.br('beqz', 't1', 'hashed'); a(addiu('t0', 't0', 1))
    a(sll('t2', 'v1', 5), addu('v1', 'v1', 't2'))
    a.br('b', 'hash'); a(addu('v1', 'v1', 't1'))
    a.label('hashed')
    a(la('t3', TABLE), move('t4', 'zero'), addiu('t5', 'zero', n))
    a.label('search')
    a.br('beq', 't4', 't5', 'miss'); a(addu('t6', 't4', 't5'))
    a(srl('t6', 't6', 1), sll('t7', 't6', 3), addu('t7', 't7', 't3'), lw('t8', 0, 't7'))
    a.br('beq', 't8', 'v1', 'hit'); a(sltu('at', 't8', 'v1'))
    a.br('beqz', 'at', 'lower'); a(NOP)
    a.br('b', 'search'); a(addiu('t4', 't6', 1))
    a.label('lower')
    a.br('b', 'search'); a(move('t5', 't6'))
    a.label('hit')
    a(lw('t8', 4, 't7'), sw('t8', 0, 's0'))
    a.label('miss')
    a(j(STRLEN), NOP)
    return a.assemble()


# House buttons (townSelectHouseMove) are right-aligned with x = 232 - 11 * strlen(name):
# 11 px per byte of the 22px font. HOUSE_W replaces that strlen with (pixel width + 5) / 11,
# measured with the VWF widths (font type 0 forced while measuring).
HOUSE_STRLEN_AT = 0x181214
WIDTH_FN = 0x2101C0


def house_w_fn(base):
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dbg'))
    from mips import Asm, move, addiu, lbu, sll, addu, sltiu, lw, sw, sd, ld, jr, jal, or_, div, r_type, NOP
    a = Asm(base)
    a(addiu('sp', 'sp', -16), sd('ra', 0, 'sp'), lw('t9', 0x90, 'gp'), sw('zero', 0x90, 'gp'),
      move('t0', 'a0'), move('t1', 'zero'))
    a.label('loop')
    a(lbu('a0', 0, 't0'))
    a.br('beqz', 'a0', 'done'); a(addiu('t0', 't0', 1))
    a(sltiu('at', 'a0', 0x80))
    a.br('bnez', 'at', 'one'); a(NOP)
    a(sltiu('at', 'a0', 0xA0))
    a.br('bnez', 'at', 'two'); a(NOP)
    a(sltiu('at', 'a0', 0xE0))
    a.br('bnez', 'at', 'one'); a(NOP)
    a.label('two')
    a(lbu('at', 0, 't0'), sll('a0', 'a0', 8), or_('a0', 'a0', 'at'), addiu('t0', 't0', 1))
    a.label('one')
    a(jal(WIDTH_FN), NOP)
    a.br('b', 'loop'); a(addu('t1', 't1', 'v0'))
    a.label('done')
    a(sw('t9', 0x90, 'gp'), addiu('t1', 't1', 5), addiu('at', 'zero', 11), div('t1', 'at'), NOP, NOP,
      r_type(0, 0, 'v0', 0, 0x12), ld('ra', 0, 'sp'), jr('ra'), addiu('sp', 'sp', 16))
    return a.assemble()


def patches(where, log=print):
    """where: {jp: va of its English} from elfstrings_build.allocate(extra=blobs())."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dbg'))
    from mips import jal, pack
    probs = problems()
    if probs:
        raise ValueError('town strings: ' + '; '.join(probs[:5]))
    known = {}
    if os.path.exists(SRC):
        for x in json.load(open(SRC, encoding='utf-8')):
            known.setdefault(djb2(x['jp'].encode('cp932')), set()).add(x['jp'])
    table = {}
    for jp, va in where.items():
        h = djb2(jp.encode('cp932'))
        clash = (known.get(h, set()) | ({table[h][0]} if h in table else set())) - {jp}
        if clash:
            raise ValueError(f'town strings: hash clash {jp!r} / {sorted(clash)!r}')
        table[h] = (jp, va)
    keys = sorted(table)
    tb = b''.join(struct.pack('<II', h, table[h][1]) for h in keys)
    code = hook_fn(len(keys))
    house_w = (TABLE + len(tb) + 15) & ~15
    wcode = house_w_fn(house_w)
    assert SCRIPT_STR + len(code) <= TABLE and house_w + len(wcode) <= REGION_END, 'town table does not fit'
    log(f'  town/map script strings: {len(keys)} translated, hook {SCRIPT_STR:#x}, table {len(tb)} bytes')
    return [(SCRIPT_STR, None, code, 'script string lookup hook'),
            (TABLE, None, tb, 'script string table (djb2 -> English)'),
            (HOOK_AT, pack([jal(STRLEN)]), pack([jal(SCRIPT_STR)]), '_exp_func string argument -> lookup hook'),
            (house_w, None, wcode, 'house button pixel width / 11'),
            (HOUSE_STRLEN_AT, pack([jal(STRLEN)]), pack([jal(house_w)]), 'townSelectHouseMove: right-align on pixel width')]


def template():
    """Refresh work/translation/en/town_strings.json from the dump, keeping English."""
    src = json.load(open(SRC, encoding='utf-8'))
    old = {r['jp']: r for r in load()} if os.path.exists(EN) else {}
    kinds = {'46': 'house', '29': 'house', '47': 'town', '7f': 'exit'}
    rows = {}
    for x in src:
        if x['next'][:2] not in ('18', 'ff'):
            continue                      # not followed by an argument token: false match
        k = kinds.get(x['prev'][-2:], 'map')
        o = old.get(x['jp'], {})
        r = rows.setdefault(x['jp'], dict(jp=x['jp'], en=o.get('en', ''), kinds=[], uses=0,
                                          notes=o.get('notes', ''), status=o.get('status', 'draft')))
        if k not in r['kinds']:
            r['kinds'].append(k)
        r['uses'] += 1
    json.dump(dict(rows=list(rows.values())), open(EN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(rows), 'rows,', sum(1 for r in rows.values() if r['en']), 'with English')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'dump':
        dump()
    elif cmd == 'template':
        template()
    elif cmd == 'check':
        ps = problems()
        print('; '.join(ps) or 'ok', f'({len(load())} rows)')
