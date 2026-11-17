import importlib.util
import json
from pathlib import Path
import pytest


def converter():
    spec = importlib.util.spec_from_file_location('sideline_export', Path(__file__).parents[1] / 'tools/export_sideline_zodiac.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source():
    geometry = dict(m='#ff9933', p=[0, 0, 0, 1, 0, 0, 0, 1, 0], n=[0, 0, 1]*3, i=[0, 1, 2])
    return {'partner_'+animal: dict(body=dict(o=[0, 0, 0], g=[geometry]),
                                  leg0=dict(o=[.2, .3, 0], g=[geometry]),
                                  stage2=dict(o=[0, 0, 0], g=[geometry]),
                                  spin=dict(o=[0, 1, 0], g=[geometry]))
            for animal in ('rat', 'ox', 'tiger', 'rabbit', 'dragon', 'snake', 'horse', 'sheep', 'monkey', 'rooster', 'dog', 'pig')}


def test_export_keeps_twelve_base_models_and_maps_sheep(tmp_path):
    original = tmp_path / 'models.js'
    original.write_text("'use strict';\nconst MODELS = " + json.dumps(source()) + ';\n', encoding='utf-8')
    before = original.read_bytes()
    result = converter().extract(original)
    assert len(result['characters']) == 12
    goat = next(c for c in result['characters'] if c['id'] == 'goat')
    assert goat['sourceId'] == 'partner_sheep'
    assert [p['name'] for p in goat['parts']] == ['body', 'leg0']
    assert goat['parts'][1]['origin'] == [.2, .3, 0]
    assert goat['parts'][0]['groups'][0]['triangles'] == [0, 1, 2]
    assert original.read_bytes() == before
    assert len(result['sourceSha256']) == 64


@pytest.mark.parametrize('field,value', [('i', [0, 1, 9]), ('p', [float('nan'), 0, 0]), ('m', 'unknown')])
def test_invalid_geometry_is_rejected(tmp_path, field, value):
    models = source()
    models['partner_rat']['body']['g'][0][field] = value
    original = tmp_path / 'models.js'
    original.write_text('const MODELS = ' + json.dumps(models) + ';', encoding='utf-8')
    with pytest.raises(ValueError):
        converter().extract(original)
