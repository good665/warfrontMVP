"""Territory-constrained construction and one-time match technologies."""
import math

BUILDINGS = {'barracks': (100., 12., 500.), 'outpost': (80., 10., 350.),
             'tower': (100., 12., 600.), 'academy': (120., 15., 400.)}
RESEARCH = {'attack': (100., 15.), 'armor': (100., 15.), 'recon': (80., 12.)}


def distance(a, b):
    return math.hypot(a['x']-b['x'], a['y']-b['y'])


class SquadInfrastructure:
    def init_infrastructure(self):
        self.buildings = {}
        self.technologies = [dict(attack=0, armor=0, recon=0) for _ in range(2)]
        self.research_jobs = [[], []]

    def has_building(self, team, kind):
        return any(b['team'] == team and b['kind'] == kind and b['hp'] > 0 and b['remaining'] <= 0
                   for b in self.buildings.values())

    def infrastructure_input(self, hero, data):
        team, action = hero['team'], data.get('economy', 'none')
        if action.startswith('build_'):
            kind = action[6:]
            if kind not in BUILDINGS:
                return 'invalid_action'
            if any(b['team'] == team and b['kind'] == kind and b['hp'] > 0 for b in self.buildings.values()):
                return 'building_exists'
            point = dict(x=data.get('order_x', 0), y=data.get('order_y', 0))
            territory = distance(self.bases[team], point) <= 520 or any(
                p['owner'] == team and distance(p, point) <= 350 for p in self.points)
            if (not territory or not 80 <= point['x'] <= 3520 or not 80 <= point['y'] <= 2320
                    or not self.clear(point, point, padding=65)
                    or any(distance(point, b) < 150 for b in [*self.bases, *self.buildings.values()] if b['hp'] > 0)):
                return 'invalid_build_location'
            cost, duration, hp = BUILDINGS[kind]
            if self.supplies[team]+1e-9 < cost:
                return 'insufficient_supplies'
            self.supplies[team] -= cost
            self.next_strategy_id += 1
            uid = f'building-{team}-{self.next_strategy_id}'
            building = self.actor(uid, kind, team, point['x'], point['y'], hp)
            building.update(remaining=duration, duration=duration, owner_id=hero['id'])
            self.buildings[uid] = building
            return ''
        if action.startswith('research_'):
            kind = action[9:]
            if kind not in RESEARCH:
                return 'invalid_action'
            if not self.has_building(team, 'academy'):
                return 'academy_required'
            if self.technologies[team][kind]:
                return 'already_researched'
            if self.research_jobs[team]:
                return 'research_busy'
            cost, duration = RESEARCH[kind]
            if self.supplies[team]+1e-9 < cost:
                return 'insufficient_supplies'
            self.supplies[team] -= cost
            self.research_jobs[team].append(dict(id=kind, duration=duration, remaining=duration))
            return ''
        return 'invalid_action'

    def infrastructure_tick(self, dt):
        for building in self.buildings.values():
            if building['hp'] > 0:
                building['remaining'] = max(0., building['remaining']-dt)
                if building['remaining'] < 1e-9:
                    building['remaining'] = 0.
        for team in (0, 1):
            queue = self.research_jobs[team]
            if queue and self.has_building(team, 'academy'):
                queue[0]['remaining'] = max(0., queue[0]['remaining']-dt)
                if queue[0]['remaining'] <= 1e-9:
                    self.technologies[team][queue.pop(0)['id']] = 1

    def all_targets(self):
        return [*self.units.values(), *self.bases, *self.buildings.values()]
