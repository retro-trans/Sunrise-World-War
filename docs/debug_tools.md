# Debug tools — Sunrise World War (SLPS-25270)

Method: `debug_tools_guide.md`. Emulator: portable PCSX2 2.x in `work/emulator/pcsx2`
(runtime + BIOS copied from the sibling Sunrise Eiyuutan 2 project by
`tools/dbg/setup.py`), muted (`nullout`, volume 0), fast boot, one test memory card,
PINE on **28027** (`SWW_PINE_PORT`). `emu.py` finds and stops only this executable by
full path, refuses a second instance, starts hidden.

PINE has memory read/write and savestates only — no registers or breakpoints. Input,
the frame clock and previews therefore come from small patches in **test builds**
(`tools/vwf.py`), not from a debugger. Function tracing, safe-halt and hot reload are
not implemented; boot a new build instead (a dev build patches in under a second).

## Tools

| Tool | Purpose |
| --- | --- |
| `tools/dbg/setup.py [--write]` | create the portable emulator with fresh settings |
| `tools/dbg/emu.py start ISO --run` / `stop --run` / `status` | project emulator only |
| `tools/dbg/pine.py` | PINE client (memory, savestate, status) |
| `tools/dbg/control.py status / press BTN / seq "A*2 wait:30" / shot LABEL / frames N` | input + screenshots (needs the monitor) |
| `tools/dbg/boot.py [--shot L]` | skip logos/movie to the title screen |
| `tools/dbg/library.py goto / show KIND IDX [--pages N --step L] / status` | library preview (needs `--preview` build) |
| `tools/dbg/sstate.py shot/dump/diff` | offline savestate reader (EE RAM, screenshot) |
| `tools/dbg/hotpatch.py OLD_ELF NEW_ELF --run` | write a newer build's executable changes into the running game (data first, `.text` hooks last) |
| `tools/disasm.py SYMBOL|ADDR [SIZE]`, `tools/xrefs.py SYM`, `tools/deadcode.py` | static analysis with the ELF symbol table |
| `tools/build.py VER [--write] [--dev] [--preview]` | builds; `--dev` patches `work/output/dev/SWW_dev.iso` in place |

Screens: `control.py shot` saves PINE slot 9 and copies the state + its screenshot to
`work/ui/shots/<UTC>_<label>/` (never deleted). Buttons: hold 8 / release 20 pad reads
by default; the title menu drops some short pulses (see below).

## Addresses

| Address | Meaning |
| --- | --- |
| 0x15A304 | `ReadPad`: `nor v1,zero,v1; andi v1,0xFFFF` → `jal MONITOR; nor` (port 0 only, `s3` = port) |
| 0x24C8D8 / 0x24C8F8 / 0x24C918 | pad raw / trigger / repeat words (+4 per port). Repeat pulses on press, then every ~5 reads after 24 |
| 0x210060 | `MAILBOX` 'SWWM': +4 injected mask, +8 pad-read counter (frame clock), +12 last word, +16 build tag |
| 0x210080 | pad monitor stub |
| 0x210100 | VWF advance table (96 × 22px, 96 × 26px) |
| 0x2101C0 | VWF width routine (`GetRomFontDispSizeX` 0x15DF20 jumps here) |
| 0x210240 | nibble-accurate 4bpp glyph blit; 0x210340 / 0x2103C0 front-ends for `PutIdx4TextureFont26Sjis` 0x15E1F8 / `22Sjis` 0x15E108 |
| 0x210460 | `LIBBOX` 'SWWL' (preview): +4 kind, +8 index, +12 busy, +16 shown, +20 exit, +24 heartbeat |
| 0x210480 | library preview driver (title menu jump table 0x2DDCE0[0] = Story → driver) |
| 0x210060–0x21137C | patch region = unreferenced `sceMkdir`…`sceUmount` (checked with `tools/deadcode.py`) |
| 0x190B68 | `deckmItemIntroView(_, kind, index)`: 1 machine / 2 pilot, table 0x9A7 / 0x2869 |
| 0x3F8928 | `txt.0`: 64 line pointers for a library entry; each line is a 64-byte `malloc` |
| 0x161628 / 0x161AA0 | `windPutText` / `windPutTextDirect`; window +0x28 right limit, +0x40/+0x44 x/y, +0x58 font type, +0x5C font space |
| gp+0x90 | current font type: 0 = 22px, 1 = 26px, 2–6 ANK fonts |
| 0x2163F4 | pfr table (12 bytes per pfr id; +8 size) |
| 0x17FAC0 | `_exp_func`: script call arguments; string args -> `mdl_str_arg` 0x266128 (+4 each), numbers -> `mdl_arg` 0x266118 (+2 each); 0x17FB14 `jal strlen` -> `SCRIPT_STR` |
| 0x210700 / 0x210780 | `SCRIPT_STR` lookup hook / table (djb2 hash, English pointer; sorted) |
| after the table | house-button width routine (`townSelectHouseMove` 0x181214: pixel width / 11) |
| gp+0x158 / gp+0x154 | script pc / current script file base; gp = 0x2F0CF0; gp-0x35E2 = current token byte |
| 0x3F2D90 + 44*i | town house table (+0xC name, 32 bytes); 0x266158 `townName` char[32] |

## Measured layouts

| Screen | Font | Width | Notes |
| --- | --- | --- | --- |
| Library (deckmItemIntroView) | 22px, space 0 | 309 px | 12 visible lines, scrolls; ≤ 64 lines, ≤ 63 bytes per line |
| Dialogue window (Versus intro) | 26px | ~470 px (portrait at left) | to be measured from RAM like the library |

## Library preview

1. `py -3.11 tools/build.py VER --preview --dev --write` (stop the emulator first: the
   build refuses to patch an ISO the emulator holds open).
2. `py -3.11 tools/dbg/emu.py start work/output/dev/SWW_dev.iso --run`
3. `py -3.11 tools/dbg/library.py goto` — presses Start/Circle until the driver heartbeat
   runs (works from the movies, title or menu).
4. `py -3.11 tools/dbg/library.py show pilot 1 --pages 3 --step 12` — opens the entry in
   the game's own window, captures each scroll position, closes it with Circle.

The preview uses the game's own window, scrolling, colours and illustrations. It does
not exercise the in-game route into the library (deck edit / shop / level-up screens).

## Town screen route

Fresh boot of a build with the monitor: `boot.py`, then `seq "CIRCLE wait:120 START wait:120
CIRCLE wait:60 CROSS wait:60 START wait:200 START wait:150 CIRCLE wait:60 START wait:60 CROSS
wait:60"` (title menu), `CIRCLE` (Story), `DOWN CIRCLE` (From Episode 1), then about 600
Circle presses through the opening scenes: Side 1 Londenion town screen (v0.3.2 capture
`work/ui/shots/20261104T014712295375Z_t11`). Hot-patching the town hook into a v0.3.0
state of the test town tw0000 left the ship menu unresponsive (that town lacks "Go Out");
use a fresh boot to approve town changes.

## Savestates

None are kept as baselines yet; every capture folder holds its own `.p2s`. Do not load a
state from an older build to approve a newer one: the state restores the old program.

## Limits / to do

- No register access: tracing and a dialogue scene preview (guide step 7) need a
  further injected driver (event start routine + interpreter context).
- Coverage check of a built image against the original (guide step 8): to do.
