from pathlib import Path
p=Path('app/squad_game.py')
s=p.read_text(encoding='utf-8-sig')
s=s.replace("KINDS = ('guard', 'archer', 'healer')", "KINDS = ('guard', 'archer', 'healer')\nHIT_PADDING = 8.")
s=s.replace("95.+(target['body_radius'] if target else 0.)", "95.+(self.hit_radius(target) if target else 0.)")
s=s.replace('self.damage(target, 18)', 'self.damage(target, 18, unit, 18.)')
s=s.replace("target['body_radius']+16.", 'self.hit_radius(target)+16.')
s=s.replace('self.damage(target, 15)', 'self.damage(target, 15, start, 10.)')
s=s.replace("reach+enemy['body_radius']", 'reach+self.hit_radius(enemy)')
s=s.replace('self.damage(enemy, power)', 'self.damage(enemy, power, hero, 28. if heavy else 18.)')
s=s.replace('contacts.append((enemy, power))', "contacts.append((enemy, power, dict(x=hero['x'], y=hero['y']), 28. if heavy else 18.))")
s=s.replace("distance(bomb, enemy) <= bomb['radius']", "distance(bomb, enemy) <= bomb['radius']+self.hit_radius(enemy)")
s=s.replace('self.damage(enemy, 30)', 'self.damage(enemy, 30, bomb, 30.)')
s=s.replace('    def damage(self, target, amount):', '''    @staticmethod
    def hit_radius(target):
        # Combat tolerance is independent of navigation/body collision.
        return target['body_radius']+(0. if target['kind'] == 'base' else HIT_PADDING)

    def knockback(self, target, source, amount):
        if target['kind'] == 'base' or amount <= 0:
            return
        dx, dy = target['x']-source['x'], target['y']-source['y']
        length = math.hypot(dx, dy)
        if length < 1e-9:
            return
        # Small collision-checked steps avoid pushing through obstacle corners.
        steps = max(1, math.ceil(amount/3.))
        for _ in range(steps):
            self.walk(target, dx/length*amount, dy/length*amount, amount/steps, 1.)

    def damage(self, target, amount, source=None, push=0.):''')
s=s.replace("        target['hit_flash'] = .15", "        target['hit_flash'] = .15\n        if source is not None:\n            self.knockback(target, source, push)")
s=s.replace('for target, power in contacts:\n            self.damage(target, power)', 'for target, power, source, push in contacts:\n            self.damage(target, power, source, push)')
p.write_text(s,encoding='utf-8')
p=Path('tests/test_squad_actions.py')
s=p.read_text(encoding='utf-8-sig').replace('[(167., 140.), (167.01, 160.), (-100., 160.)]', '[(175., 140.), (175.01, 160.), (-100., 160.)]')
p.write_text(s,encoding='utf-8')
