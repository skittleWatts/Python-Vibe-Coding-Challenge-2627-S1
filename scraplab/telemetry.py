"""Measured events, not generated diagnoses."""
from dataclasses import dataclass, field, asdict
from math import degrees, atan2, sin, cos


@dataclass
class Telemetry:
    name: str
    scenario: str
    start_x: float
    elapsed: float = 0
    distance: float = 0
    max_tilt: float = 0
    max_motor_torque: float = 0
    tipped: bool = False
    complete: bool = False
    samples: list = field(default_factory=list)
    events: list = field(default_factory=list)

    def update(self, sim):
        self.elapsed = sim.time
        self.distance = sim.robot.com.x-self.start_x
        tilt = abs(degrees(atan2(sin(sim.robot.body.angle), cos(sim.robot.body.angle))))
        self.max_tilt = max(self.max_tilt, tilt)
        self.max_motor_torque = max([self.max_motor_torque]+[m.impulse/sim.dt for _, m in sim.robot.motors])
        if tilt > 65 and not self.tipped:
            self.tipped = True
            self.events.append(f"{sim.time:.2f}s: chassis rotated past 65 degrees.")
        if sim.scenario in {"test", "benchmark"} and sim.robot.com.x > 10.2 and sim.robot.com.y > 2.3 and tilt < 45 and not self.complete:
            self.complete = True
            self.events.append(f"{sim.time:.2f}s: summit gate crossed upright.")
        if len(self.samples) < 4000 and (not self.samples or sim.time-self.samples[-1][0] >= .08):
            self.samples.append([round(sim.time, 3), round(self.distance, 4), round(tilt, 3)])

    def to_dict(self):
        return asdict(self)
