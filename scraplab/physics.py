"""SI-unit rigid body construction. Rendering never drives physical bodies."""
from dataclasses import dataclass
import math
import pymunk as pm
from .parts import CATALOG, WEAPONS, mass, centroid, vertices, dimensions, anchor
from .battle import BattleScore
from .blueprint import validate, preset
from .scenarios import RAMP, BENCHMARK_SECONDS, benchmark_controls, opponent_controls
from .telemetry import Telemetry

DT = 1/240  # Four substeps per 60 Hz frame, independent of render frequency.
GRAVITY = -9.81


@dataclass
class Visual:
    part: object
    body: pm.Body
    shape: pm.Shape


class Robot:
    def __init__(self, space, bp, offset=(0, 0), group=1):
        errors = validate(bp)
        if errors:
            raise ValueError(errors[0][1])
        self.blueprint = bp.clone()
        rigid = [p for p in bp.parts if CATALOG[p.kind].joint == "weld"]
        total = sum(mass(p) for p in rigid)
        center = pm.Vec2d(*(sum(mass(p)*centroid(p)[i] for p in rigid)/total for i in (0, 1)))
        inertia = 0
        for p in rigid:
            verts = [pm.Vec2d(*v)-center for v in vertices(p)]
            inertia += pm.moment_for_poly(mass(p), verts)
        self.body = pm.Body(total, inertia)
        self.body.position = center+offset
        space.add(self.body)
        self.bodies = [self.body]
        self.visuals, self.motors, self.joints = [], [], []
        self.power_budget = sum(120 for p in rigid if p.kind == "battery")
        self.last_controls = {}
        for p in rigid:
            shape = pm.Poly(self.body, [pm.Vec2d(*v)-center for v in vertices(p)])
            self._add_shape(space, p, shape, group)
        for p in bp.parts:
            joint = CATALOG[p.kind].joint
            if joint == "weld":
                continue
            pos = pm.Vec2d(p.x, p.y)
            if joint == "axle":
                radius = dimensions(p)[0]/2
                inertia = pm.moment_for_circle(mass(p), 0, radius)
            else:
                verts = [pm.Vec2d(*v)-pos for v in vertices(p)]
                inertia = pm.moment_for_poly(mass(p), verts)
            body = pm.Body(mass(p), inertia)
            body.position = pos+offset
            space.add(body)
            self.bodies.append(body)
            shape = pm.Circle(body, radius) if joint == "axle" else pm.Poly(body, verts)
            self._add_shape(space, p, shape, group)
            pivot_world = pm.Vec2d(*anchor(p))+offset
            pivot = pm.PivotJoint(self.body, body, pivot_world)
            pivot.collide_bodies = False
            space.add(pivot)
            self.joints.append((p, pivot))
            if joint in ("motor", "pivot"):
                limit = pm.RotaryLimitJoint(self.body, body, math.radians(-65), math.radians(100))
                space.add(limit)
            if joint in ("axle", "motor", "rotor"):
                motor = pm.SimpleMotor(self.body, body, 0)
                motor.max_force = 0
                space.add(motor)
                self.motors.append((p, motor))

    def _add_shape(self, space, part, shape, group):
        shape.friction = CATALOG[part.kind].friction*part.grip
        shape.elasticity = .02
        shape.filter = pm.ShapeFilter(group=group)
        shape.collision_type = group
        space.add(shape)
        self.visuals.append(Visual(part, shape.body, shape))

    @property
    def com(self):
        total = sum(b.mass for b in self.bodies)
        return sum((b.position*b.mass for b in self.bodies), pm.Vec2d(0, 0))/total

    def control(self, controls):
        self.last_controls = dict(controls)
        requested = sum(p.torque for p, _ in self.motors if p.control != "off")
        scale = min(1, self.power_budget/requested) if requested else 0
        for part, motor in self.motors:
            command = controls.get(part.control, 0)
            # SimpleMotor rate is omega(a)-omega(b); positive spins wheel clockwise.
            motor.rate = part.speed*command*part.direction
            motor.max_force = part.torque*scale if part.control != "off" else 0
            # A zero command brakes. This is a torque-limited motor brake.


