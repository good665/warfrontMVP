"""Actor state, damage and zodiac abilities shared by the RTS simulation."""
import math
from .zodiac_rules import ZODIAC, DAMAGE_SCALE
from .squad_items import armor_bonus, weapon_bonus, get_slot, set_slot, base, copies, tier
from .rts_vehicles import RIDE_SPEED
from .rts_map import bounds

STAT_KEYS = ('hp', 'attack', 'armor', 'magic_armor', 'speed', 'armor_pen', 'magic_pen', 'lifesteal')
COMBAT_RULES = dict(attack_reach=145., heavy_reach=210., attack_dot=.35)
# Unity plays the tiger's Mixamo clips at 2x (2.4s slash Q, 5.4s roar E); the hero stays put and holds fire meanwhile.
TIGER_CAST_SECONDS = dict(skill1=1.2, skill2=2.7)
KNOCKBACK = 10.  # world units a hero is pushed away from whoever hit them
# Hero levels 1-10 earned in the match. shortcut: XP and per-level growth are first guesses, tune after playtests.
MAX_LEVEL = 10
XP = dict(hero=100, assist=50, unit=15, nearby=7)
ASSIST_SECONDS, NEARBY_XP = 10., 600.
# A hero with 2+ hero kills in one life carries a bounty: the enemy hero who ends it gets 50 XP per kill and knocks one gear piece loose.
BOUNTY_STREAK, BOUNTY_XP = 2, 50
LEVEL_HP, LEVEL_ATTACK = .06, .05  # per level above 1


def xp_next(level):
    return 100 + 50 * (level - 1)


def bounty_gear_slot(hero):
    """The equipped slot a claimed bounty drops: higher tier of weapon (0) / armor (1), weapon on a tie, None if bare."""
    worn = [i for i in (0, 1) if get_slot(hero, i)]
    return max(worn, key=lambda i: (tier(get_slot(hero, i)), -i), default=None)


def distance(a, b):
    return math.hypot(a['x'] - b['x'], a['y'] - b['y'])


