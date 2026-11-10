"""Split ATMB rows into translatable segments and reassemble them exactly.

A segment is a run of text between control records ({C:..}/{x..}) and page breaks
(two or more newlines). Single newlines inside a segment are line breaks on the same
page. Leading/trailing newlines and all separators stay outside the segments, so
untranslated rows reassemble byte-identically (verified on every row by `selftest`).

  py -3.11 tools/segments.py selftest
"""
import re

SEP = re.compile(r'(\{C:[0-9A-Fa-f]+\}|\{x[0-9A-Fa-f]{2}\}|\n{2,})')


def split(text):
    """-> (parts, seg_index): parts is a list of strings; seg_index lists the positions
    in parts that are translatable segments."""
    parts = []
    segs = []
    for piece in SEP.split(text):
        if piece == '':
            continue
        if SEP.fullmatch(piece):
            parts.append(piece); continue
        m = re.match(r'^(\n*)(.*?)(\n*)$', piece, re.S)
        lead, core, tail = m.groups()
        if lead:
            parts.append(lead)
        if core.strip():
            segs.append(len(parts)); parts.append(core)
        elif core:
            parts.append(core)
        if tail:
            parts.append(tail)
    return parts, segs


def segments(text):
    parts, idx = split(text)
    return [parts[i] for i in idx]


def join(text, new_segments):
    parts, idx = split(text)
    if len(new_segments) != len(idx):
        raise ValueError(f'segment count {len(new_segments)} != {len(idx)}')
    for i, s in zip(idx, new_segments):
        if s is not None and s != '':
            parts[i] = s
    return ''.join(parts)


def pages(text):
    """Visible text of each page (controls removed), for layout checks."""
    out = []
    for pg in re.split(r'\n{2,}', text):
        vis = re.sub(r'\{C:[0-9A-Fa-f]+\}|\{x[0-9A-Fa-f]{2}\}', '', pg).strip('\n')
        if vis.strip():
            out.append(vis)
    return out


if __name__ == '__main__':
    import glob, json, sys
    n = segs = 0
    for p in glob.glob('work/source/text/*.json'):
        for r in json.load(open(p, encoding='utf-8'))['rows']:
            parts, idx = split(r['jp'])
            assert ''.join(parts) == r['jp'], (p, r['id'])
            assert join(r['jp'], [None] * len(idx)) == r['jp']
            n += 1; segs += len(idx)
    print(f'selftest ok: {n} rows, {segs} segments')
