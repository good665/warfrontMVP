"""Squad-mode weapons, armor, consumables and curses found in building chests.

Inventory is 10 numbered slots: 1 = equipped weapon, 2 = equipped armor, 3..10 = bag (anything).
Bag consumables are one use. Using a bag weapon/armor swaps it with the equipped one. With no room
the item in slot 10 is dropped to make space; Ctrl+number drops a slot on the ground, where anyone
with room can pick it up. Curses fire the moment they are picked up and hit every enemy hero.
The axe's wall breaking is still a later phase.
"""
import math
from .rts_map import CELL, DOORS, EXTENT, INTERIORS, OUTDOOR, RECTS, blocked, cell
from .rts_path import nearest_open
from .zodiac_rules import ZODIAC

# shortcut: armor and weapon values are placeholders ("미정" in the design), tune after playtests.
ITEMS = {
    # Between a zodiac weapon on its own character (+10) and on someone else (+5).
    'axe': dict(name='도끼', slot='weapon', attack=7.),
    'armor': dict(name='갑옷', slot='armor', armor=20.),
    'portal': dict(name='포탈', slot='bag'),
    'portal_plus': dict(name='업그레이드 포탈', slot='bag'),
    'top': dict(name='팽이', slot='bag'),
    'bouncy_ball': dict(name='탱탱볼', slot='bag'),
    'long_whip': dict(name='긴 채찍', slot='bag'),
    'curse_attack': dict(name='일반 공격 금지 저주', slot='curse'),
    'curse_skill': dict(name='스킬 금지 저주', slot='curse'),
    'curse_ultimate': dict(name='필살기 금지 저주', slot='curse'),
}
# Zodiac-exclusive gear: full effect on its own character, half (weapon) / plain armor on anyone else.
WEAPON_NAMES = dict(rat='쥐 이빨', ox='소 뿔', tiger='발톱', rabbit='당근', dragon='용 꼬리', snake='뱀 꼬리',
                    horse='말 발굽', goat='양 뿔', monkey='펀치', rooster='달걀', dog='개 뼈다귀', pig='돼지꼬리')
WEAPON_ATTACK = 10.
for _z, _name in WEAPON_NAMES.items():
    ITEMS['weapon_' + _z] = dict(name=_name, slot='weapon', attack=WEAPON_ATTACK, owner=_z)
    # Fitted armor is cut for whoever opened the chest.
    ITEMS['fitted_armor_' + _z] = dict(name=f'전용 갑옷 ({ZODIAC[_z]["name"]})', slot='armor', armor=60., owner=_z)
# 'fitted_armor' / 'zodiac_weapon' resolve per opener so the 12 variants do not flood the odds.
CHEST_POOL = ('heal', 'speed', 'attack', 'axe', 'armor', 'fitted_armor', 'zodiac_weapon', 'portal', 'portal_plus',
              'top', 'bouncy_ball', 'long_whip', 'curse_attack', 'curse_skill', 'curse_ultimate')
SLOTS = 10
BAG_SIZE = SLOTS - 2
PICKUP_RADIUS = 40.
CURSE_TIME = 60.
CURSE_TARGET = dict(curse_attack='일반공격', curse_skill='스킬', curse_ultimate='필살기')
PORTAL_GUARD = 3.
# shortcut: top/ball damage and whip reach are first guesses, tune after playtests.
TOP = dict(time=10., orbit=60., spin=3., radius=70., damage=15., every=.5, reach=650.)
BALL = dict(speed=700., radius=25., damage=20., every=.5, bounces=10, life=12.)
WHIP_REACH = 350.


def get_slot(hero, i):
    return hero['weapon'] if i == 0 else hero['armor'] if i == 1 else hero['_bag'][i-2]


def set_slot(hero, i, item):
    if i == 0: hero['weapon'] = item
    elif i == 1: hero['armor'] = item
    else: hero['_bag'][i-2] = item


# Identical weapons/armor stack into one slot: 'weapon_rat*2' is silver (x2), '*3' gold (x3).
MAX_TIER = 3


def base(item):
    return item.split('*')[0]


def tier(item):
    return int(item.split('*')[1]) if '*' in item else 1


def info(item):
    return ITEMS[base(item)]


def item_name(item):
    return info(item)['name'] + ('' if tier(item) == 1 else f' x{tier(item)}')


def _slots_for(item):
    kind = info(item)['slot']
    return ([0] if kind == 'weapon' else [1] if kind == 'armor' else []) + list(range(2, SLOTS))


def _stack_slot(hero, item):
    """Slot holding the same gear that can absorb this one (equipped slots first), or None."""
    if info(item)['slot'] not in ('weapon', 'armor'): return None
    return next((i for i in range(SLOTS) if get_slot(hero, i) and base(get_slot(hero, i)) == base(item)
                 and tier(get_slot(hero, i)) + tier(item) <= MAX_TIER), None)


