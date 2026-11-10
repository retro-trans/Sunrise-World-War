"""Opening-song cues for SLPS-25270's IPU movie player."""

import json
import os
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from dbg.mips import (Asm, NOP, addiu, addu, and_, andi, j, jal, la, lbu, lhu,
                      lui, lw, ori, pack, sll, sltiu, sltu, srl, subu, sw)


ROOT = Path(__file__).resolve().parent.parent
CUE_FILE = ROOT / 'work/translation/en/subtitles/opening.en.json'
ROMAJI_FILE = ROOT / 'work/translation/ja-Latn/subtitles/opening.json'
VA_TO_FILE = 0xFF000
UPLOAD_CALL = 0x10C38C
UPLOAD = 0x10CB20
OPENING_FRAMES = 2733
OPENING_DATA_SIZE = 0x441F0A3
FPS = 30
GLYPH_WIDTH = 11
GLYPH_HEIGHT = 20
ROMAJI_TOP = 372
ENGLISH_TOP = 404
INK = 0x80F8F8F8
BACKGROUND = 0x80181818

# Subranges of the unreferenced routines listed in elfstrings_build.DEAD.
CODE, CODE_END = 0x1E9C58, 0x1EA65C
FONT, FONT_END = 0x175DF0, 0x1767F0
RESERVED = ((CODE, CODE_END), (FONT, FONT_END))


def load_cues():
    english = json.loads(CUE_FILE.read_text(encoding='utf-8'))
    romaji = json.loads(ROMAJI_FILE.read_text(encoding='utf-8')) if ROMAJI_FILE.is_file() else {}
    cues = []
    previous_end = 0
    for start, end, line in english:
        if not previous_end <= start < end <= OPENING_FRAMES * 1000 // FPS:
            raise ValueError(f'invalid or overlapping movie subtitle cue: {start}–{end}')
        lines = (romaji.pop(str(start)), line) if str(start) in romaji else (line,)
        for text in lines:
            if not text or not text.isascii() or not text.isprintable() or (len(text) + 2) * GLYPH_WIDTH > 580:
                raise ValueError(f'movie subtitle does not fit the safe area: {text!r}')
        cues.append((start, end, lines))
        previous_end = end
    if romaji:
        raise ValueError(f'romaji starts without a matching English cue: {list(romaji)}')
    if not cues:
        raise ValueError('opening subtitle cue sheet is empty')
    return cues


def _frame(ms):
    return (ms * FPS + 999) // 1000


def _assets(cues):
    font_path = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts/consola.ttf'
    font = ImageFont.truetype(str(font_path), 18)
    chars = sorted(set(''.join(line for _, _, lines in cues for line in lines) + ' '))
    indices = {ch: i for i, ch in enumerate(chars)}
    atlas = bytearray()
    for ch in chars:
        glyph = Image.new('L', (GLYPH_WIDTH, GLYPH_HEIGHT))
        ImageDraw.Draw(glyph).text((0, 16), ch, anchor='ls', font=font, fill=255)
        for y in range(GLYPH_HEIGHT):
            mask = sum((glyph.getpixel((x, y)) >= 110) << x for x in range(GLYPH_WIDTH))
            atlas += struct.pack('<H', mask)

    records = bytearray()
    for start, end, lines in cues:
        width = max(map(len, lines)) + 2
        x = (640 - width * GLYPH_WIDTH) // 2
        stride = 8 + (width + 3) // 4 * 4
        records += struct.pack('<HHI', _frame(start), _frame(end), 8 + stride * len(lines))
        for i, line in enumerate(lines):
            remaining = len(lines) - i - 1
            top = ROMAJI_TOP if remaining else ENGLISH_TOP
            glyphs = bytes(indices[ch] for ch in line.center(width))
            records += struct.pack('<HHBBH', x, top, width, remaining, stride)
            records += glyphs + bytes(-width % 4)
    records += struct.pack('<HHI', OPENING_FRAMES, 0, 0)
    return bytes(atlas), bytes(records)


