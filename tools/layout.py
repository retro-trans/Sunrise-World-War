"""Pixel measurement and wrapping with the game's metrics (VWF advances from tools/vwf.py).

Measured in-game (v0.1.3 library preview, window struct read from RAM):
  library window (deckmItemIntroView): font type 0 (22px), right limit 309 px,
  font space 0. windPutText wraps mid-word when x + advance > right limit, and the
  entry is split into at most 64 lines of at most 63 bytes (64-byte heap buffers).

Widths: double-byte glyph = 22 / 26; single byte 0x20-0x7F = VWF table; other single
bytes (half-width kana) = 12 / 14; '%' + digit (colour) and '%R' are zero width.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(__file__))

_W = None


def widths():
    global _W
    if _W is None:
        import vwf
        t = vwf.widths()
        _W = {22: t[:96], 26: t[96:]}
    return _W


def text_width(s, font=22, space=0):
    w = widths()[font]
    x = 0; i = 0
    while i < len(s):
        c = s[i]
        if c == '%' and i + 1 < len(s) and (s[i + 1].isdigit() or s[i + 1] == 'R'):
            i += 2; continue
        if c == '{':
            j = s.index('}', i); i = j + 1; continue
        o = ord(c)
        if 0x20 <= o < 0x80:
            x += w[o - 0x20]
        elif 0xFF61 <= o <= 0xFF9F:
            x += 12 if font == 22 else 14
        else:
            x += 22 if font == 22 else 26
        x += space
        i += 1
    return x


def wrap(text, limit, font=22, space=0, indent=''):
    """Greedy word wrap of one paragraph to `limit` px. Returns lines."""
    words = text.split(' ')
    lines = []; cur = indent
    for wd in words:
        cand = (cur + ' ' + wd) if cur.strip() else (cur + wd)
        if text_width(cand, font, space) <= limit:
            cur = cand
        else:
            if cur.strip():
                lines.append(cur)
            cur = wd
            while text_width(cur, font, space) > limit:      # very long token: hard split
                k = len(cur)
                while k > 1 and text_width(cur[:k], font, space) > limit:
                    k -= 1
                lines.append(cur[:k]); cur = cur[k:]
    if cur.strip():
        lines.append(cur)
    return lines


# ---- library entries -------------------------------------------------------
LIBRARY = {'1271_02471', '1271_10345'}
LIB_LIMIT = 309
HEADER = re.compile(r'^%\d.*%\d$')


def library_layout(en):
    """Draft format: one logical line per line; lines starting with '> ' are
    paragraphs to wrap (indented two spaces). Returns final text (with the row's
    trailing {x00} kept) and a list of problems."""
    probs = []
    body, tail = en, ''
    if body.endswith('{x00}'):
        body, tail = body[:-5], '{x00}'
    out = []
    for line in body.split('\n'):
        if line.startswith('> '):
            out += wrap(line[2:].strip(), LIB_LIMIT, 22, 0, indent='  ')
        else:
            out.append(line)
    while out and out[-1] == '':
        out.pop()
    for i, l in enumerate(out):
        if text_width(l, 22) > LIB_LIMIT:
            probs.append(f'line {i + 1} {text_width(l, 22)}px > {LIB_LIMIT}: {l!r}')
        if len(l.encode('cp932', 'replace')) > 63:
            probs.append(f'line {i + 1} {len(l.encode("cp932", "replace"))} bytes > 63')
    if len(out) > 64:
        probs.append(f'{len(out)} lines > 64')
    return '\n'.join(out) + '\n' + tail, probs, len(out)


# ---- dialogue (msgStrCreate window: 468 x 78, 26px font, 3 lines/page) ----------
DIALOGUE_LIMIT = 468
DIALOGUE_LINES = 3
NOT_DIALOGUE = LIBRARY | {'2271_06810', '2368_07367', '2364_10351'}


def dialogue_layout(row_text):
    """Wrap over-long lines inside each page (word wrap at 468 px), then check
    <= 3 lines per page. Returns (text, problems)."""
    import segments
    parts, idx = segments.split(row_text)
    probs = []
    for i in idx:
        seg = parts[i]
        lines = []
        for ln in seg.split('\n'):
            lines += wrap(ln, DIALOGUE_LIMIT, 26, 0) if text_width(ln, 26) > DIALOGUE_LIMIT else [ln]
        parts[i] = '\n'.join(lines)
    out = ''.join(parts)
    for k, pg in enumerate(segments.pages(out)):
        ls = pg.split('\n')
        if len(ls) > DIALOGUE_LINES:
            probs.append(f'page {k + 1}: {len(ls)} lines > {DIALOGUE_LINES}: {pg[:60]!r}')
    return out, probs


if __name__ == '__main__':
    s = ' '.join(sys.argv[1:]) or 'The quick brown fox jumps over the lazy dog.'
    print(text_width(s, 22), text_width(s, 26))
