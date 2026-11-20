"""Actor state, damage and zodiac abilities shared by the RTS simulation."""
import math
from .zodiac_rules import ZODIAC, DAMAGE_SCALE
from .squad_items import armor_bonus, weapon_bonus

STAT_KEYS = ('hp', 'attack', 'armor', 'magic_armor', 'speed', 'armor_pen', 'magic_pen', 'lifesteal')
COMBAT_RULES = dict(attack_reach=145., heavy_reach=210., attack_dot=.35)
# Unity plays the tiger's Mixamo clips at 2x (2.4s slash Q, 5.4s roar E); the hero stays put and holds fire meanwhile.
TIGER_CAST_SECONDS = dict(skill1=1.2, skill2=2.7)


def distance(a, b):
    return math.hypot(a['x'] - b['x'], a['y'] - b['y'])


class RtsCombat:
    @staticmethod
    def actor(uid, kind, team, x, y, hp, floor=1):
        a = dict(id=uid, kind=kind, team=team, x=x, y=y, hp=float(hp), max_hp=float(hp), fx=1.-2*team, fy=0., attack_cooldown=0., dodge_cooldown=0., skill1_cooldown=0., skill2_cooldown=0., dodge_left=0., dodge_dx=0., dodge_dy=0., hit_flash=0., respawn_left=0., charge_active=False, charge_time=0., charge_ratio=0., protected=0., body_radius=dict(hero=22., guard=22., archer=20., healer=20., base=75.)[kind], action_id=0, action_target='', action_kind='', action_left=0., action_duration=0., action_fx=1.-2*team, action_fy=0., attack_phase='idle', _action_hits=set())
        a.update(floor=floor, jump_left=0., jump_cooldown=0., slow_left=0., stun_left=0., poison_left=0., poison_damage=0., poison_owner='', owner_id='', shield=0., shield_left=0., cast_left=0.)
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
        if h['speed_left'] > 0: result['speed'] *= 1.45
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
        target['hit_flash'] = .16
        if hero_source and source['hp'] > 0 and kind != 'true':
            source['hp'] = min(source['max_hp'], source['hp'] + amount * self.stats(source)['lifesteal'])
        if target['hp'] <= 0:
            target.update(action_left=0., attack_phase='idle')
            if target['kind'] == 'hero':
                target.update(respawn_left=8., shield=0.)
                target['_pending_actions'].clear()
        return amount

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
        self.start_action(h, 'ultimate' if ultimate else 'skill', .5 if ultimate else .32)
        if h['character'] == 'tiger': h['cast_left'] = TIGER_CAST_SECONDS[action]
        scale = rules[prefix + '_scale']
        ax, ay = data.get('aim_x', h['x'] + h['fx']) - h['x'], data.get('aim_y', h['y'] + h['fy']) - h['y']
        n = math.hypot(ax, ay)
        if n: h.update(fx=ax / n, fy=ay / n)
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
        names = dict(base='본진', guard='수호병', archer='궁수', healer='치유사', elite='중간보스', grunt='쫄병', dragon_boss='중앙 용')
        result.update(name=ZODIAC[a['character']]['name'] if a['kind'] == 'hero' else names[a['kind']],
                      role=2 if a['kind'] == 'healer' else 1 if a['kind'] == 'guard' else 0,
                      level=1, party_code=f'squad-{a["team"]}', windup=0., windup_left=0.)
        return result