class Simulation:
    dt = DT

    def __init__(self, bp, scenario="test", airborne=False, opponent_name="Copperhead"):
        self.blueprint = bp.clone()
        self.scenario = scenario
        self.space = pm.Space()
        self.space.gravity = (0, GRAVITY)
        self.space.iterations = 40
        self.space.collision_slop = .005
        self.time, self.accumulator = 0.0, 0.0
        self.contacts, self.impacts = [], []
        self.terrain, self.props = [], []
        self.result = ""
        self.result_reason = ""
        self.practice_raised = False
        self.practice_lowered = False
        self.knockout = [0., 0.]
        self.opponent = None
        self.opponent_name = opponent_name
        self.ai_probe_time, self.ai_probe_x, self.ai_backoff_until = 2., 3., 0.
        self.battle = BattleScore()
        self.winner = None
        self._incoming = {}
        self._weapon_shapes = set()
        self.space.on_collision(None, None, pre_solve=self._before_collision, post_solve=self._collision)
        if scenario == "arena":
            self.segment((-6, 0), (6, 0), .08)
        elif scenario == "practice":
            self.segment((-14, 0), (20, 0))
            self.box((3.2, .25), (.45, .45), 1)
        else:
            self.segment((-18, 0), (4, 0))
            for a, b in zip(RAMP, RAMP[1:]):
                self.segment(a, b)
            self.segment((13, 2.35), (18, 0))
            self.segment((18, 0), (35, 0))
            self.segment((-7, 0), (-6.7, .22), .04)
            self.segment((-6.7, .22), (-6.2, .22), .04)
            self.box((-4.5, .45), (.65, .65), 8)
            self.box((-3.5, .30), (.4, .4), 3)
        bottom = min(p.y-dimensions(p)[0]/2 if CATALOG[p.kind].joint == "axle" else min(v[1] for v in vertices(p)) for p in bp.parts) if bp.parts else 0
        x = -3 if scenario == "arena" else 0
        self.robot = Robot(self.space, bp, (x, -bottom+.09+(20 if airborne else 0)), 1)
        if scenario == "arena":
            rival = preset(opponent_name)
            # Mirror all blueprint geometry, retaining identical mechanics.
            for p in rival.parts:
                p.x = -p.x
                if p.kind in {"wedge", "arm", "pivot", "flipper"}:
                    p.angle = 180-p.angle
            self.opponent = Robot(self.space, rival, (3, .65), 2)
            self._weapon_shapes = {v.shape for robot in (self.robot, self.opponent) for v in robot.visuals if v.part.kind in WEAPONS}
        self.telemetry = Telemetry(bp.name, scenario, self.robot.com.x)

    def segment(self, a, b, radius=.035):
        shape = pm.Segment(self.space.static_body, a, b, radius)
        shape.friction = 1.0
        shape.elasticity = .01
        self.space.add(shape)
        self.terrain.append(shape)

    def box(self, position, size, weight):
        body = pm.Body(weight, pm.moment_for_box(weight, size))
        body.position = position
        shape = pm.Poly.create_box(body, size)
        shape.friction = .65
        self.space.add(body, shape)
        self.props.append((shape, weight))

    def _before_collision(self, arbiter, space, data):
        a, b = arbiter.shapes
        if self.scenario != "arena" or {a.collision_type, b.collision_type} != {1, 2} or not arbiter.is_first_contact:
            return
        points = arbiter.contact_point_set.points
        if not points:
            return
        point = (points[0].point_a+points[0].point_b)/2
        velocities = []
        for shape in (a, b):
            radius = point-shape.body.position
            velocities.append(shape.body.velocity + pm.Vec2d(-radius.y, radius.x)*shape.body.angular_velocity)
        normal = arbiter.normal
        approach = (velocities[0]-velocities[1]).dot(normal)
        contributions = [max(0, velocities[0].dot(normal)), max(0, -velocities[1].dot(normal))]
        self._incoming[(a, b)] = (approach, contributions)

    def _collision(self, arbiter, space, data):
        impulse = arbiter.total_impulse.length
        points = arbiter.contact_point_set.points
        if points:
            pos = (points[0].point_a+points[0].point_b)/2
            if impulse > .02 and len(self.contacts) < 100:
                self.contacts.append((pos, impulse/self.dt))
            if arbiter.is_first_contact and impulse > 2:
                self.impacts.append((self.time, pos, min(impulse, 60)))
            incoming = self._incoming.pop(tuple(arbiter.shapes), None)
            if incoming:
                approach, contributions = incoming
                for i, shape in enumerate(arbiter.shapes):
                    if contributions[i] >= .4 and contributions[i] >= max(contributions)*.85:
                        self.battle.impact(self.time, shape.collision_type-1, impulse, approach,
                                           shape in self._weapon_shapes, pos)

    def step(self, controls=None):
        if self.result:
            return
        self.contacts = []
        self._incoming.clear()
        controls = controls or {"drive": 0, "arm": 0}
        if self.scenario == "benchmark":
            controls = benchmark_controls(self.time)
        if self.scenario == "arena" and self.time < 2:
            controls = {"drive": 0, "arm": 0}
        self.robot.control(controls)
        if self.opponent:
            self.opponent.control(opponent_controls(self) if self.time >= 2 else {})
        self.space.step(self.dt)
        self.time += self.dt
        self.telemetry.update(self)
        if self.scenario == "practice":
            self._practice_progress()
        self.impacts = [p for p in self.impacts if self.time-p[0] < .45][-40:]
        if self.scenario == "benchmark" and self.time >= BENCHMARK_SECONDS-1e-8:
            self.result = "SUMMIT REACHED" if self.telemetry.complete else "TEST RECORDED"
            self.result_reason = "The 12-second control sequence is complete. Compare the measurements, then revise your design."
        if self.opponent:
            self._arena_result()

    def advance(self, elapsed, controls=None):
        # Cap wall-clock stalls: lose real time instead of making huge physics steps.
        self.accumulator += min(max(elapsed, 0), .10)
        while self.accumulator >= self.dt-1e-10:
            self.step(controls)
            self.accumulator -= self.dt

    def _arena_result(self):
        if self.time < 2:
            return
        losses = []
        for i, robot in enumerate((self.robot, self.opponent)):
            tilt = abs(math.atan2(math.sin(robot.body.angle), math.cos(robot.body.angle)))
            self.knockout[i] = self.knockout[i]+self.dt if tilt > math.radians(100) else 0
            losses.append(robot.com.y < -2 or self.knockout[i] >= 3)
        if all(losses):
            self.result = "DRAW / DOUBLE KNOCKOUT"
            self.result_reason = "Both robots met the loss condition on the same physics step."
        elif losses[0]:
            self.winner = 1
            self.result = self.opponent_name.upper() + " WINS"
            self.result_reason = "Your robot fell below the arena." if self.robot.com.y < -2 else "Your chassis stayed overturned for 3 seconds."
        elif losses[1]:
            self.winner = 0
            self.result = "YOU WIN"
            self.result_reason = f"{self.opponent_name} fell below the arena." if self.opponent.com.y < -2 else f"{self.opponent_name} stayed overturned for 3 seconds."
        elif self.time >= 47:
            a, b = self.battle.points
            self.winner = 0 if a > b else 1 if b > a else None
            self.result = "YOU WIN" if a > b else self.opponent_name.upper()+" WINS" if b > a else "DRAW / LEVEL ON POINTS"
            self.result_reason = f"Time! Impact points decide the match: {a} to {b}."
        if self.result:
            self.battle.finish(self.winner, self.time, knockout=any(losses))

    def _practice_progress(self):
        arms = [(p, m) for p, m in self.robot.motors if p.kind in WEAPONS]
        if not arms or self.telemetry.complete:
            return
        _, motor = arms[0]
        angle = math.degrees(motor.b.angle-motor.a.angle)
        if angle >= 45:
            self.practice_raised = True
        if angle <= -25:
            self.practice_lowered = True
        if self.practice_raised and self.practice_lowered:
            self.telemetry.complete = True
            self.telemetry.events.append(f"{self.time:.2f}s: arm crossed both +45 and -25 degree practice markers.")
