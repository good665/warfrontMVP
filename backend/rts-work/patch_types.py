from pathlib import Path
p=Path('app/squad_game.py');s=p.read_text(encoding='utf-8');s=s.replace('healer=20., base=75.', 'healer=20., scout=18., base=75.');s=s.replace("'base': '본진'", "'base': '본진', 'scout': '정찰병'");s=s.replace("'base': 0}[a['kind']]", "'base': 0, 'scout': 0}[a['kind']]");p.write_text(s,encoding='utf-8')
