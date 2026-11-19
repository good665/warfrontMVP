import importlib.util
from pathlib import Path

from app.squad_items import ITEMS
from app.zodiac_rules import ZODIAC


def load_builder():
    path = Path(__file__).resolve().parents[1] / 'tools' / 'build_lang_en.py'
    spec = importlib.util.spec_from_file_location('build_lang_en', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_server_ui_string_has_english():
    # A Korean text edit in zodiac_rules / squad_items must come with its English line.
    rows = load_builder().table()
    for z in ZODIAC.values():
        for key in ('name', 'basic', 'q', 'e', 'q_desc', 'e_desc'):
            assert rows[z[key]].isascii(), z[key]
    for item in ITEMS.values():
        assert rows[item['name']].isascii(), item['name']
    assert rows['상대편 스킬을 1분간 금지시킵니다'] == 'Enemy skills sealed for 1 minute'
