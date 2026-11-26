"""Squad-mode weapons, armor, consumables and curses found in building chests.

Inventory is 10 numbered slots: 1 = equipped weapon, 2 = equipped armor, 3..10 = bag (anything).
Bag consumables are one use. Using a bag weapon/armor swaps it with the equipped one. With no room
the item in slot 10 is dropped to make space; Ctrl+number drops a slot on the ground, where anyone
with room can pick it up. Curses fire the moment they are picked up and hit every enemy hero.
The axe is a bag consumable: using it takes an axe out for one swing (the 'Axe' clip, AXE['swing'] seconds, hero
free to move) that smashes every manor furniture piece it reaches from first chop to last (rts_map.PROPS); each piece
drops one item: fitted armor (AXE['armor_chance']) or a zodiac weapon (AXE['weapon_chance']), any of the 12, else nothing.
"""
import math
from .rts_map import CELL, DOORS, bounds, EXTENT, INTERIORS, KEEP_FLOORS, MANOR_FLOORS, OUTDOOR, PROPS, RECTS, SOLID_PROPS, blocked, cell, is_door
from .rts_path import nearest_open
from .zodiac_rules import ZODIAC

# shortcut: armor and weapon values are placeholders ("미정" in the design), tune after playtests.
ITEMS = {
    'axe': dict(name='도끼', slot='bag'),
    'armor': dict(name='갑옷', slot='armor', armor=20.),
    'portal': dict(name='포탈', slot='bag'),
    'portal_plus': dict(name='업그레이드 포탈', slot='bag'),
    'top': dict(name='팽이', slot='bag'),
    'bouncy_ball': dict(name='탱탱볼', slot='bag'),
    'long_whip': dict(name='긴 채찍', slot='bag'),
    # Lies in the garden of a stone-wall block the long whip broke; picking it up gives the hero's own zodiac weapon.
    'coin': dict(name='동전', slot='coin'),
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
    ITEMS['fitted_armor_' + _z] = dict(name=f'전용 갑옷 ({ZODIAC[_z]["name"]})', slot='armor', armor=60., owner=_z)
# 'super_jump' is not an item: a chest unlocks the hero's own super jump slot (next to E) for good.
# 'fitted_armor' / 'zodiac_weapon' each take one pool slot, then pick one of the 12 zodiac variants at random.
CHEST_POOL = ('heal', 'speed', 'attack', 'axe', 'armor', 'fitted_armor', 'zodiac_weapon', 'portal', 'portal_plus',
              'top', 'bouncy_ball', 'long_whip', 'super_jump', 'curse_attack', 'curse_skill', 'curse_ultimate')
SLOTS = 10
BAG_SIZE = SLOTS - 2
PICKUP_RADIUS = 40.
CURSE_TIME = 60.
CURSE_TARGET = dict(curse_attack='일반공격', curse_skill='스킬', curse_ultimate='필살기')
PORTAL_GUARD = 3.
# shortcut: top/ball damage and whip reach are first guesses, tune after playtests.
TOP = dict(time=10., orbit=60., spin=3., radius=140., damage=25., every=.5, reach=650.)
BALL = dict(speed=700., radius=25., damage=20., every=.5, bounces=30)
BALL_HEADINGS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]  # rebound directions
WHIP_REACH = 350.
# reach 12 cells clears every stone wall, the river, the house and the passage (not the 20-cell manors).
SUPER_JUMP = dict(reach=600., time=.9)
# shortcut: loot odds are first guesses, tune after playtests. swing = Unity's 'Axe' clip time (ZodiacHumanoidMotion).
AXE = dict(swing=1.2, reach=90., armor_chance=.05, weapon_chance=.05)


def get_slot(hero, i):
    return hero['weapon'] if i == 0 else hero['armor'] if i == 1 else hero['_bag'][i-2]


def set_slot(hero, i, item):
    if i == 0: hero['weapon'] = item
    elif i == 1: hero['armor'] = item
    else: hero['_bag'][i-2] = item


# Identical weapons/armor stack into one slot; the suffix counts copies ('weapon_rat*4' = 4 rat teeth).
# Weapons: 3 copies make silver, 3 silvers (9) make gold. Armor: 2 copies silver, 3 gold.
MAX_TIER = 3
WEAPON_TIER_COPIES = (1, 3, 9)
# shortcut: tier bonuses are first guesses (bronze/silver/gold), tune after playtests.
WEAPON_TIER_ATTACK = (10., 30., 60.)