class RtsCombat:
    @staticmethod
    def actor(uid, kind, team, x, y, hp, floor=1):
        a = dict(id=uid, kind=kind, team=team, x=x, y=y, hp=float(hp), max_hp=float(hp), fx=1.-2*team, fy=0., attack_cooldown=0., dodge_cooldown=0., skill1_cooldown=0., skill2_cooldown=0., dodge_left=0., dodge_dx=0., dodge_dy=0., hit_flash=0., respawn_left=0., charge_active=False, charge_time=0., charge_ratio=0., protected=0., body_radius=dict(hero=22., guard=22., archer=20., healer=20., base=75., bell=40.)[kind], action_id=0, action_target='', action_kind='', action_left=0., action_duration=0., action_fx=1.-2*team, action_fy=0., attack_phase='idle', _action_hits=set())
        a.update(floor=floor, hit_kind='', hit_by='', jump_left=0., jump_cooldown=0., slow_left=0., stun_left=0., poison_left=0., poison_damage=0., poison_owner='', owner_id='', shield=0., shield_left=0., cast_left=0.)
        return a

    @staticmethod
    def start_action(hero, kind, duration):
        hero.update(action_id=hero['action_id']+1, action_kind=kind,
                    action_left=duration, action_duration=duration,
                    action_fx=hero['fx'], action_fy=hero['fy'], action_target='', _action_hits=set())

    def stats(self, h):
        rules = ZODIAC[h['character']]
        result = {k: float(rules[k]) for k in STAT_KEYS}
        result.update(health=result['hp'], cooldown=0.)
        result['attack'] += weapon_bonus(h)
        grow = h.get('level', 1) - 1
        result['attack'] *= 1 + LEVEL_ATTACK * grow
        result['hp'] = result['health'] = result['hp'] * (1 + LEVEL_HP * grow)
        if h['speed_left'] > 0: result['speed'] *= 1.45
        if h.get('vehicle'): result['speed'] *= RIDE_SPEED[h['vehicle']]
        if h['rally_left'] > 0: result['attack'] *= 1.2
        if h.get('attack_left', 0) > 0: result['attack'] *= 1.3
        result['armor'] += armor_bonus(h)
        return result

    def choose_character(self, h, character):
        if character in ZODIAC and not h['character_locked'] and character != h['character']:
            h['character'] = character
            h['max_hp'] = self.stats(h)['health']
            h['hp'] = h['max_hp']  # unlocked means the hero has not fought yet

    def input(self, pid, data):
        h = self.heroes[pid]
        seq = data.get('sequence', -1)
        if self.reason or seq <= h['sequence']:
            return
        h.update(sequence=seq, input=dict(data), input_at=self.elapsed)
        self.choose_character(h, data.get('character', ''))
        for action in ('skill1', 'skill2', 'dodge', 'jump'):
            if data.get(action) and h['hp'] > 0:
                h['_pending_actions'].setdefault(action, dict(data=dict(data), expires=self.elapsed + .65))


    def damage(self, target, amount, source=None, kind='physical'):
        if (target['hp'] <= 0 or target['protected'] > 0 or target['dodge_left'] > 0
                or source is not None and (source['floor'] != target['floor'] or source['team'] == target['team'])):
            return 0.
        if target['kind'] == 'hero' and self.vehicle_hit(target, kind): return 0.
        hero_source = source is not None and source['kind'] == 'hero'
        if target['kind'] == 'hero' and kind != 'true':
            magic = kind == 'magic'
            armor = self.stats(target)['magic_armor' if magic else 'armor']
            if hero_source: armor *= 1. - self.stats(source)['magic_pen' if magic else 'armor_pen']
            amount *= 100. / (100. + armor)
        blocked = min(target.get('shield', 0), amount)
        target['shield'] -= blocked
        amount = min(target['hp'], max(0., amount - blocked))
        target['hp'] -= amount
        # Unity picks the hit-stop length from hit_kind and times it to hit_by's weapon contact frame.
        target.update(hit_flash=.16, hit_kind=kind, hit_by=source['id'] if source is not None else '')
        # 'true' is poison ticking every frame: it must not push the hero along.
        if target['kind'] == 'hero' and source is not None and amount > 0 and kind != 'true': self.knockback(target, source)
        if hero_source and amount > 0: target.setdefault('_hurt_by', {})[source['id']] = self.elapsed
        if hero_source and source['hp'] > 0 and kind != 'true':
            source['hp'] = min(source['max_hp'], source['hp'] + amount * self.stats(source)['lifesteal'])
        if target['hp'] <= 0:
            target.update(action_left=0., attack_phase='idle')
            if target['kind'] == 'hero':
                target.update(respawn_left=8., shield=0.)
                target['_pending_actions'].clear()
            self.award_kill(target, source)
        return amount

    def award_kill(self, target, source):
        hurt = target.pop('_hurt_by', {})
        if target['kind'] == 'base': return
        # source can be a proxy copy (items), so look the hero up by id
        killer = self.heroes.get(source['id']) if source is not None else None
        if target['kind'] == 'hero':
            streak, target['streak'] = target['streak'], 0
            if killer:
                claim = self.claim_bounty(target, killer, streak) if streak >= BOUNTY_STREAK else ''
                self.gain_xp(killer, XP['hero'])
                if killer['hp'] > 0: killer['streak'] += 1  # poison or a thrown item can land after the killer died
                if killer['streak'] >= BOUNTY_STREAK: self.announce_bounty(killer, claim)
                elif claim:
                    for h in self.heroes.values(): self.notify(h, claim, False)
            for pid, at in hurt.items():
                h = self.heroes.get(pid)
                if h and h is not killer and h['team'] != target['team'] and self.elapsed - at <= ASSIST_SECONDS:
                    self.gain_xp(h, XP['assist'])
            return
        if not killer: return
        self.gain_xp(killer, XP['unit'])
        for h in self.heroes.values():
            if (h is not killer and h['team'] == killer['team'] and h['hp'] > 0 and h['floor'] == target['floor']
                    and distance(h, target) <= NEARBY_XP):
                self.gain_xp(h, XP['nearby'])

    def announce_bounty(self, h, claim=''):
        # One notice slot per hero: a claim made by the same kill rides in front so it is not overwritten.
        name, lead = ZODIAC[h['character']]['name'], claim + ' · ' if claim else ''
        for other in self.heroes.values():
            self.notify(other, lead + (f'{name}에게 현상금이 걸렸습니다' if other['team'] == h['team'] else f'적 {name}에게 현상금! 처치하면 장비를 떨굽니다'), False)

    def claim_bounty(self, target, killer, streak):
        self.gain_xp(killer, BOUNTY_XP * streak)
        slot = bounty_gear_slot(target)
        if slot is not None:
            item = get_slot(target, slot)
            self.place(target, base(item))
            left = copies(item) - 1
            set_slot(target, slot, '' if left == 0 else base(item) if left == 1 else f'{base(item)}*{left}')
        return f"{ZODIAC[target['character']]['name']}의 현상금을 {ZODIAC[killer['character']]['name']}이(가) 차지했습니다"

    def gain_xp(self, h, amount):
        if h['level'] >= MAX_LEVEL: return
        h['xp'] += amount
        while h['level'] < MAX_LEVEL and h['xp'] >= xp_next(h['level']):
            h['xp'] -= xp_next(h['level'])
            old = h['max_hp']
            h['level'] += 1
            h['max_hp'] = self.stats(h)['health']
            if h['hp'] > 0: h['hp'] += h['max_hp'] - old  # the new HP arrives filled; dead heroes respawn full anyway
        if h['level'] >= MAX_LEVEL: h['xp'] = 0

    def knockback(self, target, source):
        dx, dy = target['x'] - source['x'], target['y'] - source['y']
        n = math.hypot(dx, dy)
        if not n: return
        x0, y0, x1, y1 = bounds(target['floor'])
        x = max(x0, min(x1, target['x'] + dx / n * KNOCKBACK))
        y = max(y0, min(y1, target['y'] + dy / n * KNOCKBACK))
        if not self.closed(target, x, y): target.update(x=x, y=y)  # never shove into a wall

    def event(self, h, kind, radius, text='', skill=''):
        self.next_id += 1
        self.effects.append(dict(id=str(self.next_id), kind=kind, text=text,
                                 x=h['x'], y=h['y'], floor=h['floor'], radius=radius,
                                 character=h.get('character', '') if skill else '', skill=skill,
                                 fx=h.get('fx', 0.), fy=h.get('fy', -1.),
                                 started=self.elapsed, expires=self.elapsed + .8))

    def use_skill(self, h, action, data):
        rules = ZODIAC[h['character']]
        ultimate = action == 'skill2'
        if h.get('curse_ultimate_left' if ultimate else 'curse_skill_left', 0) > 0: return
        prefix = 'e' if ultimate else 'q'
        kind, power = rules[prefix + '_kind'], rules[prefix + '_power']
        h[action + '_cooldown'] = (22. if ultimate else rules['q_cooldown']) * (1. - self.stats(h)['cooldown'])
        h['character_locked'] = True
        if h['character'] == 'tiger': h['cast_left'] = TIGER_CAST_SECONDS[action]
        scale = rules[prefix + '_scale']
        ax, ay = data.get('aim_x', h['x'] + h['fx']) - h['x'], data.get('aim_y', h['y'] + h['fy']) - h['y']
        n = math.hypot(ax, ay)
        if n: h.update(fx=ax / n, fy=ay / n)
        self.start_action(h, 'ultimate' if ultimate else 'skill', .5 if ultimate else .32)
        if kind in ('dash', 'charge'):
            self.move(h, h['x'] + h['fx'] * 280 * scale, h['y'] + h['fy'] * 280 * scale, 280 * scale, 1.)
        if kind in ('shield', 'guard', 'fortify'):
            h.update(shield=max(h['shield'], power), shield_left=6.)
        if kind in ('heal', 'fortify', 'rally'):
            h['hp'] = min(h['max_hp'], h['hp'] + power)
        if kind == 'speed': h['speed_left'] = 4.
        if kind == 'rally': h['rally_left'] = 7.
        if not ultimate and rules['q_guard']: h['protected'] = max(h['protected'], rules['q_guard'])
        radius = (370. if ultimate else 260.) * scale
        center = dict(x=h['x'], y=h['y'])
        if kind == 'meteor':
            reach = min(650., n)
            center.update(x=h['x'] + h['fx'] * reach, y=h['y'] + h['fy'] * reach)
            radius = 260. * scale
        if kind not in ('heal', 'shield', 'speed', 'rally', 'fortify'):
            for target in self.all_targets():
                if target['team'] == h['team'] or target['floor'] != h['floor'] or target['hp'] <= 0: continue
                dx, dy = target['x'] - h['x'], target['y'] - h['y']
                if kind == 'line':
                    forward, side = dx * h['fx'] + dy * h['fy'], abs(dx * h['fy'] - dy * h['fx'])
                    hit = 0 <= forward <= 650 * scale and side <= 65
                else:
                    hit = distance(center, target) <= radius
                    if kind == 'cone': hit &= dx * h['fx'] + dy * h['fy'] >= math.hypot(dx, dy) * .35
                if hit:
                    dealt = self.damage(target, power * self.stats(h)['attack'] / 20., h, 'magic')
                    if dealt and target['kind'] != 'base':
                        if kind in ('stun', 'fear'): target['stun_left'] = 1.2
                        if kind in ('slow', 'venom'): target['slow_left'] = 3.
                        if kind in ('poison', 'venom'):
                            target.update(poison_left=4., poison_damage=8. * DAMAGE_SCALE, poison_owner=h['id'])
        self.event(dict(h, x=center['x'], y=center['y']), kind, 650. * scale if kind == 'line' else radius, '', prefix)

    def basic_attack(self, h):
        """Long reach: rat pierces a line, others hit the nearest in a narrow cone. Short reach: a melee fan."""
        if h.get('curse_attack_left', 0) > 0: return
        rules = ZODIAC[h['character']]
        reach, line, fan = rules['reach'], h['character'] == 'rat', rules['reach'] < 400
        dot = .2 if h['character'] == 'ox' else .5 if fan else .85
        targets = []
        for a in self.all_targets():
            if a['team'] == h['team'] or a['hp'] <= 0 or a['floor'] != h['floor']: continue
            dx, dy = a['x'] - h['x'], a['y'] - h['y']
            forward, reach_to = dx * h['fx'] + dy * h['fy'], distance(a, h) - (a['body_radius'] if fan else 0)
            if line: ok = 0 <= forward <= reach and abs(dx * h['fy'] - dy * h['fx']) <= 45 + a['body_radius']
            else: ok = reach_to <= reach and forward >= math.hypot(dx, dy) * dot
            if ok and self.can_hit(h, a): targets.append(a)
        if not (line or fan): targets = sorted(targets, key=lambda a: distance(a, h))[:1]
        for target in targets: self.damage(target, self.stats(h)['attack'], h)
        h['attack_cooldown'] = .55
        self.start_action(h, 'attack', .28)
        self.event(h, 'shot', reach, '', 'a')

    def public(self, a):
        private = {'input', 'input_at', 'sequence'}
        result = {k: v for k, v in a.items() if not k.startswith('_') and k not in private}
        names = dict(base='본진', bell='황금종', guard='수호병', archer='궁수', healer='치유사', elite='중간보스', grunt='쫄병', dragon_boss='중앙 용')
        result.update(name=ZODIAC[a['character']]['name'] if a['kind'] == 'hero' else names[a['kind']],
                      role=2 if a['kind'] == 'healer' else 1 if a['kind'] == 'guard' else 0,
                      level=a.get('level', 1), party_code=f'squad-{a["team"]}', windup=0., windup_left=0.)
        return result
