"""Extract unchanged base zodiac geometry for the Unity SidelineZodiacBuilder."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

ANIMALS = ('rat', 'ox', 'tiger', 'rabbit', 'dragon', 'snake', 'horse', 'goat', 'monkey', 'rooster', 'dog', 'pig')


def extract(source):
    raw = Path(source).read_bytes()
    match = re.search(r'\bconst\s+MODELS\s*=\s*', raw.decode('utf-8-sig'))
    if not match:
        raise ValueError('MODELS assignment missing')
    models, _ = json.JSONDecoder().raw_decode(raw.decode('utf-8-sig')[match.end():])
    characters = []
    for animal in ANIMALS:
        source_id = 'partner_' + ('sheep' if animal == 'goat' else animal)
        parts = []
        for name, part in models[source_id].items():
            if name != 'body' and not re.fullmatch(r'leg\d+', name):
                continue
            origin = part['o']
            if len(origin) != 3 or not all(math.isfinite(v) for v in origin):
                raise ValueError('Invalid pivot: ' + source_id + '/' + name)
            groups = []
            for group in part['g']:
                p, n, indices, color = group['p'], group['n'], group['i'], group['m']
                if (not p or len(p) % 3 or len(n) != len(p) or len(indices) % 3
                        or not all(math.isfinite(v) for v in p + n)
                        or not all(isinstance(i, int) and 0 <= i < len(p)//3 for i in indices)
                        or not re.fullmatch(r'#[0-9a-fA-F]{6}', color)):
                    raise ValueError('Invalid geometry: ' + source_id + '/' + name)
                groups.append(dict(color=color, positions=p, normals=n, triangles=indices))
            parts.append(dict(name=name, origin=origin, groups=groups))
        if not any(p['name'] == 'body' for p in parts):
            raise ValueError('Body missing: ' + source_id)
        characters.append(dict(id=animal, sourceId=source_id, parts=parts))
    return dict(sourceSha256=hashlib.sha256(raw).hexdigest(), characters=characters)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = extract(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, separators=(',', ':'), allow_nan=False), encoding='utf-8')
    print('Exported', len(result['characters']), 'base zodiac models to', args.output)