def has_room(hero, item):
    return (info(item)['slot'] == 'curse' or _stack_slot(hero, item) is not None
            or any(not get_slot(hero, i) for i in _slots_for(item)))


def grant(hero, item):
    """Stack onto the same gear, else its gear slot if empty, else the first empty bag slot. With no
    room slot 10 is emptied for it. Returns the displaced item ('' if none). Curses are applied by the game."""
    if info(item)['slot'] == 'curse': return ''
    i = _stack_slot(hero, item)
    if i is not None:
        set_slot(hero, i, f'{base(item)}*{tier(get_slot(hero, i)) + tier(item)}')
        return ''
    for i in _slots_for(item):
        if not get_slot(hero, i):
            set_slot(hero, i, item)
            return ''
    old, hero['_bag'][-1] = hero['_bag'][-1], item
    return old


def _owned(hero, item):
    owner = ITEMS.get(base(item), {}).get('owner')
    return owner is None or owner == hero['character']


def armor_bonus(hero):
    item = hero.get('armor', '')
    if not item: return 0.
    if not _owned(hero, item):
        return ITEMS['armor']['armor'] * tier(item)  # wrong character still wears it as plain armor
    return info(item).get('armor', 0.) * tier(item)


def weapon_bonus(hero):
    item = hero.get('weapon', '')
    if not item: return 0.
    bonus = info(item).get('attack', 0.) * tier(item)
    return bonus if _owned(hero, item) else bonus * .5


