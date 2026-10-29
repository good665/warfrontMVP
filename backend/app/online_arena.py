"""Server-owned 1v1/3v3 simulation; accepts controls, not positions/results."""
import math
from dataclasses import asdict, dataclass

STAGE_SECONDS = 60
SCORE_TARGET = 420
TIME_LIMIT = 900
COVERS = [(320, 220, 70, 125), (320, 425, 70, 110), (890, 220, 70, 125),
          (890, 425, 70, 110), (520, 180, 90, 36), (670, 180, 90, 36),
          (520, 525, 90, 36), (670, 525, 90, 36)]


def normalized(x, y):
    length = math.hypot(x, y)
    return (x / length, y / length) if length > 0.001 else (0.0, 0.0)


def blocked(x, y):
    return not (45 <= x <= 1235 and 173 <= y <= 567) or any(
        rx - 17 <= x <= rx + w + 17 and ry - 17 <= y <= ry + h + 17 for rx, ry, w, h in COVERS)


def line_clear(ax, ay, bx, by):
    for rx, ry, w, h in COVERS:
        lo, hi = 0.0, 1.0
        for p, q in ((ax - bx, ax - rx), (bx - ax, rx + w - ax),
                     (ay - by, ay - ry), (by - ay, ry + h - ay)):
            if abs(p) < 1e-9:
                if q < 0:
                    break
            elif p < 0:
                lo = max(lo, q / p)
            else:
                hi = min(hi, q / p)
            if lo > hi:
                break
        else:
            return False
    return True


@dataclass
class Fighter:
    name: str
    team: int
    role: int
    x: float
    actor_id: int = 0
    y: float = 370.0
    fx: float = 1.0
    fy: float = 0.0
    hp: float = 120.0
    max_hp: float = 120.0
    respawn_left: float = 0.0
    protection: float = 2.0
    shield: float = 0.0
    haste: float = 0.0
    fire_boost: float = 0.0
    dodge_left: float = 0.0
    attack_cooldown: float = 0.0
    dodge_cooldown: float = 0.0
    skill1_cooldown: float = 0.0
    skill2_cooldown: float = 0.0
    hit_flash: float = 0.0
    damage_done: float = 0.0
    healing_done: float = 0.0
    objective_seconds: float = 0.0
    kills: int = 0
    deaths: int = 0


