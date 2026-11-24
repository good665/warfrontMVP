import math
import pytest
from app import rts_map as m
from app.rts_game import RtsGame
from app.rts_vehicles import VEHICLE_RESPAWN


def press_f(game, pid):
    h = game.heroes[pid]
    game.input(pid, dict(sequence=h['sequence'] + 1, vehicle=True))
    game.tick(.05)


def board(game, pid, vid):
    v = game.vehicles[vid]
    game.heroes[pid].update(x=v['x'] + 30, y=v['y'], floor=m.OUTDOOR, protected=0)
    press_f(game, pid)


def quiet(game, ne='car', sw='bus'):
    game.next_wave = 1e9  # no minions in the way
    game.init_vehicles(dict(ne=ne, sw=sw))


def test_one_random_vehicle_outside_each_manor_in_1v1_only():
    assert RtsGame(['a', 'b', 'c', 'd'], team_size=2).vehicles == {}
    seen = set()
    for seed in range(30):
        game = RtsGame(['a', 'b'], seed=seed)
        assert sorted(v.split('-')[1] for v in game.vehicles) == ['ne', 'sw']
        for v in game.vehicles.values():
            assert not m.blocked(m.OUTDOOR, *m.cell(v['x'], v['y']))
            seen.add(v['kind'])
        assert len(game.snapshot('a', 'R', 0)['vehicles']) == 2
    assert seen == {'car', 'bike', 'bus'}


def test_car_rams_enemy_heroes_cannot_attack_and_returns_after_respawn():
    game = RtsGame(['a', 'b']); quiet(game)
    a, b = game.heroes['a'], game.heroes['b']
    walk = game.stats(a)['speed']
    board(game, 'a', 'car-ne')
    assert a['vehicle'] == 'car' and game.stats(a)['speed'] == pytest.approx(walk * 1.5)
    assert 'car-ne' not in [v['id'] for v in game.snapshot('a', 'R', 0)['vehicles']]
    b.update(x=a['x'] + 40, y=a['y'], protected=0)
    game.tick(.05)
    assert b['hp'] <= 0
    game.tick(60.)
    assert a['vehicle'] == '' and game.vehicles['car-ne']['ready_at'] > game.elapsed
    game.tick(VEHICLE_RESPAWN)
    assert 'car-ne' in [v['id'] for v in game.snapshot('a', 'R', 0)['vehicles']]


def test_car_soaks_five_hits_then_breaks():
    game = RtsGame(['a', 'b']); quiet(game)
    a, b = game.heroes['a'], game.heroes['b']
    board(game, 'a', 'car-ne')
    hp = a['hp']
    for i in range(5):
        assert a['vehicle'] == 'car'
        game.damage(a, 50, b)
        game.tick(.3)
    assert a['vehicle'] == '' and a['hp'] == hp


def test_bike_doubles_speed_hit_or_f_dismounts_no_attacks_no_doors():
    game = RtsGame(['a', 'b']); quiet(game, ne='bike')
    a, b = game.heroes['a'], game.heroes['b']
    walk = game.stats(a)['speed']
    board(game, 'a', 'bike-ne')
    assert a['vehicle'] == 'bike' and game.stats(a)['speed'] == pytest.approx(walk * 2)
    b.update(x=a['x'] + 60, y=a['y'], protected=0, stun_left=1e9)  # b never swings back here
    game.input('a', dict(sequence=a['sequence'] + 1, attack=True, aim_x=b['x'], aim_y=b['y']))
    game.tick(.3)
    assert b['hp'] == b['max_hp']
    door = next(d for d in m.DOORS if d['floor'] == m.OUTDOOR and d['to_floor'] in m.MANOR_FLOORS)
    a.update(x=(door['cx'] + .5) * m.CELL, y=(door['cy'] + .5) * m.CELL)
    game.tick(.05)
    assert a['floor'] == m.OUTDOOR and a['vehicle'] == 'bike'
    press_f(game, 'a')
    assert a['vehicle'] == ''
    game.vehicles['bike-ne']['ready_at'] = 0.
    board(game, 'a', 'bike-ne')
    game.damage(a, 10, b)
    assert a['vehicle'] == '' and a['hp'] < a['max_hp']


