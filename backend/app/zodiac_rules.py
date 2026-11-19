"""Match-only zodiac characters. Values are owned by the authoritative simulation.

Stats: hp, attack, armor (physical), magic_armor, speed, armor_pen / magic_pen / lifesteal (0..1).
Basic attacks deal physical damage, Q/E deal magic damage. reach: basic attack range in server units.
q_scale / e_scale multiply skill area, line length and dash distance. q_guard: seconds of invulnerability after Q.
"""


MOVE_SCALE = 1.4  # hero run speed multiplier on the table speeds below (the follow camera scrolls at this speed)
HP_SCALE = 5  # hero and minion HP multiplier on the table values (fights were ending too fast)
DAMAGE_SCALE = 2  # hero attack multiplier (basic, skills, poison); below HP_SCALE so fights last longer than before


def _hero(name, basic, reach, stats, q, e, q_kind, e_kind, q_power, e_power, q_desc, e_desc, q_scale=2., e_scale=2., q_guard=0., q_cooldown=6.):
    hp, attack, armor, magic_armor, speed, armor_pen, magic_pen, lifesteal = stats
    speed = round(speed * MOVE_SCALE)
    hp = hp * HP_SCALE
    attack = attack * DAMAGE_SCALE
    return dict(name=name, basic=basic, reach=reach, hp=hp, attack=attack, armor=armor, magic_armor=magic_armor,
                speed=speed, armor_pen=armor_pen, magic_pen=magic_pen, lifesteal=lifesteal,
                q=q, e=e, q_kind=q_kind, e_kind=e_kind, q_power=q_power, e_power=e_power,
                q_scale=q_scale, e_scale=e_scale, q_guard=q_guard, q_cooldown=q_cooldown, q_desc=q_desc, e_desc=e_desc)


LONG, SHORT = 650., 220.

ZODIAC = {
    'rat': _hero('쥐', '쥐 이빨', LONG, (140, 19, 8, 10, 265, .10, 0, 0),
                 '재빠른 공격', '무리의 습격', 'dash', 'burst', 24, 58,
                 '앞으로 재빠르게 돌진하며 주변 적에게 피해(위력 24).\n이후 5초간 무적.',
                 '주변의 넓은 범위(15칸)에 쥐 떼가 습격해 큰 피해(위력 58).',
                 q_scale=1., q_guard=5., q_cooldown=12.),
    'ox': _hero('소', '소 뿔', SHORT, (170, 20, 15, 8, 225, 0, 0, 0),
                '뿔 들이받기', '대지의 울림', 'dash', 'stun', 34, 52,
                '뿔을 앞세워 돌진하며 주변 적에게 피해(위력 34).\n이후 1.5초간 무적.',
                '땅을 울려 넓은 범위(15칸)에 피해(위력 52)와 1.2초 기절.',
                q_scale=1., q_guard=1.5),
    'tiger': _hero('호랑이', '발톱', SHORT, (170, 24, 15, 10, 250, .20, 0, .06),
                   '맹호의 발톱', '호랑이 포효', 'cone', 'fear', 42, 48,
                   '전방 부채꼴(10칸)을 발톱으로 할퀴어 피해(위력 42).',
                   '포효로 넓은 범위(15칸)에 피해(위력 48)와 1.2초 공포.'),
    'rabbit': _hero('토끼', '당근 던지기', LONG, (155, 19, 6, 20, 260, 0, .10, 0),
                    '달빛 회복', '보름달 보호', 'heal', 'shield', 150, 320,
                    '달빛으로 체력 150 회복.',
                    '6초간 피해 320을 막는 보호막.', q_scale=1., e_scale=1.),
    'dragon': _hero('용', '용 꼬리', LONG, (170, 24, 10, 18, 235, 0, .20, 0),
                    '화염 숨결', '천룡의 분노', 'cone', 'meteor', 46, 76,
                    '전방 부채꼴(10칸)에 불을 뿜어 피해(위력 46).',
                    '조준 지점(최대 13칸)에 반경 10칸 운석 낙하(위력 76).'),
    'snake': _hero('뱀', '뱀 꼬리', LONG, (170, 22, 8, 15, 250, 0, .25, .05),
                   '독니', '맹독 안개', 'poison', 'venom', 34, 55,
                   '주변(10칸) 적을 물어 피해(위력 34)와 4초 중독.',
                   '넓은 범위(15칸)에 독안개: 피해(위력 55), 둔화, 중독.'),
    'horse': _hero('말', '말 발굽', SHORT, (190, 25, 18, 12, 280, .10, 0, 0),
                   '질주', '기병의 돌격', 'speed', 'charge', 0, 64,
                   '4초간 이동 속도 45% 증가.',
                   '앞으로 길게(11칸) 돌격한 뒤 넓은 범위(15칸)에 피해(위력 64).'),
    'goat': _hero('양', '양 뿔', SHORT, (200, 17, 18, 18, 230, 0, 0, 0),
                  '바위 방패', '초원의 축복', 'shield', 'heal', 140, 220,
                  '6초간 피해 140을 막는 보호막.',
                  '초원의 기운으로 체력 220 회복.'),
    'monkey': _hero('원숭이', '펀치', SHORT, (175, 24, 14, 12, 255, .15, 0, .05),
                    '여의봉', '회전 봉술', 'line', 'spin', 36, 60,
                    '여의봉을 뻗어 전방 일직선(26칸)의 모든 적에게 피해(위력 36).',
                    '봉을 회전시켜 넓은 범위(15칸)에 피해(위력 60).'),
    'rooster': _hero('닭', '달걀 던지기', LONG, (160, 24, 8, 12, 255, .12, 0, 0),
                     '깃털 사격', '여명의 울음', 'line', 'rally', 42, 175,
                     '깃털을 쏘아 전방 일직선(26칸)의 모든 적에게 피해(위력 42).',
                     '체력 175 회복 + 7초간 공격력 20% 증가.'),
    'dog': _hero('개', '뼈다귀 던지기', LONG, (160, 18, 14, 14, 250, .08, 0, .07),
                 '추적의 이빨', '수호자의 결의', 'slow', 'guard', 32, 150,
                 '주변(10칸) 적을 물어 피해(위력 32)와 3초 둔화.',
                 '6초간 피해 150을 막는 보호막.'),
    'pig': _hero('돼지', '몸통 박치기', SHORT, (190, 18, 15, 20, 220, 0, 0, .06),
                 '몸통 박치기', '튼튼한 배짱', 'dash', 'fortify', 32, 230,
                 '앞으로 길게(11칸) 돌진하며 주변(10칸) 적에게 피해(위력 32).',
                 '체력 230 회복 + 6초간 피해 230을 막는 보호막.'),
}
