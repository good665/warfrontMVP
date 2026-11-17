from pathlib import Path
p=Path('app/squad_game.py')
s=p.read_text(encoding='utf-8').replace('ACTION_BUFFER_SECONDS = .65', 'ACTION_BUFFER_SECONDS = .65\nMELEE_ACTIVE_END = .43')
s=s.replace('bomb_radius=150.)', 'bomb_radius=150., attack_windup=.16, heavy_windup=.20, melee_active_end=MELEE_ACTIVE_END)',1)
anchor='    def melee_tick(self, hero, dt, contacts=None):'
s=s.replace(anchor, '''    def melee_overlaps(self, hero, target, reach):
        dx, dy = target['x']-hero['x'], target['y']-hero['y']
        radius = self.hit_radius(target)
        d = math.hypot(dx, dy)
        if d > reach+radius:
            return False
        forward = dx*hero['action_fx']+dy*hero['action_fy']
        side = abs(-dx*hero['action_fy']+dy*hero['action_fx'])
        cosine = COMBAT_RULES['attack_dot']
        if d < 1e-9 or forward >= d*cosine:
            return True
        # Closest point on either finite sector edge, including the tip.
        # A body can overlap the swing even when its center is outside it.
        sine = math.sqrt(1.-cosine*cosine)
        projection = max(0., min(reach, forward*cosine+side*sine))
        return math.hypot(forward-projection*cosine, side-projection*sine) <= radius

'''+anchor)
s=s.replace("windup = .16 if hero['action_kind'] == 'attack' else .20", "windup = COMBAT_RULES['attack_windup' if hero['action_kind'] == 'attack' else 'heavy_windup']")
s=s.replace('if after >= windup and before < windup+.10:', 'if after >= windup and before < MELEE_ACTIVE_END:')
s=s.replace("                d = distance(hero, enemy)\n                dot = ((enemy['x']-hero['x'])*hero['action_fx']+(enemy['y']-hero['y'])*hero['action_fy'])/max(1e-9, d)\n", '')
s=s.replace("and d <= reach+self.hit_radius(enemy) and (d < 1e-9 or dot >= .35) and self.clear(hero, enemy)", "and enemy['protected'] <= 0 and enemy['dodge_left'] <= 0\n                        and self.melee_overlaps(hero, enemy, reach) and self.clear(hero, enemy)")
s=s.replace("'active' if after < windup+.10 else 'recovery'", "'active' if after < MELEE_ACTIVE_END else 'recovery'")
p.write_text(s,encoding='utf-8')
p=Path('tests/test_squad_actions.py')
s=p.read_text(encoding='utf-8-sig').replace('game.melee_tick(hero, .30)\n    enemy', 'game.melee_tick(hero, .31)\n    enemy')
p.write_text(s,encoding='utf-8')