def test_bus_is_a_one_way_portal_open_to_both_teams():
    game = RtsGame(['a', 'b']); quiet(game, ne='bus', sw='bus')
    b = game.heroes['b']
    board(game, 'b', 'bus-ne')  # enemy team may ride it too
    bus = game.vehicles['bus-ne']
    assert (b['x'], b['y']) == (bus['x'], bus['y'])  # aboard
    assert 'bus-ne' not in [v['id'] for v in game.snapshot('a', 'R', 0)['vehicles']]  # gone through the portal
    assert not m.blocked(m.OUTDOOR, *m.cell(bus['portal_x'], bus['portal_y']))
    start = b['x'], b['y']
    game.tick(.5)
    assert b['portal_left'] > 0 and b['x'] < 6000 and b['y'] < 1500  # still in the NE yard, drawn to the portal
    assert start[1] < b['y'] < bus['portal_y'] + 1  # driving south toward the portal
    game.tick(.6)
    assert b['y'] > bus['portal_y'] + 150 and not m.blocked(m.OUTDOOR, *m.cell(b['x'], b['y']))  # all the way through
    assert game.damage(b, 50, game.heroes['a']) == 0  # untouchable while entering
    game.tick(.2)
    assert b['portal_left'] == 0 and b['portal_out_left'] > 0
    sw = game.vehicles['bus-sw']
    assert b['x'] < 1000 and b['y'] > 5400 and abs(b['x'] - sw['x']) < 800
    assert not m.blocked(m.OUTDOOR, *m.cell(b['x'], b['y']))
    assert game.vehicles['bus-ne']['ready_at'] == pytest.approx(game.elapsed - 1.3 + VEHICLE_RESPAWN, abs=.1)  # set when F was pressed
    board(game, 'a', 'bus-ne')
    game.tick(1.3)
    assert game.heroes['a']['y'] < 3200  # on cooldown: nobody moved
    board(game, 'a', 'bus-sw')
    game.tick(1.3)
    assert game.heroes['a']['x'] > 5400 and game.heroes['a']['y'] < 1000


@pytest.mark.parametrize('kind', ['car', 'bike'])
def test_rides_keep_the_driving_direction_when_the_mouse_moves(kind):
    game = RtsGame(['a', 'b']); quiet(game, ne=kind)
    a = game.heroes['a']
    board(game, 'a', f'{kind}-ne')
    for _ in range(13): game.input('a', dict(sequence=a['sequence'] + 1, move_x=0, move_y=1)); game.tick(.1)
    assert (a['fx'], a['fy']) == pytest.approx((0, 1), abs=.05)
    # Stopped, the cursor off to the side (and the attack button held): the ride keeps facing where it went.
    game.input('a', dict(sequence=a['sequence'] + 1, move_x=0, move_y=0, aim_x=a['x'] + 300, aim_y=a['y'], attack=True)); game.tick(.1)
    assert (a['fx'], a['fy']) == pytest.approx((0, 1), abs=.05)


def test_letting_go_of_one_diagonal_key_first_keeps_the_ride_diagonal():
    game = RtsGame(['a', 'b']); quiet(game, ne='bike')
    a = game.heroes['a']
    board(game, 'a', 'bike-ne')
    def drive(mx, my, seconds):
        for _ in range(round(seconds / .05)): game.input('a', dict(sequence=a['sequence'] + 1, move_x=mx, move_y=my)); game.tick(.05)
    drive(1, 1, 1.)
    assert math.degrees(math.atan2(a['fy'], a['fx'])) == pytest.approx(45, abs=1)
    drive(1, 0, .05)  # the down key comes up a moment before the right key
    drive(0, 0, .5)
    assert math.degrees(math.atan2(a['fy'], a['fx'])) == pytest.approx(45, abs=15)
    drive(1, 0, 1.)  # a held turn still completes
    assert math.degrees(math.atan2(a['fy'], a['fx'])) == pytest.approx(0, abs=1)


def test_rides_park_where_left_and_can_be_retaken_until_their_time_is_up():
    game = RtsGame(['a', 'b']); quiet(game, ne='car')
    a, b = game.heroes['a'], game.heroes['b']
    car = game.vehicles['car-ne']
    board(game, 'a', 'car-ne')
    game.damage(a, 50, b); game.tick(.3)  # one of five hits spent
    a.update(x=a['x'] + 200, fx=1., fy=0.)
    press_f(game, 'a')
    assert a['vehicle'] == '' and (car['x'], car['y'], car['fx'], car['fy']) == (a['x'], a['y'], 1., 0.)
    parked = next(v for v in game.snapshot('a', 'R', 0)['vehicles'] if v['id'] == 'car-ne')
    assert parked['x'] == a['x'] and 0 < parked['left'] < 60
    game.tick(10.)
    press_f(game, 'a')  # back in: the same clock and the hits already taken
    assert a['vehicle'] == 'car' and a['vehicle_hits'] == 4 and a['vehicle_left'] == pytest.approx(60 - 10.4, abs=.2)
    press_f(game, 'a')
    game.tick(51.)  # time runs out while parked
    assert (car['x'], car['y']) == (car['home_x'], car['home_y']) and car['ready_at'] > game.elapsed
    press_f(game, 'a')
    assert a['vehicle'] == ''


def test_thrown_off_bike_stays_put_but_a_broken_car_goes_home():
    game = RtsGame(['a', 'b']); quiet(game, ne='bike', sw='car')
    a, b = game.heroes['a'], game.heroes['b']
    board(game, 'a', 'bike-ne')
    game.damage(a, 10, b)
    bike = game.vehicles['bike-ne']
    assert a['vehicle'] == '' and bike['ready_at'] <= game.elapsed and (bike['x'], bike['y']) == (a['x'], a['y'])
    board(game, 'b', 'car-sw')
    for _ in range(5): game.damage(b, 50, a); game.tick(.3)
    car = game.vehicles['car-sw']
    assert b['vehicle'] == '' and (car['x'], car['y']) == (car['home_x'], car['home_y']) and car['ready_at'] > game.elapsed
