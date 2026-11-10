"""VWF and debug-monitor patches for SLPS_252.70 (Sunrise World War).

All window text (dialogue, menus, library) is drawn by windPutText/windPutTextDirect
-> _PutSjisWindow -> fntPutSjisPSMT4/8 -> PutIdx{4,8}TextureFont{22,26}Sjis, and each
advance (and windGetStrPixelLength) comes from GetRomFontDispSizeX. So:

  * GetRomFontDispSizeX: single-byte 0x20-0x7F in font types 0 (22px) and 1 (26px)
    return a per-glyph advance from WIDTHS; everything else keeps original behaviour.
  * PutIdx4TextureFont26Sjis / 22Sjis: replaced by a nibble-accurate 4bpp blitter.
    The originals copy whole bytes at x/2, so odd x snapped left and a byte holding
    one ink nibble overwrote the neighbour's pixel. PSMT8 putters are already exact.
  * ASCII glyph images in pack 0002 (res 0x2858 26px 12x24, res 0x2855 22px 10x20)
    are replaced with proportional glyphs (tools/fontgen.py).
  * ReadPad monitor: ORs MAILBOX+4 into port 0's button word, counts reads (frame
    clock), keeps the last word. Used by tools/dbg/control.py through PINE.

Code lives in the unreferenced libkernel IO wrappers sceMkdir..sceUmount
(0x210060-0x21137C, checked with tools/deadcode.py; no code/data references).
"""
import os, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'dbg'))
sys.path.insert(0, os.path.dirname(__file__))
from mips import *
import fontgen

REGION = (0x210060, 0x21137C)
MAILBOX = 0x210060          # +0 'SWWM' +4 inject mask +8 pad-read counter +12 last buttons +16 build tag
MONITOR = 0x210080
WIDTHS = 0x210100           # 96 bytes 22px (type 0) then 96 bytes 26px (type 1)
WIDTH_FN = 0x2101C0
BLIT = 0x210240
FRONT26 = 0x210340
FRONT22 = 0x2103C0
REGION_USED_END = 0x210440

GET_DISP_X = 0x15DF20       # GetRomFontDispSizeX
GET_DISP_X_SINGLE = 0x15DF30
GET_DISP_X_DBCS = 0x15DFA0
GET26 = 0x15DE08            # Get26x26x4FontAddr
GET22 = 0x15DCD8            # Get22x22x4FontAddr
PUT4_26 = 0x15E1F8
PUT4_22 = 0x15E108
PAD_HOOK = 0x15A304         # ReadPad: nor v1,zero,v1 ; andi v1,v1,0xffff

FONT_PACK_FILE = 2
FONT26_RID = 0x2858         # 96 glyphs, 0x20-0x7F, 12x24 4bpp
FONT22_RID = 0x2855         # 120 glyphs, 0x20-0x97, 10x20 4bpp


def width_fn():
    a = Asm(WIDTH_FN)
    a(andi('a0', 'a0', 0xFFFF), andi('v0', 'a0', 0xFF00))
    a.br('bnez', 'v0', 'dbcs'); a(lw('v1', 0x90, 'gp'))
    a(sltiu('at', 'v1', 2))
    a.br('beqz', 'at', 'orig'); a(addiu('v0', 'a0', -0x20))
    a(sltiu('at', 'v0', 0x60))
    a.br('beqz', 'at', 'orig'); a(sll('at', 'v1', 5))
    a(addu('v0', 'v0', 'at'), sll('at', 'v1', 6), addu('v0', 'v0', 'at'),
      lui('at', hi(WIDTHS)), addu('at', 'at', 'v0'),
      jr('ra'), lbu('v0', lo(WIDTHS), 'at'))
    a.label('orig'); a(j(GET_DISP_X_SINGLE), NOP)
    a.label('dbcs'); a(j(GET_DISP_X_DBCS), NOP)
    return a.assemble()


