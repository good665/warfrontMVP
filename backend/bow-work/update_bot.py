from pathlib import Path
p=Path('app/squad_bot.py');s=p.read_text(encoding='utf-8-sig').replace("stop_range = 105 if command == 'focus' else 35", "stop_range = 480 if command == 'focus' else 35")
s=s.replace("        data = dict(sequence=self.sequence", "        charging = hero.get('charge_active', False)\n        start_charge = visible and reach <= 650 and hero['skill1_cooldown'] <= 0 and not charging and not self.retreating\n        hold_charge = charging and hero['charge_time'] < 1.2 and not self.retreating\n        data = dict(sequence=self.sequence")
s=s.replace("attack=visible and reach <= 145+target['body_radius'],\n                    skill1=visible and reach <= 210+target['body_radius'],", "attack=visible and reach <= 700 and not charging and not start_charge,\n                    skill1=start_charge, charge_held=start_charge or hold_charge, charge_release=charging and not hold_charge,")
p.write_text(s,encoding='utf-8')
