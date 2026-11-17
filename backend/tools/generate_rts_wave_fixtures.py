from pathlib import Path
import sys,json,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.squad_rooms import SquadRooms
rooms=SquadRooms(clock=lambda:0.)
state=rooms.create('a',team_size=2)
for pid in ('b','c','d'): state=rooms.join(state['code'],pid)
game=rooms.rooms[state['code']]['game']
for _ in range(600):game.tick(.05)
folder=Path(tempfile.gettempdir())
first=rooms.state(state['code'],'a')
for name in ('warfront-rts-wave-before.json','warfront-rts-fixture.json'):(folder/name).write_text(json.dumps(first,default=list),encoding='utf-8')
for _ in range(40):game.tick(.05)
(folder/'warfront-rts-wave-after.json').write_text(json.dumps(rooms.state(state['code'],'a'),default=list),encoding='utf-8')
for name in ('warfront-rts-waves.request','warfront-rts-checks.request','warfront-zodiac-effects.request'):(folder/name).write_text('run',encoding='utf-8')
print('Created four-player wave fixture at 30s and 32s, editor requests ready')
