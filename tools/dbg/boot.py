"""Boot helper: wait for the monitor, skip the opening movies, stop at the title
('Press START'). Uses Circle then Start, as the logo/movie sequence needs both.

  py -3.11 tools/dbg/boot.py [--shot LABEL]
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pine, control


def boot(p):
    control.check(p)
    control.frames(p, 200, 90)
    control.press(p, 'CIRCLE', 8, 60)
    control.press(p, 'START', 8, 90)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--shot')
    a = ap.parse_args()
    p = pine.connect(60)
    try:
        boot(p)
        if a.shot:
            print(control.shot(p, a.shot))
    finally:
        p.close()
