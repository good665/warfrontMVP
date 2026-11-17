from app.squad_rooms import SquadRooms


def test_two_vs_two_waits_for_four_and_assigns_teams():
    rooms=SquadRooms(clock=lambda:0.)
    code=rooms.create('a',team_size=2)['code']
    assert rooms.join(code,'b')['status']=='waiting'
    assert rooms.join(code,'c')['status']=='waiting'
    state=rooms.join(code,'d')
    assert state['status']=='active'
    assert [m['team'] for m in state['members']]==[0,1,0,1]


def test_queues_do_not_mix_team_sizes():
    rooms=SquadRooms(clock=lambda:0.)
    first=rooms.create('a',queue=True,team_size=1)
    second=rooms.create('b',queue=True,team_size=2)
    assert first['code']!=second['code']


def test_computer_fills_three_slots():
    rooms=SquadRooms(clock=lambda:0.)
    state=rooms.computer('a',team_size=2)
    assert state['status']=='active' and len(state['members'])==4


def test_one_teammate_leaving_does_not_end_match():
    rooms=SquadRooms(clock=lambda:0.)
    code=rooms.create('a',team_size=2)['code']
    for pid in ('b','c','d'): rooms.join(code,pid)
    rooms.leave('a')
    assert rooms.state(code,'c')['status']=='active'
    rooms.leave('c')
    assert rooms.state(code,'b')['winner']==1


def test_leaving_pause_owner_releases_team_match():
    rooms=SquadRooms(clock=lambda:0.)
    code=rooms.create('a',team_size=2)['code']
    for pid in ('b','c','d'): rooms.join(code,pid)
    rooms.pause(code,'a',True)
    rooms.leave('a')
    assert not rooms.state(code,'c')['paused']