def blit_fn():
    """a0 tex, a1 x, a2 y, a3 glyph, t0 cell width (even), t1 rows. Leaf; clobbers
    at v0 v1 a3 t2-t9 HI/LO. Texture height 0x8C(gp), row stride (pixels) 0x88(gp)."""
    a = Asm(BLIT)
    a(lw('t2', 0x8C, 'gp'), lw('t9', 0x88, 'gp'), move('t3', 'zero'))
    a.label('row')
    a(addu('t4', 'a2', 't3'), slt('at', 't4', 't2'))
    a.br('bnez', 'at', 'nowrap'); a(NOP)
    a(div('t4', 't2'), mfhi('t4'))
    a.label('nowrap')
    a(mult3('t5', 't4', 't9'), addu('t5', 't5', 'a1'), move('t6', 'zero'))
    a.label('col')
    a(lbu('t7', 0, 'a3'), andi('t8', 't7', 15))
    a.br('beqz', 't8', 'skip0'); a(addu('v0', 't5', 't6'))
    pix(a, 'p0')
    a.label('skip0')
    a(srl('t8', 't7', 4))
    a.br('beqz', 't8', 'skip1'); a(addu('v0', 't5', 't6'))
    a(addiu('v0', 'v0', 1))
    pix(a, 'p1')
    a.label('skip1')
    a(addiu('a3', 'a3', 1), addiu('t6', 't6', 2), slt('at', 't6', 't0'))
    a.br('bnez', 'at', 'col'); a(NOP)
    a(addiu('t3', 't3', 1), slt('at', 't3', 't1'))
    a.br('bnez', 'at', 'row'); a(NOP)
    a(jr('ra'), NOP)
    return a.assemble()


def pix(a, tag):
    """write nibble t8 at pixel index v0 of texture a0 (uses v0 v1 at)"""
    a(srl('v1', 'v0', 1), addu('v1', 'v1', 'a0'), andi('at', 'v0', 1))
    a.br('bnez', 'at', tag + 'odd'); a(lbu('v0', 0, 'v1'))
    a(andi('v0', 'v0', 0xF0))
    a.br('b', tag + 'done'); a(or_('v0', 'v0', 't8'))
    a.label(tag + 'odd')
    a(andi('v0', 'v0', 0x0F), sll('at', 't8', 4), or_('v0', 'v0', 'at'))
    a.label(tag + 'done')
    a(sb('v0', 0, 'v1'))


def front_fn(base, getaddr, narrow, wide, rows):
    a = Asm(base)
    a(addiu('sp', 'sp', -0x30), sd('s0', 0, 'sp'), sd('s1', 8, 'sp'), sd('s2', 0x10, 'sp'),
      sd('s3', 0x18, 'sp'), sd('ra', 0x20, 'sp'),
      move('s0', 'a0'), move('s1', 'a1'), move('s2', 'a2'), andi('s3', 'a3', 0xFFFF),
      jal(getaddr), move('a0', 's3'),
      move('a3', 'v0'), move('a0', 's0'), move('a1', 's1'), move('a2', 's2'),
      andi('v0', 's3', 0xFF00), addiu('t0', 'zero', narrow))
    a.br('beqz', 'v0', 'go'); a(addiu('t1', 'zero', rows))
    a(addiu('t0', 'zero', wide))
    a.label('go')
    a(jal(BLIT), NOP,
      move('a0', 's3'), ld('s0', 0, 'sp'), ld('s1', 8, 'sp'), ld('s2', 0x10, 'sp'),
      ld('s3', 0x18, 'sp'), ld('ra', 0x20, 'sp'),
      j(GET_DISP_X), addiu('sp', 'sp', 0x30))
    return a.assemble()


def monitor_fn():
    a = Asm(MONITOR)
    a(andi('v1', 'v1', 0xFFFF))
    a.br('bnez', 's3', 'done'); a(NOP)          # s3 = pad port in ReadPad; port 0 only
    a(addiu('sp', 'sp', -16), sd('t9', 0, 'sp'), lui('at', hi(MAILBOX)),
      lw('t9', lo(MAILBOX + 4), 'at'), or_('v1', 'v1', 't9'),
      lw('t9', lo(MAILBOX + 8), 'at'), addiu('t9', 't9', 1), sw('t9', lo(MAILBOX + 8), 'at'),
      sw('v1', lo(MAILBOX + 12), 'at'), ld('t9', 0, 'sp'), addiu('sp', 'sp', 16))
    a.label('done')
    a(jr('ra'), NOP)
    return a.assemble()


