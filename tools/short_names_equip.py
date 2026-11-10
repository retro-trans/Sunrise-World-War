"""Short names for special skills, equipment and skills (field +8, half-width kana)."""
import sys, json, re
sys.path.insert(0, r'E:\Projects\Sunrise World War\tools')
from disasm import Elf
e = Elf()
P = r'E:\Projects\Sunrise World War\work\translation\en\elf_strings.json'
d = json.load(open(P, encoding='utf-8'))
es = {int(r['va'], 16): r for r in d['rows']}
T = {'special': (0x248738, 60, 256, 14), 'dev': (0x237E20, 56, 151, 13), 'skill': (0x24C338, 16, 34, 11)}
B = {
 # special
 'ﾒﾝﾃﾅﾝｽ': 'Maintenance', 'ｽﾅｲﾊﾟｰ': 'Sniper Shot', 'ｺｳｲｷｼｴﾝ': 'Wide Support', 'ﾀﾞﾝﾏｸ': 'Barrage',
 'ﾊﾞｸｹﾞｷ': 'Bombing Sup.', 'ｱｻﾙﾄｻﾎﾟｰﾄ': 'Assault Sup.', 'ｵｳｷｭｳｼｭｳﾘ': 'E. Repair', 'ﾋﾅﾝﾕｳﾄﾞｳ': 'Evacuation',
 'Aｺﾝﾋﾞﾈｰｼｮﾝ': 'A. Combination', 'ﾒｶﾞﾋﾞｰﾑﾎｳ': 'M. Beam Cannon', 'ﾀﾀﾞﾝﾄｳﾐｻｲﾙ': 'MIRV Missile',
 'ﾂｲﾝﾊﾞｽﾀｰﾗｲﾌﾙ': 'Twin Buster R.', 'ｷｼｭｳｺｳｹﾞｷ': 'Surprise Atk.', 'ｺﾞｯﾄﾞﾌｨﾝｶﾞｰ': 'God Finger',
 'ｾｷﾊﾃﾝｷｮｳｹﾝ': 'Sekiha Tenkyo', 'ﾒｶﾞﾋﾞｰﾑﾗｲﾌﾙ': 'M. Beam Rifle', 'ﾍﾝｹｲｺｳｹﾞｷ': 'Transform Atk.',
 '100ﾚﾝｿｳﾐｻｲﾙ': '100-Tube Msl.', 'V-MAXﾚｯﾄﾞﾊﾟﾜｰ': 'V-MAX Red Pwr.', 'ﾀﾃｲﾁﾓﾝｼﾞｷﾞﾘ': 'Ichimonji Cut',
 'ｻﾝﾀﾞｰｸﾗｯｼｭ': 'Thunder Crash', 'ﾌｧｲﾅﾙｱﾀｯｸ': 'Final Attack', 'ﾗｲﾒｲｸｽﾞｼ': 'Thunder Break',
 'ﾛｹｯﾄﾊﾟﾝﾁ': 'Rocket Punch', 'ASﾐｻｲﾙ': 'AS Missile', 'ooooo': '-----', 'ﾏﾙﾁｺﾝﾃﾅ': 'Multicontainer',
 'ﾐﾘｵﾝｼｭｰﾀｰ': 'Mil. Shooter', 'ｼｮﾙﾀﾞｰｷｬﾉﾝ': 'Shldr. Cannon', 'ﾛｹｯﾄﾗﾝﾁｬｰ': 'Rocket Lnchr.',
 'ﾏｸﾞﾈｼｳﾑｱﾛｰ': 'Mag. Arrow', 'ｲﾝﾛｳ': 'Inro', 'ｼｷｺｳﾖｳ': 'Morale Boost', 'Kﾊﾞｽﾀｰﾗﾝﾁｬｰ': 'Mod. Buster L.',
 'ﾀｲｶﾝｺｳｹﾞｷ': 'AS Attack', 'Hﾀｲｶﾝﾐｻｲﾙ': 'Heavy AS Msl.', 'ﾊﾞｽﾀｰﾗﾝﾁｬｰ': 'Buster Lnchr.', 'ﾚｰﾙｷｬﾉﾝ': 'Rail Cannon',
 'ﾂｲﾝﾚｰｻﾞｰｿｰﾄﾞ': 'Twin L. Sword', 'ﾎｰﾐﾝｸﾞﾐｻｲﾙ': 'Homing Msl.', '30ﾚﾝｽﾛｳﾗﾝｻｰ': '30-Shot Lancer',
 'ﾒｶﾞﾊﾞｽﾞｰｶﾗﾝﾁｬｰ': 'M. Bazooka L.', 'ｾｲｱﾂｼｬｹﾞｷ': 'Suppress. Fire', 'ｺｳｼｬｷｶﾝﾎｳ': 'AA Autocannon',
 'ﾘｮｳﾖｳﾛｹｯﾄ': 'AA/AG Rocket', 'ｺｳｲｷｶｸｻﾝﾋﾞｰﾑ': 'Spread Beam', 'ｷｺｳﾃｲ': 'Kikoutei', 'ｷｬｸﾎﾝｸｳｶﾝ': 'Script Space',
 'ﾗｲﾄﾆﾝｸﾞﾄﾞﾘﾙ': 'Lightng. Drill', 'F･ﾌﾞﾗｯｸﾎｰﾙ': 'F. Black Hole', 'ﾌｸﾘｭｳ･ｶﾞﾘｭｳ': 'Fukuryu/Garyu',
 'ｾﾝｼﾉﾁｶﾗ': 'Warrior Power', 'ﾆﾚﾝｺﾞﾏ': 'Twin Tops', 'ﾋｬｸﾚﾂｹﾝ': '100 Rend Fists', 'J･ﾛｯｸｸﾞﾝﾀﾞﾝ': "Locke's Corps",
 'ｼｭｳﾀﾞﾝﾈﾝﾎﾟｳ': 'Group Psychic', 'ﾖｳｼﾞｬﾉﾁｶﾗ': 'Yoja Power', 'ﾗﾝｾｲｻﾞﾝ': 'Storm Star Cut', 'ｺｳｻﾗﾝﾌﾞ': 'Sand Dance',
 'ｹﾞﾝｻﾂｶｲ': 'Phantom Field', 'ｼﾞｬｶﾞｹﾝ･ｵﾛﾁ': 'Jagaken Orochi', 'ｼﾞｬｶﾞｹﾝ･ｾﾝ': 'Jagaken Flash',
 'ｱﾝｺｸﾁｮｳﾋｷﾞﾘ': 'Dark Leap Cut', 'ｼﾝｸｳﾊ': 'H. Shockwave', 'ｶﾞﾝﾃﾂｻｲ': 'H. Rock Crush', 'ﾁｮｳﾘｭｳﾊ': 'H. Wave Smash',
 'ﾗｲｺｳｻﾞﾝ': 'H. Thunder Cut', 'ｿｳｴﾝｻﾞﾝ': 'H. Twin Flame', 'ｾﾝｺｳｻﾞﾝ': 'H. Radiant Cut',
 # equipment
 'ﾅｼ': 'None', 'ﾀｲｸｳﾎｳ': 'AA Gun', 'ｼｭﾎｳ': 'Main Cannon', 'ｿｸｼｬﾎｳ': 'Rapid Gun', 'ﾀｲﾁﾐｻｲﾙ': 'AG Missile',
 'ﾀｲｸｳﾐｻｲﾙ': 'AA Missile', 'ﾀｲｶﾝﾐｻｲﾙ': 'AS Missile', 'ｳﾁｭｳﾐｻｲﾙ': 'Space Msl.', 'ﾊﾝﾖｳﾐｻｲﾙ': 'Multi Msl.',
 'ｸﾗｽﾀｰﾎﾞﾑ': 'Cluster Bmb', 'ﾒｶﾞﾘｭｳｼﾎｳ': 'Mega Ptcl.', 'Hﾒｶﾞﾘｭｳｼﾎｳ': 'H. Mega Ptcl.', 'ﾋﾞｰﾑﾎｳ': 'Beam Cannon',
 'ﾏｲｸﾛCSﾎｳ': 'Micro CS Gun', 'ﾍﾋﾞｰﾎﾞﾑ': 'Heavy Bomb', 'Mﾘｭｳｼｻﾝﾌﾟ': 'M. Dispenser', 'ENﾌﾞｰｽﾀｰ': 'EN Booster',
 'ENｼﾞｪﾈﾚｰﾀ': 'EN Gen.', 'ENﾀｰﾎﾞ': 'EN Turbo', 'ENﾀﾝｸCAR': 'Veh. EN Tank', 'ﾚｰｻﾞｰ': 'Laser',
 'ｾﾝﾀｲｼｭｳﾘ': 'Hull Repair', 'ﾏｼﾝﾘﾊﾞｰｽ': 'Mch. Revive', 'HUFﾘﾊﾞｰｽ': 'HUF Revive', 'ｱｲﾃﾑﾘﾊﾞｰｽ': 'Item Revive',
 'CAﾘﾊﾞｰｽ': 'CAR Revive', 'ｼｭｳﾘCAR': 'Veh. Repair', 'ｺｳｼｷﾞｮﾗｲ': 'Photon Trp.', 'ﾄﾞｳﾀｲｾﾝｻｰ': 'Motion Sen.',
 'ﾀｲｼﾞﾝｾﾝｻｰ': 'Pers. Sens.', 'ｶﾓﾌﾗｰｼﾞｭ': 'Camouflage', 'ｲｸｾｲｿﾌﾄ': 'Training Soft', 'ﾃﾞﾝｼﾎﾞｳﾍｷ': 'ECM Barrier',
 'ﾎﾞｳｷﾞｮｹｯｶｲ': 'Protect. Ward', 'ｶﾝｾｲｼｽﾃﾑ': 'Unit Ctrl.', 'ｼｷｼｽﾃﾑ': 'Veh. Cmd.', 'FCSｷｮｳｶ': 'FCS Up',
 'VFCSｷｮｳｶ': 'V-FCS Up', 'DFﾌｨｰﾙﾄﾞ': 'Def. Field', 'HUFｲｸｾｲｿﾌﾄ': 'HUF Training', 'ｸｳｶﾝﾜｲｷｮｸ': 'Spatial Dist.',
 'ﾒﾃｵ_ｼｭﾎｳ': 'Meteor Cannon', 'ﾌﾟﾗﾈｯﾄﾎﾞﾏｰ': 'Planet Bomber', 'ﾎﾞｳｴｲｷｮｳｼﾂ': 'Defense Class', 'Iﾍﾝｹｲｿｳﾁ': 'IG Transform',
 'Lｷｶﾝｼﾞｭｳ': 'Light MG', 'Hｷｶﾝｼﾞｭｳ': 'Heavy MG', 'ﾀｲｸｳｷｶﾝﾎｳ': 'AA Autocannon', 'ﾑﾊﾝﾄﾞｳﾎｳ': 'Recoilless',
 'ｿｳｺｳ_CAR': 'Veh. Armor', 'ATﾛｹｯﾄ': 'AT Rocket', 'ｹｲﾀｲATM': 'Portable ATM', 'ｹｲﾀｲSAM': 'Portable SAM',
 'ｼｬｹﾞｷﾕﾆｯﾄ': 'Firing Unit', 'ｿｹﾞｷﾚｰｻﾞｰ': 'Snipe Laser', 'ｿｳｺｳ': 'Armor', 'M2ｷｶﾝｼﾞｭｳ': 'M2 HMG',
 '35mmGUN': '35mm Gun', 'ｵｰﾗﾉﾊﾞﾎｳ': 'Aura Nova Gun', 'ﾎﾟﾀﾝﾎｳ': 'Potan Cannon', 'ENｼｮｸ': 'EN Ration',
 'ENﾌﾞｰｽﾀｰC': 'V. EN Boost', 'ATｼｴﾝｷ': 'Spotter Plane', 'SPｼｴﾝｷ': 'Liaison Plane', 'HPｼｴﾝｷ': 'AEW Aircraft',
 'ｽﾀﾐﾅ': 'Stamina Drink', 'ATｼｴﾝｷ_H': 'Fast Spotter', 'SPｼｴﾝｷ_H': 'Fast Liaison', 'HPｼｴﾝｷ_H': 'Fast AEW',
 'ｶｸｾｲｷ_H': 'HP Megaphone', 'ｽﾀﾐﾅ_S': 'Sp. Stamina', 'ﾘﾍﾟｱｷｯﾄ_H': 'Adv. Med Kit',
 # skills
 'ｾﾝｾｲ': '1st Strike', 'ｾﾂﾔｸ': 'EN Saver', 'ｷﾞｬｸｾﾝｾｲ': 'Counter 1st',
}
def s(p):
    return e.cstr(p) if 0x2b8000 < p < 0x2f0c00 else None