def base(item):
    return item.split('*')[0]


def copies(item):
    return int(item.split('*')[1]) if '*' in item else 1


def max_copies(item):
    return WEAPON_TIER_COPIES[-1] if info(item)['slot'] == 'weapon' else MAX_TIER


def tier(item):
    """1 bronze, 2 silver, 3 gold."""
    if info(item)['slot'] != 'weapon': return copies(item)
    return sum(copies(item) >= need for need in WEAPON_TIER_COPIES)


def info(item):
    return ITEMS[base(item)]


def item_name(item):
    return info(item)['name'] + ('' if copies(item) == 1 else f' x{copies(item)}')


def _slots_for(item):
    kind = info(item)['slot']
    return ([0] if kind == 'weapon' else [1] if kind == 'armor' else []) + list(range(2, SLOTS))


def _stack_slot(hero, item):
    """Slot holding the same gear that can absorb this one (equipped slots first), or None."""
    if info(item)['slot'] not in ('weapon', 'armor'): return None
    return next((i for i in range(SLOTS) if get_slot(hero, i) and base(get_slot(hero, i)) == base(item)
                 and copies(get_slot(hero, i)) + copies(item) <= max_copies(item)), None)


def has_room(hero, item):
    return (info(item)['slot'] == 'curse' or _stack_slot(hero, item) is not None
            or any(not get_slot(hero, i) for i in _slots_for(item)))


def grant(hero, item):
    """Stack onto the same gear, else its gear slot if empty, else the first empty bag slot. With no
    room slot 10 is emptied for it. Returns the displaced item ('' if none). Curses are applied by the game."""
    if info(item)['slot'] == 'curse': return ''
    i = _stack_slot(hero, item)
    if i is not None:
        set_slot(hero, i, f'{base(item)}*{copies(get_slot(hero, i)) + copies(item)}')
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
    bonus = WEAPON_TIER_ATTACK[tier(item) - 1]
    return bonus if _owned(hero, item) else bonus * .5


