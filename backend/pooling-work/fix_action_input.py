from pathlib import Path
p=Path('tests/test_squad_input_buffer.py')
s=p.read_text(encoding='utf-8-sig').replace("game.input('a', dict(sequence=1, skill2=True, aim_x=1800., aim_y=1200.))", "game.input('a', dict(sequence=hero['sequence'], skill2=True, aim_x=1800., aim_y=1200.))")
p.write_text(s,encoding='utf-8')
p=Path('app/squad_game.py')
s=p.read_text(encoding='utf-8').replace('HIT_PADDING = 8.', 'HIT_PADDING = 8.\nACTION_BUFFER_SECONDS = .65')
s=s.replace("input_at=-1., protected=2.)", "input_at=-1., protected=2., _pending_actions={})")
s=s.replace("        command = data.get('command', 'none')", """        if hero['hp'] > 0:
            for action in ('dodge', 'skill1', 'skill2'):
                if data.get(action):
                    hero['_pending_actions'][action] = dict(data=data.copy(), expires=self.elapsed+ACTION_BUFFER_SECONDS)
        command = data.get('command', 'none')""")
s=s.replace("                hero.update(action_left=0., attack_phase='idle', dodge_left=0.)", "                hero.update(action_left=0., attack_phase='idle', dodge_left=0.)\n                hero['_pending_actions'].clear()")
start=s.index("            melee = hero['action_kind']")
end=s.index("            if hero['action_kind'] not in ('attack', 'heavy'):",start)
s=s[:start]+'''            pending = hero['_pending_actions']
            for action in list(pending):
                if pending[action]['expires'] < self.elapsed:
                    del pending[action]
            # Dodge cancels any attack; skills cancel the basic swing. During
            # another skill/dodge the one-shot press survives movement packets.
            action = None
            if 'dodge' in pending and hero['dodge_cooldown'] <= 0 and hero['dodge_left'] <= 0:
                action = 'dodge'
            elif hero['dodge_left'] <= 0 and (hero['action_left'] <= 0 or hero['action_kind'] == 'attack'):
                for skill in ('skill1', 'skill2'):
                    if skill in pending and hero[skill+'_cooldown'] <= 0:
                        action = skill
                        break
            action_input = pending.pop(action)['data'] if action else control
            melee = hero['action_kind'] in ('attack', 'heavy') and hero['action_left'] > 0
            ax = action_input.get('aim_x', hero['x']+hero['fx'])-hero['x']
            ay = action_input.get('aim_y', hero['y']+hero['fy'])-hero['y']
            length = math.hypot(ax, ay)
            if length and (action or not melee) and hero['dodge_left'] <= 0:
                hero['fx'], hero['fy'] = ax/length, ay/length
            if action == 'dodge':
                dodge_x, dodge_y = action_input.get('move_x', 0), action_input.get('move_y', 0)
                direction = math.hypot(dodge_x, dodge_y)
                hero.update(dodge_cooldown=3., dodge_left=.22,
                            dodge_dx=dodge_x/direction if direction else hero['fx'],
                            dodge_dy=dodge_y/direction if direction else hero['fy'])
                self.start_action(hero, 'dodge', .22)
                hero.update(action_fx=hero['dodge_dx'], action_fy=hero['dodge_dy'])
            elif action == 'skill1':
                hero['skill1_cooldown'] = 5.
                self.start_action(hero, 'heavy', .55)
            elif action == 'skill2':
                hero['skill2_cooldown'] = 8.
                self.start_action(hero, 'bomb', .30)
                self.throw_bomb(hero, action_input)
            if hero['dodge_left'] > 0:
                self.walk(hero, hero['dodge_dx']*1000, hero['dodge_dy']*1000, 580, min(dt, hero['dodge_left']))
            else:
                self.walk(hero, dx/n*1000, dy/n*1000, 235, dt)
                if hero['action_left'] <= 0 and control.get('attack') and hero['attack_cooldown'] <= 0:
                    hero['attack_cooldown'] = .55
                    self.start_action(hero, 'attack', .55)
''' + s[end:]
p.write_text(s,encoding='utf-8')