class RtsItems:
    """Item effects for RtsGame (needs self.rng, heroes, all_targets, damage, event, home, ground)."""

    def chest_reward(self, h):
        reward = self.rng.choice(CHEST_POOL)
        if reward == 'fitted_armor': return 'fitted_armor_' + h['character']
        if reward == 'zodiac_weapon': return 'weapon_' + self.rng.choice(sorted(WEAPON_NAMES))
        return reward

    def give(self, h, item):
        """grant() and drop whatever it displaced at the hero's feet."""
        old = grant(h, item)
        if old: self.place(h, old)
        if info(item)['slot'] == 'curse': self.curse(h, item)

    def place(self, h, item):
        self.next_id += 1
        # _by: the dropper cannot re-pick it until they have walked away once.
        self.ground.append(dict(id=f'ground-{self.next_id}', item=item, floor=h['floor'], x=h['x'], y=h['y'], _by=h['id']))

    def drop_slot(self, h, slot):
        if not 0 <= slot < SLOTS or not get_slot(h, slot): return
        self.place(h, get_slot(h, slot))
        set_slot(h, slot, '')

    def pickup(self, h):
        for g in list(self.ground):
            if (g['floor'] != h['floor'] or g['_by'] == h['id'] or not has_room(h, g['item'])
                    or math.hypot(g['x']-h['x'], g['y']-h['y']) > PICKUP_RADIUS):
                continue
            self.ground.remove(g)
            self.give(h, g['item'])
            self.event(h, 'pickup', 60., text=item_name(g['item']))

    def ground_tick(self):
        for g in self.ground:
            by = self.heroes.get(g['_by'])
            if by and (by['floor'] != g['floor'] or math.hypot(by['x']-g['x'], by['y']-g['y']) > PICKUP_RADIUS * 2):
                g['_by'] = ''

    def ground_public(self, floor):
        return [dict(id=g['id'], item=g['item'], name=item_name(g['item']), floor=floor, x=g['x'], y=g['y'])
                for g in self.ground if g['floor'] == floor]

    def curse(self, h, item):
        what = CURSE_TARGET[item]
        self.notify(h, f'상대편 {what}을 1분간 금지시킵니다', False)
        for enemy in self.heroes.values():
            if enemy['team'] != h['team']:
                enemy[item + '_left'] = CURSE_TIME
                self.notify(enemy, f'저주에 걸렸습니다!\n1분간 {what}을 사용할 수 없습니다', True)

    @staticmethod
    def notify(h, text, alert):
        """One-shot message in the owner's battle snapshot; the client shows each notice_id once."""
        h.update(_notice=text, _notice_alert=alert, _notice_id=h.get('_notice_id', 0) + 1)

    def use_item(self, h, data):
        """Bag slot (3..10): consumables fire once; weapon/armor swap with the equipped one."""
        slot = data.get('item', -1)
        if not 2 <= slot < SLOTS or not get_slot(h, slot): return
        item = get_slot(h, slot)
        kind = info(item)['slot']
        if kind in ('weapon', 'armor'):
            gear = 0 if kind == 'weapon' else 1
            set_slot(h, slot, get_slot(h, gear))
            set_slot(h, gear, item)
            return
        set_slot(h, slot, '')
        getattr(self, 'item_' + item)(h, data)
        self.event(h, item, WHIP_REACH if item == 'long_whip' else 80., text=ITEMS[item]['name'])  # kind = item id for client visuals

    def teleport(self, h, floor, x, y):
        h.update(floor=floor, x=x, y=y, protected=max(h['protected'], PORTAL_GUARD), door_cooldown=1.,
                 command='hold', order_x=x, order_y=y, _path=[])

    def item_portal(self, h, data):
        floors = sorted(f for f in INTERIORS if f != h['floor'])
        floor = self.rng.choice(floors)
        door = next(d for d in DOORS if d['to_floor'] == floor)
        self.teleport(h, floor, door['to_x'], door['to_y'])

    def item_portal_plus(self, h, data):
        home = self.home(h['id'])
        # Same spot the hero starts on: inside the home walls, toward the board centre.
        x = home['x'] + (180 if home['x'] < EXTENT/2 else -180)
        y = home['y'] + (180 if home['y'] < EXTENT/2 else -180)
        self.teleport(h, OUTDOOR, *nearest_open(OUTDOOR, x, y, True, self.opened))

    def item_top(self, h, data):
        ax, ay = data.get('aim_x', h['x']) - h['x'], data.get('aim_y', h['y']) - h['y']
        n = math.hypot(ax, ay)
        k = min(1., TOP['reach'] / n) if n else 0.
        self.spawn_item(h, 'top', cx=h['x'] + ax*k, cy=h['y'] + ay*k, left=TOP['time'])

    def item_bouncy_ball(self, h, data):
        self.spawn_item(h, 'bouncy_ball', vx=h['fx']*BALL['speed'], vy=h['fy']*BALL['speed'],
                        bounces=0, left=BALL['life'])

    def spawn_item(self, h, kind, **extra):
        self.next_id += 1
        self.items.append(dict(id=f'item-{self.next_id}', kind=kind, owner=h['id'], team=h['team'],
                               floor=h['floor'], x=h['x'], y=h['y'], _hit={}, **extra))

    def item_long_whip(self, h, data):
        """Sweeps away the small stone-wall blocks ('wall' rects) in front of the hero."""
        if h['floor'] != OUTDOOR: return
        for i, (kind, x0, y0, x1, y1, _) in enumerate(RECTS):
            if kind != 'wall' or i in self.broken_walls: continue
            px = max(x0*CELL, min((x1+1)*CELL, h['x'])) - h['x']
            py = max(y0*CELL, min((y1+1)*CELL, h['y'])) - h['y']
            d = math.hypot(px, py)
            if d <= WHIP_REACH and px*h['fx'] + py*h['fy'] >= d*.3:
                self.broken_walls.append(i)
                self.opened.update((x, y) for x in range(x0, x1+1) for y in range(y0, y1+1))

    def items_tick(self, dt):
        for item in self.items:
            item['left'] -= dt
            owner = self.heroes[item['owner']]
            if item['kind'] == 'top':
                age = TOP['time'] - item['left']
                item.update(x=item['cx'] + TOP['orbit']*math.cos(age*TOP['spin']),
                            y=item['cy'] + TOP['orbit']*math.sin(age*TOP['spin']))
                self.item_hits(item, owner, TOP)
                continue
            # Ball: sub-steps of at most 20 units; a blocked axis flips its velocity (one bounce).
            steps = max(1, math.ceil(BALL['speed'] * dt / 20))
            for _ in range(steps):
                nx, ny = item['x'] + item['vx']*dt/steps, item['y'] + item['vy']*dt/steps
                wall_x = blocked(item['floor'], *cell(nx, item['y']), self.opened)
                wall_y = blocked(item['floor'], *cell(item['x'], ny), self.opened)
                if wall_x: item['vx'] = -item['vx']
                if wall_y: item['vy'] = -item['vy']
                if not wall_x and not wall_y and blocked(item['floor'], *cell(nx, ny), self.opened):
                    item['vx'], item['vy'] = -item['vx'], -item['vy']  # corner
                    wall_x = True
                if wall_x or wall_y:
                    item['bounces'] += 1
                    if item['bounces'] >= BALL['bounces']: item['left'] = 0.; break
                else:
                    item['x'], item['y'] = nx, ny
            self.item_hits(item, owner, BALL)
        self.items = [i for i in self.items if i['left'] > 0]

    def item_hits(self, item, owner, rules):
        for target in self.all_targets():
            if (target['team'] == item['team'] or target['floor'] != item['floor'] or target['hp'] <= 0
                    or item['_hit'].get(target['id'], -1.) > self.elapsed):
                continue
            if math.hypot(target['x']-item['x'], target['y']-item['y']) <= rules['radius'] + target['body_radius']:
                item['_hit'][target['id']] = self.elapsed + rules['every']
                # Proxy source: the owner may have changed floors; no lifesteal from items.
                self.damage(target, rules['damage'], dict(owner, floor=item['floor'], hp=0.), 'magic')

    def items_public(self, floor):
        return [{k: v for k, v in i.items() if not k.startswith('_')} for i in self.items if i['floor'] == floor]
