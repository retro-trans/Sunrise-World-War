"""World-map briefing images (packs 3605-3629, 3764-3769): Japanese place labels.

Each label is defined once (source sprite + box in stored 320x448 pixels + English) and
found on every map by template matching (labels are pasted at the same pixels, sometimes
dimmed). `rows()` returns gfx_text rows with one `labels` entry per match.

  py -3.11 tools/map_labels.py find      report matches per map
  py -3.11 tools/map_labels.py write     replace the map rows in work/translation/gfx/gfx_text.json
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import gfx

MAPS = list(range(8996, 9021)) + list(range(9155, 9161))     # sprite ids
LABELS = [
    # (source rid, box, jp, en)
    (9001, (110, 323, 158, 349), 'アレクス港', 'Alex Port'),
    (9001, (91, 176, 171, 204), 'フィークス半島', 'Fiex Peninsula'),
    (9002, (70, 171, 115, 199), '乾燥地帯', 'Arid Zone'),
    (9002, (144, 186, 189, 213), '穀倉地帯', 'Breadbasket'),
    (9002, (189, 211, 228, 239), '寒冷地', 'Cold Zone'),
    (9005, (188, 254, 219, 276), 'モナク', 'Monak'),
    (9008, (225, 195, 295, 219), 'アスタンテ要塞', 'Astante Fortress'),
    (9009, (162, 233, 192, 254), 'モナク (left of the dot)', 'Monak'),
    (9009, (207, 220, 265, 244), 'ナルゴウ地方', 'Nargou Region'),
    (9017, (163, 133, 200, 157), 'セシル島', 'Cecil Island'),
    (9017, (213, 118, 262, 140), 'セシベル基地', 'Cecibel Base'),
    (9018, (118, 252, 170, 294), 'タルク半島 第3軍拠点', 'Taruk Peninsula\n3rd Army Base'),
    (9155, (55, 62, 134, 88), 'テラ世界全図', 'Terra Realm Map'),
    (9155, (130, 117, 165, 141), 'アジア', 'Asia'),
    (9155, (193, 135, 230, 161), 'ガイア', 'Gaia'),
    (9155, (73, 184, 132, 210), 'ペンタゴナ', 'Pentagona'),
    (9155, (96, 303, 142, 329), 'イベリア', 'Iberia'),
    (9155, (155, 288, 246, 314), 'バイストンウェル', 'Byston Well'),
    (9158, (165, 113, 205, 122), 'パラダイムシティ', 'Paradigm City'),
    (9158, (211, 114, 254, 124), 'ノースベース', 'North Base'),
    (9158, (138, 157, 176, 177), 'ホシミ（GEAR本部）', 'Hoshimi\n(GEAR HQ)'),
    (9158, (232, 148, 279, 168), 'イーストベース（レジスタンス基地）', 'East Base\n(Resistance Base)'),
    (9158, (206, 178, 240, 187), 'バザーポイント', 'Bazaar Point'),
    (9158, (160, 194, 175, 203), 'クスコ', 'Cusco'),
    (9158, (181, 208, 214, 218), 'グラドスシティ', 'Grados City'),
    (9159, (79, 96, 139, 115), 'グラドス補給路', 'Grados Supply Line'),
]
SMALL = {'パラダイムシティ', 'ノースベース', 'ホシミ（GEAR本部）', 'イーストベース（レジスタンス基地）',
         'バザーポイント', 'クスコ', 'グラドスシティ'}
PLATE = {'テラ世界全図', 'グラドス補給路'}


def _gray(rid):
    import numpy as np, cv2
    a = np.array(gfx.compose(rid)[0].convert('RGB'))
    return cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)


def matches(thresh=0.85):
    import cv2
    grays = {r: _gray(r) for r in set(MAPS) | {l[0] for l in LABELS}}
    out = {r: [] for r in MAPS}
    for src, box, jp, en in LABELS:
        x0, y0, x1, y1 = box
        t = grays[src][y0:y1, x0:x1]
        for r in MAPS:
            res = cv2.matchTemplate(grays[r], t, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if mx >= thresh:
                dx, dy = loc[0] - x0, loc[1] - y0
                out[r].append(dict(jp=jp, en=en, box=[x0 + dx, y0 + dy, x1 + dx, y1 + dy], score=round(mx, 3)))
    return out


STYLE = dict(bg='inpaint', hstretch=2, keep_palette=True, font='boldi',
             glyph_hsv=[[[0, 0, 100], [45, 160, 255]], [[150, 0, 100], [180, 160, 255]]],
             grow=4, thresh=220, stroke_w=2, squeeze=0.7, size=18)
TERRA = {'アジア', 'ガイア', 'ペンタゴナ', 'イベリア', 'バイストンウェル'}


_V = {}


def bright(rid, box):
    """True when the label is drawn at full brightness (not a greyed earlier label)."""
    import numpy as np, cv2
    if rid not in _V:
        a = np.array(gfx.compose(rid)[0].convert('RGB'))
        _V[rid] = cv2.cvtColor(a, cv2.COLOR_RGB2HSV)[..., 2]
    x0, y0, x1, y1 = box
    return float(np.percentile(_V[rid][y0:y1, x0:x1], 99.5)) >= 215


def rows():
    out = []
    for r, ls in matches().items():
        if not ls:
            continue
        labels = []
        for l in ls:
            lb = dict(box=l['box'], en=l['en'])
            if r < 9155:                      # red/green maps: also catch dimmed (greyed) labels
                lb.update(glyph_hsv=STYLE['glyph_hsv'] + [[[0, 0, 115], [25, 225, 255]], [[160, 0, 115], [180, 225, 255]]])
                if bright(r, l['box']):       # current labels: the game's cream text
                    lb.update(fill=[255, 236, 170], stroke=[45, 25, 10])
            if l['jp'] in SMALL:
                # white text on a translucent plate: inpaint only the white glyphs (the plate
                # around them is rebuilt), then plain white text
                lb.update(glyph_hsv=[[[0, 0, 105], [180, 110, 255]]], thresh=9999, grow=2, size=10, font='bold',
                          stroke_w=0, scale2=1.0, gap=0.0, fill=[240, 240, 245], stroke=[0, 0, 0], squeeze=0.6,
                          plate_tint=[18, 22, 58, 0.55])
            if l['jp'] == 'ホシミ（GEAR本部）':      # location dot left of the first line
                dx = l['box'][0] - 138
                lb.update(protect=[[142 + dx, l['box'][1] - 2, 149 + dx, l['box'][1] + 8]])
            if l['jp'] == 'アスタンテ要塞':        # dimmed copies keep dark glyph edges
                lb.update(grow=2, stroke_w=2, glyph_hsv=[[[0, 0, 115], [25, 225, 255]], [[160, 0, 115], [180, 225, 255]]])
            if l['jp'] in PLATE:
                lb.update(font='bold', size=15, fill=[230, 240, 250], stroke=[10, 30, 50],
                          glyph_hsv=[[[0, 0, 150], [180, 80, 255]]])
            if l['jp'] in TERRA:
                lb.update(font='bold', fill=[255, 230, 80], stroke=[70, 40, 0], size=19)
            if '\n' in l['en'] and l['jp'] not in SMALL:
                lb.update(size=13, gap=0.05)
            labels.append(lb)
        out.append(dict(rid=r, jp=' / '.join(l['jp'] for l in ls), en=' / '.join(l['en'].replace('\n', ' ') for l in ls),
                        labels=labels, notes='world map labels (tools/map_labels.py)', **STYLE))
    return out


if __name__ == '__main__':
    if sys.argv[1] == 'write':
        import json
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'work/translation/gfx/gfx_text.json')
        d = json.load(open(p, encoding='utf-8'))
        new = rows()
        d['rows'] = [x for x in d['rows'] if x['rid'] not in MAPS] + new
        json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(len(new), 'map rows,', sum(len(x['labels']) for x in new), 'labels')
    if sys.argv[1] == 'find':
        for r, ls in matches().items():
            print(r, [(l['en'].replace('\n', ' '), l['score']) for l in ls])