def widths():
    _, a22 = fontgen.build(22, 96)
    _, a26 = fontgen.build(26, 96)
    out = bytearray()
    for adv in (a22, a26):
        for w in adv:
            if w == 6:      # windPutText treats an advance of 6 as a dakuten (adds to +0xE0)
                w = 7
            out.append(w)
    return bytes(out)


def font_members(orig22, orig26):
    """Return replacement bytes for res 0x2855 (22px, 120 glyphs) and 0x2858 (26px)."""
    g26, _ = fontgen.build(26, 96)
    assert len(g26) == len(orig26) == 96 * 144
    g22, _ = fontgen.build(22, 96)
    assert len(orig22) == 120 * 100
    g22 = g22 + orig22[96 * 100:]           # keep codes 0x80-0x97 as shipped
    return g22, g26


# ---- dialogue typewriter space ----------------------------------------------------
# TextWaitPutProc (0x161DB8) replaces an ASCII space with the string at 0x2ED4D0,
# "\xA1\xA1" (two half-width full stops, blank in the Japanese font). With the English
# font those draw two "｡" marks per space; make the string a plain ASCII space.
TYPE_SPACE = 0x2ED4D0

# ---- telops (location captions) ---------------------------------------------------
# telopMainProcess (0x118870) centres the caption as 27 px per 2 bytes and draws it two
# bytes per fixed 26 px cell, dropping the last byte of an odd-length string. English
# needs the real pixel width and proportional advances:
#  * TELOP_W replaces the width maths: v0 = pixel width (GetRomFontDispSizeX per char),
#    s4 = (len + 1) / 2 steps (loop count; the last odd byte is no longer lost).
#  * Each step draws the whole prefix (2 more bytes per step) at the caption's left edge
#    through TELOP_DRAW, which NUL-terminates the prefix in place around the call.
TELOP_FN = 0x118870
TELOP_WIDTH_AT = 0x1188EC
TELOP_STEP_AT = 0x118B3C
WIND_PUT_TEXT_XY = 0x161950
TELOP_W = 0x210600
TELOP_DRAW = 0x2106C0


def telop_w_fn():
    a = Asm(TELOP_W)
    # measured before the telop window sets the font: use the 26px type it draws with
    a(addiu('sp', 'sp', -16), sd('ra', 0, 'sp'), lw('s1', 0, 's5'), move('s2', 'zero'), move('s3', 's1'),
      lw('at', 0x90, 'gp'), sw('at', 8, 'sp'), addiu('at', 'zero', 1), sw('at', 0x90, 'gp'))
    a.label('loop')
    a(lbu('a0', 0, 's1'))
    a.br('beqz', 'a0', 'done'); a(addiu('s1', 's1', 1))
    a(sltiu('at', 'a0', 0x80))
    a.br('bnez', 'at', 'one'); a(NOP)
    a(sltiu('at', 'a0', 0xA0))
    a.br('bnez', 'at', 'two'); a(NOP)
    a(sltiu('at', 'a0', 0xE0))
    a.br('bnez', 'at', 'one'); a(NOP)
    a.label('two')
    a(lbu('at', 0, 's1'), sll('a0', 'a0', 8), or_('a0', 'a0', 'at'), addiu('s1', 's1', 1))
    a.label('one')
    a(jal(WIDTH_FN), NOP)
    a.br('b', 'loop'); a(addu('s2', 's2', 'v0'))
    a.label('done')
    a(lw('at', 8, 'sp'), sw('at', 0x90, 'gp'), subu('v0', 's1', 's3'), srl('s4', 'v0', 1), move('v0', 's2'),
      ld('ra', 0, 'sp'), jr('ra'), addiu('sp', 'sp', 16))
    return a.assemble()


