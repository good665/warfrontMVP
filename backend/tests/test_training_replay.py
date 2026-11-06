import importlib.util
import json
from pathlib import Path

import pytest


def engine():
    assert importlib.util.find_spec('app.training_replay'), 'portable replay engine must exist'
    from app import training_replay
    return training_replay


def event(tick, action=0, x=0, y=0, index=0):
    return dict(tick=tick, action=action, x=x, y=y, index=index)


def test_xorshift_hand_derived_uint_wrap_and_zero_fallback():
    rng = engine().XorShift32(1)
    assert [rng.next_uint() for _ in range(3)] == [270369, 67634689, 2647435461]
    assert engine().XorShift32(0).next_uint() == engine().XorShift32(2463534242).next_uint()


def test_range_initial_target_spawn_lifetime_and_score_are_integer_rules():
    s = engine().Session('range', 1)
    # First two RNG values modulo the spawn ranges: x=19369,y=20689.
    assert s.targets[0] == [0, 19369, 20689, 180, False]
    s.apply(event(0, x=19369, y=20689))
    s.advance(72)
    t = s.targets[-1]
    s.apply(event(72, x=t[1], y=t[2]))
    assert (s.score, s.hits, s.shots) == (220, 2, 2)
    s.advance(144)
    assert len(s.targets) == 2 and s.targets[-1][4]
    t = s.targets[-1]
    s.apply(event(216, x=t[1], y=t[2]))
    assert (s.score, s.friendly_hits) == (70, 1)
    s.advance(108)
    assert s.misses == 1  # third target expires exactly at tick324


def test_range_radius_inclusive_and_idle_expiry_shots_distinct():
    s = engine().Session('range', 1)
    s.apply(event(0, x=22369, y=20689))
    assert (s.score, s.hits) == (100, 1)
    m = engine().replay('range', 1, 4500, [])
    assert m == dict(score=0, hits=0, friendly_hits=0, misses=46, shots=0,
                    deliveries=0, collisions=0, completed_codes=0, mistakes=0,
                    played_ticks=4500, elapsed_ticks=4500)


def test_drone_integer_step_clamp_collision_and_stun_boundaries():
    s = engine().Session('drone', 1)
    s.apply(event(0, 1, 90000, 20000))
    s.advance(85)
    assert s.drone == (37200, 20000) and s.collisions == 0
    s.advance(1)
    assert s.drone == (37200, 20000) and s.collisions == 1 and s.stun == 65
    s.advance(64)
    assert s.stun == 1
    s.advance(1)
    assert s.stun == 0
    s.apply(event(151, 1, 0, 0))
    s.advance(1)
    # sqrt(35400^2+18200^2)=39804; signed division truncates toward zero.
    assert s.drone == (36916, 19854)


def test_cipher_preview_boundary_hand_derived_sequence_and_final_penalty():
    s = engine().Session('cipher', 1)
    assert s.sequence == [1, 1]
    s.advance(189)
    s.apply(event(189, 2, index=1))
    assert s.progress == 0
    s.advance(1)
    s.apply(event(190, 2, index=1))
    s.advance(1)
    s.apply(event(191, 2, index=1))
    assert (s.score, s.completed_codes, len(s.sequence)) == (200, 1, 3)
    result = engine().replay('cipher', 1, 4200, [event(4200, 2, index=0)])
    assert (result['played_ticks'], result['elapsed_ticks'], result['mistakes']) == (4200, 4500, 1)


@pytest.mark.parametrize('game,seed,ticks,events', [
    ('bad', 1, 4500, []), ('range', 0, 4500, []), ('range', True, 4500, []),
    ('range', 2147483648, 4500, []), ('range', 1, 4499, []),
    ('range', 1, 4501, []), ('range', 1, 4500.0, []), ('range', 1, 4500, {}),
    ('range', 1, 4500, [event(0, 1)]), ('drone', 1, 4500, [event(0, 0)]),
    ('cipher', 1, 4500, [event(0, 0)]), ('range', 1, 4500, [event(4500)]),
    ('range', 1, 4500, [event(0), event(0)]),
    ('range', 1, 4500, [event(1), event(0)]), ('range', 1, 4500, [event(-1)]),
    ('range', 1, 4500, [event(0, x=-1)]), ('range', 1, 4500, [event(0, x=100001)]),
    ('range', 1, 4500, [event(0, y=40001)]), ('range', 1, 4500, [event(0, index=1)]),
    ('range', 1, 4500, [event(0, x=float('nan'))]),
    ('range', 1, 4500, [event(0, x=True)]), ('range', 1, 4500, [dict(tick=0)]),
    ('range', 1, 4500, [dict(event(0), extra=1)]),
    ('cipher', 1, 4500, [event(0, 2, x=1)]), ('cipher', 1, 4500, [event(0, 2, index=4)]),
    ('cipher', 1, 4201, [event(4200, 2)]),
    ('cipher', 1, 4201, [event(4200, 2), event(4201, 2)]),
    ('cipher', 1, 4199, [event(4200, 2)]),
    ('range', 1, 4500, [event(i) for i in range(4502)]),
])
def test_replay_rejects_noncanonical_or_unfinished_runs(game, seed, ticks, events):
    with pytest.raises(ValueError):
        engine().replay(game, seed, ticks, events)


def test_csharp_fixtures_match_all_metrics_and_final_state():
    fixture = Path(__file__).parent / 'fixtures' / 'training_replay_v2.json'
    assert fixture.exists(), 'C# fixture generator must publish parity corpus'
    cases = json.loads(fixture.read_text(encoding='utf-8'))
    assert {c['game'] for c in cases} == {'range', 'drone', 'cipher'}
    assert len(cases) >= 9
    for c in cases:
        assert engine().replay(c['game'], c['seed'], c['total_ticks'], c['events']) == c['metrics'], c['name']
        s = engine().Session(c['game'], c['seed'])
        for e in c['events']:
            s.advance(e['tick'] - s.played_ticks)
            s.apply(e)
        s.advance(c['total_ticks'] - s.played_ticks)
        assert s.snapshot() == c['state'], c['name']


def test_range_radius_outside_and_last_active_tick_boundaries():
    s = engine().Session('range', 1)
    s.apply(event(0, x=22370, y=20689))
    assert (s.hits, s.misses, s.shots) == (0, 1, 1)
    result = engine().replay('range', 1, 4500, [event(4499)])
    assert result['shots'] == 1 and result['played_ticks'] == 4500


def test_drone_canonical_coordinate_edges_are_accepted():
    for x, y in [(0, 0), (100000, 40000)]:
        result = engine().replay('drone', 2147483647, 4500, [event(0, 1, x, y)])
        assert result['played_ticks'] == 4500