class RtsItems:
    """Item effects for RtsGame (needs self.rng, heroes, all_targets, damage, event, home, ground)."""

    def chest_reward(self, h):
        reward = self.rng.choice(CHEST_POOL)
        if reward == 'super_jump' and h['super_jump']: return self.chest_reward(h)  # already unlocked: roll again
        if reward == 'fitted_armor': return 'fitted_armor_' + self.rng.choice(sorted(WEAPON_NAMES))  # any of the 12, like weapons
        if reward == 'zodiac_weapon': return 'weapon_' + self.rng.choice(sorted(WEAPON_NAMES))
        return reward

    @staticmethod
    def resolve(h, item):
        """A coin turns into the picker's own zodiac weapon."""
        return 'weapon_' + h['character'] if item == 'coin' else item

    def give(self, h, item):
        """grant() and drop whatever it displaced at the hero's feet."""
        item = self.resolve(h, item)
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
            item = self.resolve(h, g['item'])
            if (g['floor'] != h['floor'] or g['_by'] == h['id'] or not has_room(h, item)
                    or math.hypot(g['x']-h['x'], g['y']-h['y']) > PICKUP_RADIUS):
                continue
            self.ground.remove(g)
            self.give(h, item)
            self.event(h, 'pickup', 60., text=item_name(item))

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
        if item == 'bouncy_ball' and h['floor'] not in INTERIORS:
            self.notify(h, '탱탱볼은 실내에서만 사용할 수 있습니다', False)
            return  # Rejected uses keep the consumable in its original bag slot.
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

    def dev_command(self, pid, action, item='', floor=OUTDOOR, x=0., y=0., level=1):
        """Developer panel: receive any item, or jump into an interior / onto open outdoor ground.
        Only reachable through the route when settings.squad_dev_tools is on."""
        h = self.heroes[pid]
        if action == 'level_up':
            self.gain_xp(h, 100 + 50 * (h['level'] - 1) - h['xp'])  # exactly the rest of this level
        elif action == 'set_level':  # preview any level look, up or down
            h.update(level=level, xp=0)
            h['max_hp'] = self.stats(h)['health']
            if h['hp'] > 0: h['hp'] = h['max_hp']
        elif action == 'give' and item == 'super_jump':
            h['super_jump'] = True
        elif action == 'give':
            if item not in ITEMS: raise ValueError('unknown_item')
            self.give(h, item)
        elif floor == OUTDOOR:
            x, y = max(35., min(EXTENT-35, x)), max(35., min(EXTENT-35, y))
            self.teleport(h, OUTDOOR, *nearest_open(OUTDOOR, x, y, False, self.opened))
        else:
            # Arrive where that building's front door drops you; a door that is off this match (2:2 manor) does not count.
            # keeps are locked until their base falls; the dev panel walks in anyway (2F: off the stairs)
            door = next((d for d in DOORS if d['to_floor'] == floor and (floor in KEEP_FLOORS or d['floor'] == OUTDOOR
                         and is_door(OUTDOOR, d['cx'], d['cy'], self.opened))), None)
            if door is None: raise ValueError('unknown_floor')
            self.teleport(h, floor, door['to_x'], door['to_y'])

    def item_portal(self, h, data):
        floors = sorted(f for f in INTERIORS if f != h['floor'] and f not in KEEP_FLOORS and (self.team_size == 1 or f not in MANOR_FLOORS))
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
        # Aimed into a wall or past a room's edge (interiors are small): spin on the nearest open floor of that level.
        cx, cy = nearest_open(h['floor'], h['x'] + ax*k, h['y'] + ay*k, False, self.opened)
        self.spawn_item(h, 'top', cx=cx, cy=cy, left=TOP['time'])

    def item_bouncy_ball(self, h, data):
        if h['floor'] not in INTERIORS: return
        ax = data.get('aim_x', h['x']) - h['x']
        ay = data.get('aim_y', h['y']) - h['y']
        norm = math.hypot(ax, ay)
        if norm < .001:
            ax, ay = h['fx'], h['fy']
            norm = math.hypot(ax, ay)
        if norm < .001: ax, ay, norm = 0., -1., 1.
        x0, y0, x1, y1 = bounds(h['floor'])
        # A safety lifetime longer than 30 full room diagonals: expire on bounce 30,
        # including in the largest manor, rather than the old fixed 12-second timer.
        lifetime = (BALL['bounces'] + 1) * math.hypot(x1-x0, y1-y0) / BALL['speed'] + 1.
        self.spawn_item(h, 'bouncy_ball', vx=ax/norm*BALL['speed'], vy=ay/norm*BALL['speed'],
                        bounces=0, left=lifetime)

    def ball_rebound(self, item, wall_x, wall_y):
        """Off a wall in a random one of the 8 directions (sides, up/down, diagonals) that leads away from it and into
        open floor, so the ball crosses the whole room instead of ping-ponging on one line."""
        away_x = -math.copysign(1, item['vx']) if wall_x else 0
        away_y = -math.copysign(1, item['vy']) if wall_y else 0
        step = CELL * .6
        options = [(dx, dy) for dx, dy in BALL_HEADINGS if dx*away_x + dy*away_y > 0
                   and not blocked(item['floor'], *cell(item['x'] + dx*step, item['y'] + dy*step), self.opened)]
        if not options:  # boxed in: plain reflection
            options = [(-item['vx'] if wall_x else item['vx'], -item['vy'] if wall_y else item['vy'])]
        dx, dy = self.rng.choice(options)
        n = math.hypot(dx, dy)
        item.update(vx=dx/n*BALL['speed'], vy=dy/n*BALL['speed'])

    def spawn_item(self, h, kind, **extra):
        self.next_id += 1
        self.items.append(dict(id=f'item-{self.next_id}', kind=kind, owner=h['id'], team=h['team'],
                               floor=h['floor'], x=h['x'], y=h['y'], _hit={}, **extra))

    def item_axe(self, h, data):
        ax, ay = data.get('aim_x', h['x'] + h['fx']) - h['x'], data.get('aim_y', h['y'] + h['fy']) - h['y']
        n = math.hypot(ax, ay)
        if n: h.update(fx=ax / n, fy=ay / n)
        h['axe_left'] = AXE['swing']  # the axe shows in hand for the swing
        self.start_action(h, 'axe', AXE['swing'])
        self.axe_swing(h)  # first chop now; rts_game.hero_tick keeps swinging while axe_left lasts

    def axe_swing(self, h):
        """Every tick of the swing (axe_left > 0): smash each unbroken piece with a cell in reach on the hero's front
        half, so anything met from the first chop to the last breaks, even while walking."""
        if h['floor'] == OUTDOOR: return
        def in_reach(p):
            for cx, cy in p['cells']:
                dx, dy = (cx+.5)*CELL - h['x'], (cy+.5)*CELL - h['y']
                if math.hypot(dx, dy) <= AXE['reach'] + CELL / 2 and dx*h['fx'] + dy*h['fy'] >= 0: return True
            return False
        for prop in PROPS:
            if prop['floor'] == h['floor'] and prop['id'] not in self.broken_props and in_reach(prop): self.smash(h, prop)

    def smash(self, h, prop):
        self.broken_props.append(prop['id'])
        if prop['kind'] not in SOLID_PROPS: self.opened.update((prop['floor'], cx, cy) for cx, cy in prop['cells'])
        roll = self.rng.random()
        if roll < AXE['armor_chance'] + AXE['weapon_chance']:
            item = ('fitted_armor_' if roll < AXE['armor_chance'] else 'weapon_') + self.rng.choice(sorted(WEAPON_NAMES))
            # Loot lies on the freed cells (a solid fireplace: the open cells around it, not the hero's own), at cell
            # centres a step from the hero, so it waits on the floor instead of being swept up by the swing.
            spots = [tuple(c) for c in prop['cells']]
            if prop['kind'] in SOLID_PROPS:
                spots = sorted({(x+a, y+b) for x, y in spots for a in (-1, 0, 1) for b in (-1, 0, 1)} - set(spots)
                               - {cell(h['x'], h['y'])})
                spots = [s for s in spots if not blocked(prop['floor'], *s, self.opened)] or [cell(h['x'], h['y'])]
            self.next_id += 1
            sx, sy = spots[0]
            self.ground.append(dict(id=f'ground-{self.next_id}', item=item, floor=prop['floor'],
                                    x=(sx+.5)*CELL, y=(sy+.5)*CELL, _by=''))

    def leap(self, h, data):
        """Super jump slot (R / next to E, unlocked from a chest, no cooldown): leap the way the hero is running (movement keys), else the way it faces, over walls, water and buildings;
        lands on the farthest open spot within reach.
        rts_game.hero_tick flies the hero along _leap while super_jump_left lasts (no input, no doors/chests)."""
        mx, my = data.get('move_x', 0), data.get('move_y', 0)
        n = math.hypot(mx, my)
        fx, fy = (mx / n, my / n) if n else (h['fx'], h['fy'])
        x0, y0, x1, y1 = bounds(h['floor'])
        tx, ty = h['x'], h['y']
        for k in range(int(SUPER_JUMP['reach'] // 10), 0, -1):
            x, y = max(x0, min(x1, h['x'] + fx*k*10)), max(y0, min(y1, h['y'] + fy*k*10))
            c = cell(x, y)
            if not blocked(h['floor'], *c, self.opened) and not is_door(h['floor'], *c, self.opened):
                tx, ty = x, y
                break
        h.update(fx=fx, fy=fy, _leap=(h['x'], h['y'], tx, ty), super_jump_left=SUPER_JUMP['time'],
                 super_jump_duration=SUPER_JUMP['time'], command='hold', _path=[])

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
                self.next_id += 1  # a coin waits in the middle of the garden the wall enclosed
                self.ground.append(dict(id=f'ground-{self.next_id}', item='coin', floor=OUTDOOR,
                                        x=(x0+x1+1)/2*CELL, y=(y0+y1+1)/2*CELL, _by=''))

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
            # Ball: sub-steps of at most 20 units; hitting a wall is one bounce.
            steps = max(1, math.ceil(BALL['speed'] * dt / 20))
            for _ in range(steps):
                nx, ny = item['x'] + item['vx']*dt/steps, item['y'] + item['vy']*dt/steps
                wall_x = blocked(item['floor'], *cell(nx, item['y']), self.opened)
                wall_y = blocked(item['floor'], *cell(item['x'], ny), self.opened)
                if not wall_x and not wall_y and blocked(item['floor'], *cell(nx, ny), self.opened):
                    wall_x = wall_y = True  # corner
                if wall_x or wall_y:
                    item['bounces'] += 1
                    if item['bounces'] >= BALL['bounces']: item['left'] = 0.; break
                    self.ball_rebound(item, wall_x, wall_y)
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
