"""Build the Unity English table (Assets/Resources/Lang/en.txt) for L.T().

Keys are the exact Korean UI strings. Server-sent strings (zodiac names, skills, descriptions,
item names, curse notices) are read from the backend tables so a Korean edit there fails this
script instead of silently showing Korean in English mode. Run from backend/:
    python tools/build_lang_en.py C:/Users/good6/WarfrontMVP/Assets/Resources/Lang/en.txt
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.squad_items import CURSE_TARGET, ITEMS  # noqa: E402
from app.zodiac_rules import ZODIAC  # noqa: E402
from lang_en_ui import UI  # noqa: E402  (tools/ is on sys.path when run as a script)

NAMES = dict(rat='Rat', ox='Ox', tiger='Tiger', rabbit='Rabbit', dragon='Dragon', snake='Snake', horse='Horse',
             goat='Goat', monkey='Monkey', rooster='Rooster', dog='Dog', pig='Pig')

SERVER = {
    # basic attacks / weapon names
    '쥐 이빨': 'Rat Fang', '소 뿔': 'Ox Horn', '발톱': 'Claw', '당근 던지기': 'Carrot Toss', '용 꼬리': 'Dragon Tail',
    '뱀 꼬리': 'Snake Tail', '말 발굽': 'Hoof', '양 뿔': 'Goat Horn', '펀치': 'Punch', '달걀 던지기': 'Egg Toss',
    '뼈다귀 던지기': 'Bone Toss', '몸통 박치기': 'Body Slam', '당근': 'Carrot', '달걀': 'Egg', '개 뼈다귀': 'Dog Bone',
    '돼지꼬리': 'Pig Tail',
    # skills
    '재빠른 공격': 'Quick Strike', '무리의 습격': 'Swarm Raid', '뿔 들이받기': 'Horn Charge', '대지의 울림': 'Earthquake',
    '맹호의 발톱': 'Tiger Claw', '호랑이 포효': 'Tiger Roar', '달빛 회복': 'Moonlight Heal', '보름달 보호': 'Full Moon Ward',
    '화염 숨결': 'Fire Breath', '천룡의 분노': 'Wrath of the Sky Dragon', '독니': 'Venom Fang', '맹독 안개': 'Toxic Mist',
    '질주': 'Gallop', '기병의 돌격': 'Cavalry Charge', '바위 방패': 'Rock Shield', '초원의 축복': 'Meadow Blessing',
    '여의봉': 'Extending Staff', '회전 봉술': 'Staff Spin', '깃털 사격': 'Feather Shot', '여명의 울음': 'Dawn Crow',
    '추적의 이빨': 'Hunting Bite', '수호자의 결의': "Guardian's Resolve", '튼튼한 배짱': 'Iron Belly',
    # items
    '도끼': 'Axe', '갑옷': 'Armor', '포탈': 'Portal', '업그레이드 포탈': 'Upgraded Portal', '팽이': 'Spinning Top',
    '탱탱볼': 'Bouncy Ball', '긴 채찍': 'Long Whip', '슈퍼점프': 'Super Jump', '일반 공격 금지 저주': 'Curse: No Attacks',
    '스킬 금지 저주': 'Curse: No Skills', '필살기 금지 저주': 'Curse: No Ultimate',
}
DESC = {
    'rat': ('Dash forward quickly, damaging nearby enemies (power {q}).\nInvulnerable for {g} s afterwards.',
            'A rat swarm raids a wide area (15 cells) for heavy damage (power {e}).'),
    'ox': ('Charge horns-first, damaging nearby enemies (power {q}).\nInvulnerable for {g} s afterwards.',
           'Shake the ground: damage in a wide area (15 cells) (power {e}) and 1.2 s stun.'),
    'tiger': ('Claw a frontal cone (10 cells) for damage (power {q}).',
              'Roar: damage in a wide area (15 cells) (power {e}) and 1.2 s fear.'),
    'rabbit': ('Moonlight restores {q} HP.', 'A shield that blocks {e} damage for 6 s.'),
    'dragon': ('Breathe fire in a frontal cone (10 cells) for damage (power {q}).',
               'A meteor (radius 10 cells) strikes the aimed spot (up to 13 cells) (power {e}).'),
    'snake': ('Bite enemies nearby (10 cells) for damage (power {q}) and 4 s poison.',
              'Toxic mist in a wide area (15 cells): damage (power {e}), slow and poison.'),
    'horse': ('Move speed +45% for 4 s.',
              'Charge far forward (11 cells), then damage a wide area (15 cells) (power {e}).'),
    'goat': ('A shield that blocks {q} damage for 6 s.', 'The meadow restores {e} HP.'),
    'monkey': ('Extend the staff to hit every enemy in a line ahead (26 cells) (power {q}).',
               'Spin the staff to damage a wide area (15 cells) (power {e}).'),
    'rooster': ('Shoot feathers at every enemy in a line ahead (26 cells) (power {q}).',
                'Restore {e} HP + attack +20% for 7 s.'),
    'dog': ('Bite enemies nearby (10 cells) for damage (power {q}) and 3 s slow.',
            'A shield that blocks {e} damage for 6 s.'),
    'pig': ('Charge far forward (11 cells), damaging enemies nearby (10 cells) (power {q}).',
            'Restore {e} HP + a shield that blocks {e} damage for 6 s.'),
}
CURSE_EN = dict(curse_attack='basic attacks', curse_skill='skills', curse_ultimate='ultimates')

CLIENT = {
    # stats panel and skill tooltips (RtsStatsHud)
    '장거리': 'Ranged', '단거리': 'Melee', '공격력': 'Attack', '물리 방어력': 'Armor', '마법 방어력': 'Magic Res',
    '스피드': 'Speed', 'HP 흡수율 {0:0}%': 'Lifesteal {0:0}%', '물리 방어력 무시 {0:0}%': 'Armor pen {0:0}%',
    '마법 방어력 무시 {0:0}%': 'Magic pen {0:0}%',
    '기본 공격 · {0}\n{1} 물리 공격 (공격력 {2:0.#})': 'Basic attack · {0}\n{1} physical attack (attack {2:0.#})',
    '스킬 Q · {0}  (재사용 {1:0}초, 마법 피해)\n{2}': 'Skill Q · {0}  ({1:0} s cooldown, magic damage)\n{2}',
    '필살기 E · {0}  (재사용 22초, 마법 피해)\n{1}': 'Ultimate E · {0}  (22 s cooldown, magic damage)\n{1}',
    # gear slots (SquadGearHud)
    '{0} · {1} 전용 무기 · 공격력 증가': '{0} · {1} exclusive weapon · attack up',
    '전용 갑옷 ({0}) · 방어력 크게 증가': 'Fitted armor ({0}) · armor greatly up',
    '내 캐릭터 전용 · 효과 100%': 'Made for your character · 100% effect',
    '다른 캐릭터 전용 · 효과 절반': "Another character's gear · half effect",
    '다른 캐릭터 전용 · 일반 갑옷만큼만 막아 줌': "Another character's gear · blocks like plain armor",
    '도끼 · 사용하면 앞쪽 건물 안 테이블·의자를 한 번 내려쳐 부숩니다 (5% 전용 갑옷 · 5% 전용 무기)':
        'Axe · one chop that smashes the table or chair in front of you inside a building (5% fitted armor · 5% zodiac weapon)',
    '갑옷 · 방어력 증가': 'Armor · armor up',
    '포탈 · 다른 건물로 랜덤 이동 (이동 후 3초 무적)': 'Portal · teleport to a random other building (3 s invulnerable)',
    '업그레이드 포탈 · 우리 기지 성벽으로 이동 (3초 무적)': 'Upgraded Portal · teleport inside your base walls (3 s invulnerable)',
    '팽이 · 지정 위치를 10초간 돌며 피해': 'Spinning Top · circles the target spot for 10 s, damaging enemies',
    '탱탱볼 · 실내 전용 · 조준 방향으로 발사 · 벽에 30번 튕기면 사라짐': 'Bouncy Ball · indoors only · fires toward your aim · disappears after 30 wall bounces',
    '탱탱볼은 실내에서만 사용할 수 있습니다': 'Bouncy Ball can only be used indoors',
    '긴 채찍 · 앞쪽 돌담 건축물을 쓸어 날려버립니다': 'Long Whip · sweeps away the stone-wall blocks in front of you',
    '슈퍼점프 R · 가고 있는 방향으로 돌담·강·건물을 뛰어넘습니다 (최대 12칸, 재사용 대기 없음)': 'Super Jump R · leap over stone walls, rivers and buildings in the direction you are moving (up to 12 cells, no cooldown)',
    '슈퍼점프 · 보물상자에서 얻으면 이 칸에 고정됩니다': 'Super Jump · unlocks in this slot for good once found in a treasure chest',
    '슈퍼점프를 얻었습니다!\nE 옆 칸 또는 R 키로 사용': 'Super Jump unlocked!\nUse it from the slot next to E or with R',
    '[{0}] 또는 우클릭 장착 · ': '[{0}] or right-click to equip · ', '[{0}] 사용 · 1회용 · ': '[{0}] to use · single use · ',
    '은색 · 같은 장비 2개 · 효과 2배': 'Silver · 2 of the same gear · 2x effect',
    '금색 · 같은 장비 3개 · 효과 3배': 'Gold · 3 of the same gear · 3x effect',
    '{0}Ctrl+{1} 버리기': '{0}Ctrl+{1} to drop', '봉인': 'Sealed', '저주로 봉인됨 · {0}초 남음': 'Sealed by a curse · {0} s left',
    '저주': 'Curse',
    # battle bar, respawn, floor hints (NovemberBattleHud, SquadMapView)
    '이동': 'Move', '조작 설정': 'Controls', '항복 · 마을': 'Surrender · Town',
    '영웅 부활까지 {0:0.0}초\n마우스 · 터치로 360° 둘러보기': 'Hero respawns in {0:0.0} s\nLook around 360° with mouse or touch',
    '바깥 보기 · WASD 이동 · G 집결 · Tab: 건물 안으로': 'Outside view · WASD pan · G rally · Tab: back inside',
    '건물 내부 · Tab: 바깥 보기': 'Inside a building · Tab: outside view',
    '바깥 본진·부대가 공격받고 있습니다 (Tab)': 'Your base or army outside is under attack (Tab)',
}


def table():
    rows = dict(UI)
    rows.update(CLIENT)
    for cid, z in ZODIAC.items():
        name = NAMES[cid]
        rows[z['name']] = name
        for key in ('basic', 'q', 'e'):
            rows[z[key]] = SERVER[z[key]]
        q, e = DESC[cid]
        fill = dict(q=z['q_power'], e=z['e_power'], g=f"{z['q_guard']:g}")
        rows[z['q_desc']], rows[z['e_desc']] = q.format(**fill), e.format(**fill)
    for item in ITEMS.values():
        if 'owner' in item and item['slot'] == 'armor':
            rows[item['name']] = f"Fitted Armor ({NAMES[item['owner']]})"
        else:
            rows[item['name']] = SERVER[item['name']]
    for curse, what in CURSE_TARGET.items():
        rows[f'상대편 {what}을 1분간 금지시킵니다'] = f"Enemy {CURSE_EN[curse]} sealed for 1 minute"
        rows[f'저주에 걸렸습니다!\n1분간 {what}을 사용할 수 없습니다'] = f"You've been cursed!\nNo {CURSE_EN[curse]} for 1 minute"
    return rows


def main(out):
    esc = lambda s: s.replace('\n', '\\n')
    lines = ['# Generated by backend/tools/build_lang_en.py - Korean key<TAB>English. Edit the script, not this file.']
    lines += [f'{esc(k)}\t{esc(v)}' for k, v in table().items()]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{len(lines) - 1} lines -> {out}')


if __name__ == '__main__':
    main(sys.argv[1])
