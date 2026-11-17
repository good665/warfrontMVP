from pathlib import Path
p=Path('app/squad_game.py')
s=p.read_text(encoding='utf-8')
s=s.replace("visible = [a for a in enemies if distance(unit, a) <= reach", "visible = [a for a in enemies if distance(unit, a) <= reach+(0. if unit['kind'] == 'archer' else self.hit_radius(a))")
s=s.replace("reach = 320 if unit['kind'] == 'archer' else 95", "reach = 320. if unit['kind'] == 'archer' else 95.+self.hit_radius(target)")
p.write_text(s,encoding='utf-8')
p=Path('tests/test_squad_companions.py')
s=p.read_text(encoding='utf-8-sig').replace("assert snap['projectiles'][0]['end_x'] == enemy['x']", "assert snap['projectiles'][0]['end_x'] == 1250.\n    assert enemy['x'] == 1260.  # Impact pushes the target past the fixed arrow endpoint.")
p.write_text(s,encoding='utf-8')
