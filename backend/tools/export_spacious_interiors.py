"""Export the exact authoritative room geometry input for Blender and Unity QA."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import rts_map as m

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
parser.add_argument('--map-output', required=True)
args = parser.parse_args()
rooms = []
for kind, name in [('house', 'Hanok'), ('passage', 'Passage')]:
    floor, (ox, oy, rows, _) = next((f, room) for f, room in m.INTERIORS.items() if room[3] == kind)
    props = [dict(kind=p['kind'], c=p['x']/m.CELL-ox, r=p['y']/m.CELL-oy,
                  cells=[[x-ox, y-oy] for x,y in p['cells']]) for p in m.PROPS if p['floor'] == floor]
    rooms.append(dict(name=name, kind=kind, width=len(rows[0]), height=len(rows), rows=list(rows), props=props,
                      door_groups=[dict(center=list(center), cells=[list(p) for p in cells]) for center,cells in m._door_groups(rows)]))
Path(args.output).write_text(json.dumps(dict(version=m.map_payload()['version'], rooms=rooms), indent=2), encoding='utf-8')
Path(args.map_output).write_text(json.dumps(m.map_payload(), indent=2), encoding='utf-8')
print('Exported authoritative layouts:', [(r['name'], r['width'], r['height']) for r in rooms])
