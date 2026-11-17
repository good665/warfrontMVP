"""Room-local RTS computer controller using the same inputs as humans."""


class SquadBot:
    def __init__(self, pid):
        self.pid = pid

    def tick(self, game):
        if not game.reason:
            game.bot_input(self.pid)
