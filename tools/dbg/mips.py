"""Tiny R5900 instruction encoder (just what the hooks and VWF need)."""
import struct

R = {n: i for i, n in enumerate(
    'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}


def _r(x):
    return R[x] if isinstance(x, str) else x


def i_type(op, rs, rt, imm):
    return (op << 26) | (_r(rs) << 21) | (_r(rt) << 16) | (imm & 0xFFFF)


def r_type(rs, rt, rd, sa, fn):
    return (_r(rs) << 21) | (_r(rt) << 16) | (_r(rd) << 11) | (sa << 6) | fn


def lui(rt, imm): return i_type(0x0F, 0, rt, imm)
def addiu(rt, rs, imm): return i_type(0x09, rs, rt, imm)
def ori(rt, rs, imm): return i_type(0x0D, rs, rt, imm)
def andi(rt, rs, imm): return i_type(0x0C, rs, rt, imm)
def slti(rt, rs, imm): return i_type(0x0A, rs, rt, imm)
def sltiu(rt, rs, imm): return i_type(0x0B, rs, rt, imm)
def lw(rt, off, rs): return i_type(0x23, rs, rt, off)
def sw(rt, off, rs): return i_type(0x2B, rs, rt, off)
def lbu(rt, off, rs): return i_type(0x24, rs, rt, off)
def lb(rt, off, rs): return i_type(0x20, rs, rt, off)
def lhu(rt, off, rs): return i_type(0x25, rs, rt, off)
def sb(rt, off, rs): return i_type(0x28, rs, rt, off)
def sh(rt, off, rs): return i_type(0x29, rs, rt, off)
def ld(rt, off, rs): return i_type(0x37, rs, rt, off)
def sd(rt, off, rs): return i_type(0x3F, rs, rt, off)
def beq(rs, rt, off): return i_type(0x04, rs, rt, off)
def bne(rs, rt, off): return i_type(0x05, rs, rt, off)
def blez(rs, off): return i_type(0x06, rs, 0, off)
def bgtz(rs, off): return i_type(0x07, rs, 0, off)
def beqz(rs, off): return beq(rs, 'zero', off)
def bnez(rs, off): return bne(rs, 'zero', off)
def addu(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x21)
def subu(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x23)
def daddu(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x2D)
def or_(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x25)
def and_(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x24)
def nor(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x27)
def sltu(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x2B)
def slt(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x2A)
def sll(rd, rt, sa): return r_type(0, rt, rd, sa, 0x00)
def srl(rd, rt, sa): return r_type(0, rt, rd, sa, 0x02)
def sra(rd, rt, sa): return r_type(0, rt, rd, sa, 0x03)
def jr(rs): return r_type(rs, 0, 0, 0, 0x08)
def mult3(rd, rs, rt): return r_type(rs, rt, rd, 0, 0x18)   # R5900: rd = LO = rs*rt
def div(rs, rt): return r_type(rs, rt, 0, 0, 0x1A)
def mfhi(rd): return r_type(0, 0, rd, 0, 0x10)
def jalr(rs, rd='ra'): return r_type(rs, 0, rd, 0, 0x09)
def move(rd, rs): return daddu(rd, rs, 'zero')
def j(target): return (0x02 << 26) | ((target >> 2) & 0x3FFFFFF)
def jal(target): return (0x03 << 26) | ((target >> 2) & 0x3FFFFFF)
NOP = 0


def hi(addr):
    """upper half for lui when the low half is used as a signed offset"""
    return ((addr + 0x8000) >> 16) & 0xFFFF


def lo(addr):
    return addr & 0xFFFF


def la(rt, addr):
    return [lui(rt, hi(addr)), addiu(rt, rt, lo(addr))]


def pack(words):
    return b''.join(struct.pack('<I', w & 0xFFFFFFFF) for w in words)


class Asm:
    """Assembler with labels for short routines. Branch targets are labels."""

    def __init__(self, base):
        self.base = base
        self.items = []
        self.labels = {}

    def label(self, name):
        self.labels[name] = self.base + 4 * len(self.items)

    def __call__(self, *ws):
        for w in ws:
            if isinstance(w, list):
                self.items.extend(w)
            else:
                self.items.append(w)

    def br(self, kind, *args):
        """kind in beq/bne/beqz/bnez/blez/bgtz/b; last arg is a label"""
        self.items.append((kind, args))

    def pc(self):
        return self.base + 4 * len(self.items)

    def assemble(self):
        out = []
        for i, it in enumerate(self.items):
            if isinstance(it, tuple):
                kind, args = it
                *regs, lab = args
                off = (self.labels[lab] - (self.base + 4 * i + 4)) >> 2
                if kind == 'b':
                    out.append(beq('zero', 'zero', off))
                else:
                    out.append(globals()[kind](*regs, off))
            else:
                out.append(it)
        return pack(out)
