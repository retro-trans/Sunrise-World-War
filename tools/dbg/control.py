"""Game-guarded control through PINE (port SWW_PINE_PORT, default 28027).

  py -3.11 tools/dbg/control.py status
  py -3.11 tools/dbg/control.py press CIRCLE [--hold 4] --run
  py -3.11 tools/dbg/control.py seq "CIRCLE*3 DOWN CIRCLE" --run   (button*count, wait:N frames)
  py -3.11 tools/dbg/control.py shot LABEL --run
  py -3.11 tools/dbg/control.py frames N

Requires a project build with the pad monitor (tools/vwf.py MAILBOX 'SWWM' at 0x210060).
Input is cleared in a finally block. Screenshots come from PINE savestates (slot 9),
saved with the state under work/ui/shots/<UTC>_<label>/; old runs are never deleted.
"""
import argparse, json, os, shutil, sys, time, zipfile
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(__file__))
import pine
from sstate import State

ROOT = Path(__file__).resolve().parents[2]
SERIAL = 'SLPS-25270'
BASE = 0x210060
MAGIC = 0x4D575753            # 'SWWM'
BUTTONS = dict(L2=1, R2=2, L1=4, R1=8, TRIANGLE=16, CIRCLE=32, CROSS=64, SQUARE=128,
               SELECT=256, L3=512, R3=1024, START=2048, UP=4096, RIGHT=8192, DOWN=16384, LEFT=32768)


def check(p):
    gid = p.game_id()
    if gid != SERIAL:
        raise RuntimeError(f'unexpected game serial {gid!r}')
    if p.read32(BASE) != MAGIC:
        raise RuntimeError('monitor absent: boot a project test ISO built with the monitor')


def frames(p, n, timeout=20):
    start = p.read32(BASE + 8); end = time.monotonic() + timeout
    while True:
        el = (p.read32(BASE + 8) - start) & 0xFFFFFFFF
        if el > 0x7FFFFFFF:
            raise RuntimeError('frame counter reset (state load?)')
        if el >= n:
            return
        if time.monotonic() > end:
            raise TimeoutError('pad-read counter stopped')
        time.sleep(0.005)


def press(p, button, hold=8, release=20):
    mask = 0
    for b in button.upper().split('+'):
        mask |= BUTTONS[b]
    try:
        p.write32(BASE + 4, mask); frames(p, hold)
    finally:
        p.write32(BASE + 4, 0)
    frames(p, release)


def seq(p, spec, hold=8, release=20):
    for tok in spec.split():
        if tok.lower().startswith('wait:'):
            frames(p, int(tok[5:])); continue
        b, _, n = tok.partition('*')
        for _ in range(int(n or 1)):
            press(p, b, hold, release)


def shot(p, label, slot=9):
    states = ROOT / 'work/emulator/pcsx2/sstates'
    states.mkdir(parents=True, exist_ok=True)
    before = {f: (f.stat().st_mtime_ns, f.stat().st_size) for f in states.glob(f'*.{slot:02d}.p2s')}
    p.save_state(slot)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        for f in states.glob(f'{SERIAL}*.{slot:02d}.p2s'):
            if before.get(f) != (f.stat().st_mtime_ns, f.stat().st_size):
                try:
                    time.sleep(0.3)
                    png = State(f).screenshot()
                    run = ROOT / 'work/ui/shots' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '_' + label)
                    run.mkdir(parents=True)
                    shutil.copy2(f, run / (label + '.p2s')); (run / 'screen.png').write_bytes(png)
                    return run / 'screen.png'
                except (OSError, ValueError, KeyError, zipfile.BadZipFile, EOFError):
                    pass
        time.sleep(0.2)
    raise TimeoutError('savestate screenshot unavailable')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['status', 'press', 'seq', 'shot', 'frames'])
    ap.add_argument('arg', nargs='?')
    ap.add_argument("--hold", type=int, default=8)
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args()
    if a.action in ('press', 'seq', 'shot') and not a.run:
        print('DRY RUN:', a.action, a.arg, '- add --run'); return
    p = pine.connect(retries=5)
    try:
        if a.action == 'status':
            st = dict(status=p.status(), serial=p.game_id())
            try:
                st['monitor'] = p.read32(BASE) == MAGIC
                st['frames'] = p.read32(BASE + 8); st['buttons'] = hex(p.read32(BASE + 12))
                st['build'] = p.read(BASE + 16, 16).rstrip(b'\0').decode('ascii', 'replace')
            except Exception as e:
                st['error'] = str(e)
            print(json.dumps(st)); return
        check(p)
        if a.action == 'press':
            press(p, a.arg, a.hold)
        elif a.action == 'seq':
            seq(p, a.arg, a.hold)
        elif a.action == 'frames':
            frames(p, int(a.arg)); print(p.read32(BASE + 8))
        else:
            print(shot(p, a.arg))
    finally:
        p.close()


if __name__ == '__main__':
    main()
