import pytest
from pydantic import ValidationError
from app.rts_game import RtsGame
from app.squad_routes import SquadInput


def test_g_rally_is_gone_minions_keep_their_wave_route():
    game = RtsGame(['a', 'b'])
    game.input('a', dict(sequence=1, command='gather', order_x=1800, order_y=600))
    game.tick(30)
    mine = [u for u in game.minions.values() if u['owner_id'] == 'a']
    assert mine and all(u['command'] == 'wave' for u in mine)
    assert 'pings' not in game.battle_snapshot('a')
    with pytest.raises(ValidationError):
        SquadInput(sequence=1, command='gather')
