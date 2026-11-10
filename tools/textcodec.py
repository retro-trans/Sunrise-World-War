"""Lossless ATMB editor codec. Ported from the sibling Sunrise Eiyuutan 2 project and
re-checked against SLPS-25270 GetMessagePage (0x113668): line-start headers
％/＄ + u16, ＆ｖ + u32 + u16, ＆ｆ + u16 id + u16 argc + argc*u32; inline
＠ｃ/＠ｂ/＠ｖ + u16 and the ＃ one-character escape. A line-start newline ends a page.

{C:HEX} preserves complete control records, {xHH} preserves nontext bytes.
Raw controls are never decoded as Japanese or allowed to terminate a message.
"""
import re
import struct

TOKEN = re.compile(r'\{C:([0-9A-Fa-f]+)\}|\{x([0-9A-Fa-f]{2})\}')


def control_size(data, i, line_start=True):
    head = data[i:i+2]
    # Raw renderer font selectors survive native message decoding and are
    # consumed later by mesPutSOneCode. Protect them like binary records.
    if len(head)==2 and head[0]==0x23 and 0x30<=head[1]<=0x35:
        return 2
    # GetMessagePage 0x12EA38 skips these header branches once s4 records
    # body text. In prose, full-width percent/dollar/ampersand are glyphs.
    if line_start and head in (b'\x81\x90', b'\x81\x93'):
        return 4
    if line_start and head == b'\x81\x95':
        sub = data[i+2:i+4]
        if sub == b'\x82\x96':
            return 10
        if sub == b'\x82\x86' and i+8 <= len(data):
            return 8+4*struct.unpack_from('<H',data,i+6)[0]
    if head == b'\x81\x97':
        return 6
    if head == b'\x81\x8f' and i+2 < len(data):
        return 4 if data[i+2] >= 0x80 else 3
    return 0


def decode(data):
    out = []
    i = 0
    line_start = True
    while i < len(data):
        n = control_size(data,i,line_start)
        if n:
            if i+n > len(data):
                raise ValueError('Truncated control at %X' % i)
            out.append('{C:'+data[i:i+n].hex().upper()+'}')
            head = data[i:i+2]
            # Header/voice/function records, encoded font/format/timing
            # directives do not advance native s4. Runtime values, character
            # insertion, escapes and raw renderer #digit bytes do.
            if (head[:1] == b'#' or head == b'\x81\x8f' or
                    head == b'\x81\x97' and data[i+2:i+4] in (b'\x82\x62', b'\x82\x96')):
                line_start = False
            i += n
            continue
        c = data[i]
        n = 2 if 0x81 <= c <= 0x9f or 0xe0 <= c <= 0xfc else 1
        raw = data[i:i+n]
        try:
            ch = raw.decode('cp932')
            if len(raw)!=n or ch.encode('cp932')!=raw or c<0x20 and c not in (10,13,9) or ch in '{}':
                raise ValueError()
            out.append(ch)
        except (UnicodeError,ValueError):
            out.extend('{x%02X}' % b for b in raw)
        line_start = c == 10
        i += n
    return ''.join(out)


def encode(text):
    out = bytearray()
    pos = 0
    for m in TOKEN.finditer(text):
        literal = text[pos:m.start()]
        if '{' in literal or '}' in literal:
            raise ValueError('Unrecognised editor tag')
        out.extend(literal.encode('cp932'))
        out.extend(bytes.fromhex(m.group(1) or m.group(2)))
        pos = m.end()
    literal = text[pos:]
    if '{' in literal or '}' in literal:
        raise ValueError('Unrecognised editor tag')
    out.extend(literal.encode('cp932'))
    return bytes(out)


def controls(text):
    return [m.group() for m in TOKEN.finditer(text)]


def parse_table(data):
    if data[:4] != b'ATMB' or len(data)<12:
        raise ValueError('Not ATMB')
    n=struct.unpack_from('<I',data,4)[0]
    if not 0 < n < 100000 or 8+4*n>len(data):
        raise ValueError('Bad ATMB count')
    offsets=list(struct.unpack_from('<%dI'%n,data,8))
    if offsets[0]!=8+4*n or any(a>=b for a,b in zip(offsets,offsets[1:])) or offsets[-1]>=len(data):
        raise ValueError('Bad ATMB offsets')
    return [data[a:b] for a,b in zip(offsets,offsets[1:]+[len(data)])]


def build_table(rows):
    pos=8+4*len(rows)
    offsets=[]
    for row in rows:
        offsets.append(pos)
        pos+=len(row)
    return b'ATMB'+struct.pack('<I',len(rows))+struct.pack('<%dI'%len(rows),*offsets)+b''.join(rows)