class OnlineArena:
    def __init__(self, names, roles):
        if len(names) not in (2, 6) or len(names) != len(roles):
            raise ValueError("A friend match requires two or six humans")
        self.team_size = len(names) // 2
        self.score_target = SCORE_TARGET if self.team_size == 1 else 600
        self.time_limit = TIME_LIMIT if self.team_size == 1 else 1200
        self.actors = []
        for slot, (name, role) in enumerate(zip(names, roles)):
            team = slot % 2
            hp = (120, 160, 100)[role]
            self.actors.append(Fighter(name, team, role, 105.0 if team == 0 else 1175.0,
                                       actor_id=slot, y=370 if self.team_size == 1 else 285 + slot // 2 * 80,
                                       fx=1.0 if team == 0 else -1.0, hp=hp, max_hp=hp))
        self.elapsed = 0.0
        self.blue_score = self.red_score = self.capture = 0.0
        self.owner = -1
        self.contested = self.finished = False
        self.winner = -1
        self.bullets = []
        self.dangers = []
        self.supplies = [dict(x=640.0, y=240.0, ready=True, respawn=0.0),
                         dict(x=640.0, y=500.0, ready=True, respawn=0.0)]
        self.feed = [f"ONLINE {self.team_size}:{self.team_size} / CAPTURE THE POINT"]
        self.danger_timer = 0.0
        self.previous_stage = 1

    @property
    def stage(self):
        return 1 + int(self.elapsed // STAGE_SECONDS)

    def finish(self, winner, reason):
        if not self.finished:
            self.finished = True
            self.winner = winner
            self.feed.insert(0, reason)

    def move(self, actor, dx, dy):
        if not blocked(actor.x + dx, actor.y):
            actor.x += dx
        if not blocked(actor.x, actor.y + dy):
            actor.y += dy

    def damage(self, target, amount, source=None):
        if target.hp <= 0 or target.protection > 0:
            return
        amount = min(target.hp, amount * (0.35 if target.shield > 0 else 1))
        target.hp -= amount
        target.hit_flash = 0.15
        if source is not None:
            source.damage_done += amount
        if target.hp <= 0:
            target.deaths += 1
            target.respawn_left = min(12, 7 + self.stage)
            if source is not None:
                source.kills += 1
                if source.team == 0:
                    self.blue_score += 3
                else:
                    self.red_score += 3
                self.feed.insert(0, f"{source.name} > {target.name}")
                self.feed = self.feed[:4]

    def skill(self, actor, second):
        if second:
            actor.skill2_cooldown = 14
            if actor.role == 2:
                for ally in self.actors:
                    if ally.team == actor.team and ally.hp > 0 and math.hypot(ally.x - actor.x, ally.y - actor.y) < 170:
                        ally.haste = 5
            else:
                for enemy in self.actors:
                    if enemy.team != actor.team and enemy.hp > 0 and math.hypot(enemy.x - actor.x, enemy.y - actor.y) < 140 and line_clear(actor.x, actor.y, enemy.x, enemy.y):
                        self.damage(enemy, 25 if actor.role == 1 else 38, actor)
                        dx, dy = normalized(enemy.x - actor.x, enemy.y - actor.y)
                        self.move(enemy, dx * 28, dy * 28)
        else:
            actor.skill1_cooldown = 12
            if actor.role == 0:
                actor.fire_boost = 5
            elif actor.role == 1:
                for ally in self.actors:
                    if ally.team == actor.team and ally.hp > 0 and math.hypot(ally.x - actor.x, ally.y - actor.y) < 145:
                        ally.shield = 5
            else:
                for ally in self.actors:
                    if ally.team == actor.team and ally.hp > 0 and math.hypot(ally.x - actor.x, ally.y - actor.y) < 150:
                        amount = min(45, ally.max_hp - ally.hp)
                        ally.hp += amount
                        actor.healing_done += amount

    def step(self, dt, controls):
        if self.finished:
            return
        # The room runner supplies a fixed step, never a client-provided time delta.
        if not 0 < dt <= 0.05:
            raise ValueError("invalid server step")
        self.elapsed = round(self.elapsed + dt, 6)
        if self.stage != self.previous_stage:
            self.previous_stage = self.stage
            self.danger_timer = 0
            self.feed.insert(0, f"THREAT LEVEL {self.stage}")
            self.feed = self.feed[:4]
        for actor, control in zip(self.actors, controls):
            if actor.hp <= 0:
                actor.respawn_left = max(0, actor.respawn_left - dt)
                if actor.respawn_left == 0:
                    actor.hp = actor.max_hp
                    actor.x = 105 if actor.team == 0 else 1175
                    actor.y = 370 if self.team_size == 1 else 285 + actor.actor_id // 2 * 80
                    actor.protection = 2.5
                    for key in ("shield", "haste", "fire_boost", "dodge_left", "attack_cooldown", "dodge_cooldown", "skill1_cooldown", "skill2_cooldown"):
                        setattr(actor, key, 0)
                continue
            for key in ("protection", "shield", "haste", "fire_boost", "dodge_left", "attack_cooldown",
                        "dodge_cooldown", "skill1_cooldown", "skill2_cooldown", "hit_flash"):
                setattr(actor, key, max(0, getattr(actor, key) - dt))
            dx, dy = control.get("move_x", 0.0), control.get("move_y", 0.0)
            if math.hypot(dx, dy) > 1:
                dx, dy = normalized(dx, dy)
            aim = normalized(control.get("aim_x", actor.x + actor.fx) - actor.x,
                             control.get("aim_y", actor.y + actor.fy) - actor.y)
            if aim != (0.0, 0.0):
                actor.fx, actor.fy = aim
            if control.get("dodge") and actor.dodge_cooldown == 0:
                actor.dodge_left, actor.dodge_cooldown = 0.2, 4
                actor.protection = max(actor.protection, 0.25)
                if math.hypot(dx, dy) > 0.1:
                    actor.fx, actor.fy = normalized(dx, dy)
            speed = (155 if actor.role == 1 else 180) * (1.35 if actor.haste > 0 else 1)
            if actor.dodge_left > 0:
                dx, dy, speed = actor.fx, actor.fy, 650
            self.move(actor, dx * speed * dt, dy * speed * dt)
            if control.get("skill1") and actor.skill1_cooldown == 0:
                self.skill(actor, False)
            if control.get("skill2") and actor.skill2_cooldown == 0:
                self.skill(actor, True)
            if control.get("attack") and actor.attack_cooldown == 0:
                actor.attack_cooldown = (0.42 if actor.role == 0 else 0.65) * (0.55 if actor.fire_boost > 0 else 1)
                self.bullets.append(dict(team=actor.team, actor_id=actor.actor_id, x=actor.x + actor.fx * 22, y=actor.y + actor.fy * 22,
                                         vx=actor.fx * 470, vy=actor.fy * 470, life=1.5, damage=15 if actor.role == 0 else 12))
        remaining_bullets = []
        for bullet in self.bullets:
            nx, ny = bullet["x"] + bullet["vx"] * dt, bullet["y"] + bullet["vy"] * dt
            bullet["life"] -= dt
            if bullet["life"] <= 0 or not line_clear(bullet["x"], bullet["y"], nx, ny):
                continue
            target = next((a for a in self.actors if a.team != bullet["team"] and a.hp > 0 and math.hypot(a.x - nx, a.y - ny) < 22), None)
            if target is not None:
                self.damage(target, bullet["damage"], self.actors[bullet["actor_id"]])
                continue
            bullet.update(x=nx, y=ny)
            remaining_bullets.append(bullet)
        self.bullets = remaining_bullets
        self.update_environment(dt)
        present = [a.hp > 0 and math.hypot(a.x - 640, a.y - 370) < 92 for a in self.actors]
        blue = any(inside and a.team == 0 for a, inside in zip(self.actors, present))
        red = any(inside and a.team == 1 for a, inside in zip(self.actors, present))
        self.contested = blue and red
        for actor, inside in zip(self.actors, present):
            if inside:
                actor.objective_seconds += dt
        if blue and not red:
            self.capture = min(100, self.capture + dt * 14)
        elif red and not blue:
            self.capture = max(-100, self.capture - dt * 14)
        if self.capture >= 100:
            self.owner = 0
        elif self.capture <= -100:
            self.owner = 1
        if not self.contested:
            if self.owner == 0 and not red:
                self.blue_score += dt
            elif self.owner == 1 and not blue:
                self.red_score += dt
        if max(self.blue_score, self.red_score) >= self.score_target or self.elapsed >= self.time_limit:
            winner = -1 if abs(self.blue_score - self.red_score) < 0.01 else (0 if self.blue_score > self.red_score else 1)
            self.finish(winner, "MATCH COMPLETE")

    def update_environment(self, dt):
        if self.stage >= 2:
            self.danger_timer -= dt
            if self.danger_timer <= 0:
                positions = [(450, 370), (830, 370), (640, 370), (640, 250)]
                self.dangers.extend(dict(x=x, y=y, radius=54.0, age=0.0) for x, y in positions[:min(4, self.stage)])
                self.danger_timer = max(10, 27 - self.stage * 3)
        for danger in self.dangers:
            danger["age"] += dt
            if danger["age"] < 2:
                continue
            for actor in self.actors:
                if math.hypot(actor.x - danger["x"], actor.y - danger["y"]) < danger["radius"] + 16:
                    self.damage(actor, dt * min(18, 6 + self.stage * 2))
        self.dangers = [d for d in self.dangers if d["age"] <= 7]
        for supply in self.supplies:
            if not supply["ready"]:
                supply["respawn"] -= dt
                supply["ready"] = supply["respawn"] <= 0
                continue
            for actor in self.actors:
                if 0 < actor.hp < actor.max_hp and math.hypot(actor.x - supply["x"], actor.y - supply["y"]) < 32:
                    actor.hp = min(actor.max_hp, actor.hp + 35)
                    supply.update(ready=False, respawn=30)
                    break

    def snapshot(self):
        return dict(elapsed=self.elapsed, stage=self.stage, stage_seconds=STAGE_SECONDS,
                    next_stage_in=STAGE_SECONDS - self.elapsed % STAGE_SECONDS,
                    remaining=max(0, self.time_limit - self.elapsed), blue_score=self.blue_score,
                    red_score=self.red_score, capture=self.capture, owner=self.owner,
                    contested=self.contested, winner=self.winner, actors=[asdict(a) for a in self.actors],
                    bullets=[{k: v for k, v in b.items() if k != "damage"} for b in self.bullets],
                    dangers=[dict(d) for d in self.dangers], supplies=[dict(s) for s in self.supplies], feed=list(self.feed))