done = {}; bad = []; used = set()
for t, (b, st, cnt, lim) in T.items():
    for i in range(cnt):
        p0, p4, p8 = [e.u32(b + st * i + o) for o in (0, 4, 8)]
        sh = s(p8)
        if not sh or p8 in done or (es.get(p8) or {}).get('en'):
            continue
        full = (es.get(p4) or {}).get('en') or (es.get(p0) or {}).get('en') or ''
        m = re.fullmatch(r'(.+?)_(\d)', sh)
        base, lv = (m.group(1), m.group(2)) if m and m.group(1) in B else (sh, None)
        if base in B:
            used.add(base)
            en = B[base]
            if lv:
                en = en + ' Lv' + lv if len(en) + 4 <= lim else en + ' ' + lv
        elif full and len(full) <= lim:
            en = full
        else:
            bad.append((t, hex(p8), sh, full)); continue
        if len(en) > lim:
            bad.append((t, hex(p8), sh, en, 'too long')); continue
        done[p8] = (t, sh, en)
print('filled', len(done), 'bad', bad, 'unused bases', [k for k in B if k not in used])
for p8, (t, sh, en) in done.items():
    r = es.get(p8)
    if r is None:
        r = dict(va=hex(p8), jp=sh, en='', group=f'names:{t}+8', status='draft', skip=False, notes='')
        d['rows'].append(r); es[p8] = r
    r['en'] = en; r['notes'] = '[v0.3.11] short name (list cells: special 14, equipment 13, skill 11)'
if '--write' in sys.argv:
    json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('WRITTEN')
for p8, (t, sh, en) in list(done.items())[:12]:
    print(t, sh, '->', en)
