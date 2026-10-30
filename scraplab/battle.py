"""Arcade points from measured impacts; points never change physical forces."""
from dataclasses import dataclass, asdict
import json


class BattleScore:
    def __init__(self):
        self.points = [0, 0]
        self.hits = [0, 0]
        self.last_hit = [-10., -10.]
        self.events = []
        self.finished = False

    def impact(self, time, side, impulse, closing_speed, weapon, position):
        # First-contact gating is done by Simulation. Cooldown groups a multi-part
        # collision into one hit and prevents contact jitter from farming points.
        if self.finished or time < 2 or impulse < 5 or closing_speed < .8 or time-self.last_hit[side] < .55:
            return 0
        value = 10 + min(20, int(impulse/4)) + (15 if weapon else 0)
        self.points[side] += value
        self.hits[side] += 1
        self.last_hit[side] = time
        self.events.append((time, side, value, "WEAPON HIT" if weapon else "RAM", tuple(position)))
        self.events = self.events[-12:]
        return value

    def finish(self, winner, time, knockout=False):
        if self.finished:
            return
        self.finished = True
        if winner is not None and knockout:
            self.points[winner] += 250
            self.events.append((time, winner, 250, "FINISH BONUS", (0, 2)))


@dataclass
class BattleRecord:
    wins: int = 0
    losses: int = 0
    draws: int = 0
    total_points: int = 0
    best: int = 0
    streak: int = 0

    @property
    def rank(self):
        return "CRUCIBLE ACE" if self.total_points >= 2000 else "ARENA ENGINEER" if self.total_points >= 750 else "SCRAP FIGHTER" if self.total_points >= 250 else "ROOKIE BUILDER"

    def complete(self, winner, points):
        self.total_points += points
        self.best = max(self.best, points)
        if winner == 0:
            self.wins += 1
            self.streak += 1
        else:
            self.streak = 0
            if winner == 1:
                self.losses += 1
            else:
                self.draws += 1

    @classmethod
    def load(cls, root):
        try:
            data = json.loads((root / "session" / "arena.json").read_text(encoding="utf-8"))
            record = cls(**data)
            if any(type(v) is not int or not 0 <= v <= 10**12 for v in asdict(record).values()):
                raise ValueError("Invalid battle record")
            return record
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, root):
        folder = root / "session"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "arena.json"
        temp = path.with_suffix(".json.tmp")
        temp.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        temp.replace(path)
