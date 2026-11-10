"""Dump the ELF name tables (pointer fields) to work/source/name_tables.json.

table: (base VA, stride, {field offset: label}) from the accessor routines:
  chara  charaGetInfoPtr 0x226EB8 * 12   +0 full, +4 display, +8 short
  mch    mchGetPtr       0x22C538 * 76   +0 full name
  ship   shipGetPtr      0x239FC0 * 64   +0 full name
  dev    devGetPtr       0x237E20 * 56   +0 name, +0x28 info
  skill  skillGetPtr     0x24C338 * 16   +0 name?, +0xC info
  eve    eveGetPtr       0x23E2C0 * 20   +0.., +0x10 info
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from disasm import Elf

TABLES = dict(
    chara=(0x226EB8, 12, (0, 4, 8)),
    mch=(0x22C538, 76, (0, 4, 8, 12)),
    ship=(0x239FC0, 64, (0, 4, 8)),
    dev=(0x237E20, 56, (0, 4, 0x28)),
    skill=(0x24C338, 16, (0, 4, 8, 0xC)),
    eve=(0x23E2C0, 20, (0, 4, 8, 0xC, 0x10)),
)


def is_str(e, p):
    if not (0x2B8100 <= p < 0x2F0C00):
        return False
    s = e.cstr(p)
    return s is not None and len(s) > 0 and '�' not in s


def dump(e, name):
    base, stride, fields = TABLES[name]
    rows = []
    i = 0
    while True:
        rec = {}
        for f in fields:
            p = e.u32(base + i * stride + f)
            if is_str(e, p):
                rec[f'+{f:X}'] = dict(va=hex(p), jp=e.cstr(p))
        if not rec:
            if i > 0 and all(not is_str(e, e.u32(base + (i + k) * stride)) for k in range(4)):
                break
        rows.append(dict(index=i, **rec))
        i += 1
        if i > 3000:
            break
    return rows


if __name__ == '__main__':
    e = Elf()
    out = {n: dump(e, n) for n in TABLES}
    json.dump(out, open('work/source/name_tables.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for n, rows in out.items():
        print(n, len(rows), [ (r.get('+0') or {}).get('jp') for r in rows[:6]])
