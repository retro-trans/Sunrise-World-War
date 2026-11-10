"""Library (encyclopedia) preview in a --preview build.

Boot the build, open the title menu and select Story: the debug driver loads
deckmenu.pac and waits. Then:

  py -3.11 tools/dbg/library.py goto              title screen -> menu -> Story (= preview driver)
  py -3.11 tools/dbg/library.py show pilot 1      open entry, capture every scroll position
  py -3.11 tools/dbg/library.py show machine 150 --pages 4
  py -3.11 tools/dbg/library.py status

Kinds: machine (1), pilot (2). Captures go to work/ui/shots/<UTC>_lib_<kind>_<idx>_<n>/.
The entry window scrolls one line per Down press; --step lines per capture (default 11
of the 12 visible lines). Circle closes the entry. See tools/vwf.py LIBBOX/DRIVER.
"""
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import pine, control

LIBBOX = 0x210460
MAGIC = 0x4C575753          # 'SWWL'
KINDS = dict(machine=1, pilot=2, ship=4)


def state(p):
    return dict(magic=p.read32(LIBBOX) == MAGIC, kind=p.read32(LIBBOX + 4), index=p.read32(LIBBOX + 8),
                busy=p.read32(LIBBOX + 12), shown=p.read32(LIBBOX + 16), heartbeat=p.read32(LIBBOX + 24))


def wait_busy(p, want, timeout=20):
    end = time.monotonic() + timeout
    while p.read32(LIBBOX + 12) != want:
        if time.monotonic() > end:
            raise TimeoutError(f'library preview busy != {want}')
        time.sleep(0.02)


def alive(p, frames=20):
    hb = p.read32(LIBBOX + 24)
    control.frames(p, frames)
    return p.read32(LIBBOX + 24) != hb


def goto(p, tries=12):
    """From anywhere in the boot/title flow: Start/Circle until the driver heartbeat runs."""
    for k in range(tries):
        if alive(p):
            return True
        control.press(p, 'START' if k % 2 == 0 else 'CIRCLE', 8, 70)
    if alive(p):
        return True
    raise TimeoutError('preview driver did not start')


def show(p, kind, idx, pages, step, label=None):
    if p.read32(LIBBOX + 12):
        raise RuntimeError('an entry is already open; close it with Circle first')
    p.write32(LIBBOX + 8, idx); p.write32(LIBBOX + 4, KINDS[kind])
    wait_busy(p, 1)
    control.frames(p, 130)
    shots = []
    for n in range(pages):
        shots.append(str(control.shot(p, f'lib_{label or kind}_{idx}_{n}')))
        if n + 1 < pages:
            for _ in range(step):
                control.press(p, 'DOWN', 3, 4)
            control.frames(p, 10)
    control.press(p, 'CIRCLE')
    wait_busy(p, 0)
    return shots


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['status', 'goto', 'show'])
    ap.add_argument('kind', nargs='?')
    ap.add_argument('index', nargs='?', type=int)
    ap.add_argument('--pages', type=int, default=3)
    ap.add_argument('--step', type=int, default=11)
    a = ap.parse_args()
    p = pine.connect(5)
    try:
        control.check(p)
        if a.action == 'status':
            print(json.dumps(state(p))); return
        if p.read32(LIBBOX) != MAGIC:
            raise RuntimeError('not a --preview build')
        if a.action == 'goto':
            goto(p)
            print(json.dumps(state(p)))
        else:
            for s in show(p, a.kind, a.index, a.pages, a.step):
                print(s)
    finally:
        p.close()


if __name__ == '__main__':
    main()