def _renderer(table):
    a = Asm(CODE)
    # Match ipumTransTexture's ready flags and the opening's exact ipum header.
    for off, expected in ((0, 0x104), (4, OPENING_FRAMES * 2),
                          (0x10, 40), (0x14, 28), (0x0C, OPENING_DATA_SIZE)):
        a(lw('v0', off, 'a0'))
        if off == 0:
            a(andi('v0', 'v0', expected))
        a(la('v1', expected))
        a.br('bne', 'v0', 'v1', 'upload'); a(NOP)
    a(lw('v0', 8, 'a0'), srl('v0', 'v0', 1), la('a1', table))
    a.label('cue')
    a(lhu('t0', 0, 'a1'), sltu('t1', 'v0', 't0'))
    a.br('bnez', 't1', 'upload'); a(lhu('t0', 2, 'a1'))
    a(sltu('t1', 'v0', 't0'))
    a.br('bnez', 't1', 'draw'); a(lw('t0', 4, 'a1'))
    a.br('beqz', 't0', 'upload'); a(NOP)
    a.br('b', 'cue'); a(addu('a1', 'a1', 't0'))

    a.label('draw')
    # Paint the decoded RGB32 macroblocks through the uncached EE alias, before
    # the game's DMA takes the pixels. Leave the decoder and original upload intact.
    a(lw('t1', -0x74, 'gp'), lui('v0', 0x2000))
    a(lui('v1', 0x01ff), ori('v1', 'v1', 0xffff), and_('t1', 't1', 'v1'), addu('t1', 't1', 'v0'))
    a(la('a3', FONT), la('t8', INK ^ BACKGROUND), la('t9', BACKGROUND), addiu('a1', 'a1', 8))
    a.label('line')
    a(addiu('t0', 'zero', 0))
    a.label('row')
    a(lhu('v0', 2, 'a1'), addu('v0', 'v0', 't0'), srl('t3', 'v0', 4), sll('t6', 't3', 13), sll('t3', 't3', 15))
    a(andi('v0', 'v0', 15), sll('v0', 'v0', 6), addu('t3', 't3', 't6'), addu('t3', 't3', 'v0'))
    a(addu('t3', 't3', 't1'), lhu('t2', 0, 'a1'), lbu('v1', 4, 'a1'), addiu('a2', 'a1', 8))
    a(addu('v1', 'v1', 'a2'))
    a.label('glyph')
    a(lbu('v0', 0, 'a2'), sll('t4', 'v0', 5), sll('v0', 'v0', 3), addu('t4', 't4', 'v0'))
    a(sll('v0', 't0', 1), addu('t4', 't4', 'v0'), addu('t4', 't4', 'a3'), lhu('t4', 0, 't4'))
    a(addiu('t5', 'zero', GLYPH_WIDTH))
    a.label('pixel')
    a(andi('t6', 't2', 0xfff0), sll('t6', 't6', 6), andi('t7', 't2', 15), sll('t7', 't7', 2))
    a(addu('t7', 't7', 't6'), addu('t7', 't7', 't3'), andi('v0', 't4', 1), subu('v0', 'zero', 'v0'))
    a(and_('v0', 'v0', 't8'), addu('v0', 'v0', 't9'), sw('v0', 0, 't7'))
    a(addiu('t5', 't5', -1), addiu('t2', 't2', 1))
    a.br('bnez', 't5', 'pixel'); a(srl('t4', 't4', 1))
    a(addiu('a2', 'a2', 1))
    a.br('bne', 'a2', 'v1', 'glyph'); a(NOP)
    a(addiu('t0', 't0', 1), sltiu('v0', 't0', GLYPH_HEIGHT))
    a.br('bnez', 'v0', 'row'); a(NOP)
    a(lbu('v0', 5, 'a1'))
    a.br('beqz', 'v0', 'upload'); a(lhu('v0', 6, 'a1'))
    a.br('b', 'line'); a(addu('a1', 'a1', 'v0'))
    a.label('upload')
    a(j(UPLOAD), NOP)
    return a.assemble()


def patches(source):
    atlas, cues = _assets(load_cues())
    size = len(_renderer(0))
    code = _renderer(CODE + size) + cues
    if CODE + len(code) > CODE_END or FONT + len(atlas) > FONT_END:
        raise ValueError('opening subtitles exceed reserved ELF space')
    return [
        (CODE, source[CODE - VA_TO_FILE:CODE - VA_TO_FILE + len(code)], code, 'opening subtitle renderer and cues'),
        (FONT, source[FONT - VA_TO_FILE:FONT - VA_TO_FILE + len(atlas)], atlas, 'opening subtitle glyphs'),
        (UPLOAD_CALL, pack([jal(UPLOAD)]), pack([jal(CODE)]), 'opening subtitle hook'),
    ]


def srt():
    def timestamp(ms):
        seconds, remainder = divmod(ms, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f'{hours:02d}:{minutes:02d}:{seconds:02d},{remainder:03d}'

    return '\n\n'.join(f'{i}\n{timestamp(start)} --> {timestamp(end)}\n' + '\n'.join(lines)
                       for i, (start, end, lines) in enumerate(load_cues(), 1)) + '\n'