def telop_draw_fn():
    """windPutTextXY(a0, a1, a2, a3) with t0 = end of the prefix to draw."""
    a = Asm(TELOP_DRAW)
    a(addiu('sp', 'sp', -16), sd('ra', 0, 'sp'), sw('t0', 8, 'sp'), lbu('t1', 0, 't0'),
      sb('t1', 12, 'sp'), jal(WIND_PUT_TEXT_XY), sb('zero', 0, 't0'),
      lw('t0', 8, 'sp'), lbu('t1', 12, 'sp'), sb('t1', 0, 't0'),
      ld('ra', 0, 'sp'), jr('ra'), addiu('sp', 'sp', 16))
    return a.assemble()


MTC1_ZERO_F0 = 0x44800000


def telop_patches():
    width_old = bytes.fromhex('03000424 42a00200 1b000402 c0101400 23105400 80020324 80100200 01008050 cd010000 23105400')
    # strlen's result is ignored; TELOP_W walks the string itself. divu s0/3 stays (mfhi s0 later)
    width_new = pack([jal(TELOP_W), NOP, addiu('a0', 'zero', 3), 0x0204001B, addiu('v1', 'zero', 0x280),
                      NOP, NOP, NOP, NOP, NOP])
    step_old = bytes.fromhex('0000a38e 00009344 20008046 1a007326 40101100 01003126 21104300 2d204002 00004690'
                             '2d28c002 00d00046 2d380000 1000a6a3 01004390 64000046 00080644 1200a0a3 1100a3a3'
                             '700000ae 5486050c 740000ae')
    step_new = pack([lw('v1', 0, 's5'), MTC1_ZERO_F0, 0x46800020, addiu('s3', 's3', 0x1A), sll('v0', 's1', 1),
                     addiu('s1', 's1', 1), addu('v0', 'v0', 'v1'), move('a0', 's2'), addiu('t0', 'v0', 2),
                     move('a1', 'v1'), 0x4600D000, move('a3', 'zero'), NOP, NOP, 0x46000064, 0x44060800,
                     NOP, NOP, sw('zero', 0x70, 's0'), jal(TELOP_DRAW), sw('zero', 0x74, 's0')])
    return [(TELOP_W, None, telop_w_fn(), 'telop pixel width + step count'),
            (TELOP_DRAW, None, telop_draw_fn(), 'telop prefix draw'),
            (TELOP_WIDTH_AT, width_old, width_new, 'telopMainProcess: centre on pixel width'),
            (TELOP_STEP_AT, step_old, step_new, 'telopMainProcess: draw growing prefix proportionally')]


def patches(elf_bytes, monitor=True, vwf=True, tag=b'v0.0'):
    """[(va, expected_old_bytes_or_None, new_bytes, purpose)]"""
    ch = []
    if vwf:
        ch.append((WIDTHS, None, widths(), 'VWF advance table (22px, 26px)'))
        ch.append((WIDTH_FN, None, width_fn(), 'VWF width routine'))
        ch.append((BLIT, None, blit_fn(), 'nibble-accurate 4bpp glyph blit'))
        ch.append((FRONT26, None, front_fn(FRONT26, GET26, 12, 24, 24), 'PutIdx4 26px front-end'))
        ch.append((FRONT22, None, front_fn(FRONT22, GET22, 10, 20, 20), 'PutIdx4 22px front-end'))
        ch.append((GET_DISP_X, pack([andi('a0', 'a0', 0xFFFF), andi('v0', 'a0', 0xFF00)]),
                   pack([j(WIDTH_FN), NOP]), 'GetRomFontDispSizeX -> VWF width'))
        ch.append((PUT4_26, bytes.fromhex('d0ffbd270000b0ff'), pack([j(FRONT26), NOP]), 'PutIdx4TextureFont26Sjis -> VWF blit'))
        ch.append((PUT4_22, bytes.fromhex('d0ffbd270000b0ff'), pack([j(FRONT22), NOP]), 'PutIdx4TextureFont22Sjis -> VWF blit'))
        ch.append((TYPE_SPACE, b'\xa1\xa1\x00', b' \x00\x00', 'typewriter space -> ASCII space'))
        ch += telop_patches()
    if monitor:
        ch.append((MAILBOX, None, b'SWWM' + bytes(12) + tag[:16].ljust(16, b'\0'), 'debug mailbox'))
        ch.append((MONITOR, None, monitor_fn(), 'pad monitor'))
        ch.append((PAD_HOOK, pack([nor('v1', 'zero', 'v1'), andi('v1', 'v1', 0xFFFF)]),
                   pack([jal(MONITOR), nor('v1', 'zero', 'v1')]), 'ReadPad -> pad monitor'))
    for va, old, new, why in ch:
        if REGION[0] <= va < REGION[1]:
            assert va + len(new) <= REGION[1], why
    # no overlaps between region items
    spans = sorted((va, va + len(new), why) for va, old, new, why in ch if REGION[0] <= va < REGION[1])
    for (a0, a1, w0), (b0, b1, w1) in zip(spans, spans[1:]):
        assert a1 <= b0, ('overlap', w0, w1, hex(a1), hex(b0))
    return ch


if __name__ == '__main__':
    for va, old, new, why in patches(b''):
        print(f'{va:08x} {len(new):4d} {why}')


# ---------------------------------------------------------------------------
# Library preview (debug builds only, build.py --preview)
#
# Title menu case 0 (Story, the default cursor item; jump table 0x2DDCE0[0]) goes to
# DRIVER instead of 0x1526E0. DRIVER loads
# deckmenu.pac (pfr id 1272: tables 2471 machine/ship, 10345 pilot) and then loops on
# thrdPass. When the host writes a kind (1 machine, 2 pilot, 4 ship) to LIBBOX+4 it
# calls deckmItemIntroView(0, kind, LIBBOX+8) - the game's own library window with
# its own scrolling - and returns to the loop when Circle/Cross closes it. LIBBOX+20
# = 1 unloads the pack and continues the original Story path.
LIBBOX = 0x210460       # +0 'SWWL' +4 kind +8 index +12 busy +16 shown count +20 exit +24 heartbeat
DRIVER = 0x210480
MENU_TABLE = 0x2DDCE0
STORY_CASE = 0x1526E0
PFR_LOAD = 0x1073C0
PFR_UNLOAD = 0x107460
THRD_PASS = 0x101EB8
INTRO_VIEW = 0x190B68
DECKMENU_PFR = 1272


def driver_fn():
    a = Asm(DRIVER)
    a(addiu('sp', 'sp', -0x10), jal(PFR_LOAD), addiu('a0', 'zero', DECKMENU_PFR))
    a.label('loop')
    a(jal(THRD_PASS), NOP, lui('at', hi(LIBBOX)), lw('v0', lo(LIBBOX + 24), 'at'),
      addiu('v0', 'v0', 1), sw('v0', lo(LIBBOX + 24), 'at'), lw('v0', lo(LIBBOX + 20), 'at'))
    a.br('bnez', 'v0', 'exit'); a(lw('a1', lo(LIBBOX + 4), 'at'))
    a.br('beqz', 'a1', 'loop'); a(lw('a2', lo(LIBBOX + 8), 'at'))
    a(sw('zero', lo(LIBBOX + 4), 'at'), addiu('v0', 'zero', 1), sw('v0', lo(LIBBOX + 12), 'at'),
      jal(INTRO_VIEW), move('a0', 'zero'),
      lui('at', hi(LIBBOX)), sw('zero', lo(LIBBOX + 12), 'at'), lw('v0', lo(LIBBOX + 16), 'at'),
      addiu('v0', 'v0', 1))
    a.br('b', 'loop'); a(sw('v0', lo(LIBBOX + 16), 'at'))
    a.label('exit')
    a(sw('zero', lo(LIBBOX + 20), 'at'), jal(PFR_UNLOAD), addiu('a0', 'zero', DECKMENU_PFR),
      j(STORY_CASE), addiu('sp', 'sp', 0x10))
    return a.assemble()


def preview_patches():
    code = driver_fn()
    assert DRIVER + len(code) <= REGION[1]
    return [(LIBBOX, None, b'SWWL' + bytes(28), 'library preview mailbox'),
            (DRIVER, None, code, 'library preview driver'),
            (MENU_TABLE, struct.pack('<I', STORY_CASE), struct.pack('<I', DRIVER),
             'title menu Story -> library preview driver')]
