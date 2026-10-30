import math
import unittest
from scraplab.blueprint import preset, Blueprint
from scraplab.physics import Simulation, DT


def benchmark(bp):
    sim = Simulation(bp, "benchmark")
    for _ in range(round(12/DT)):
        sim.step()
    return sim


class PhysicsTests(unittest.TestCase):
    def test_signature_experiment_is_real_and_repeatable(self):
        high = preset("Tall order")
        low = high.clone()
        next(p for p in low.parts if p.kind == "battery").y = .38
        a, b = benchmark(high), benchmark(low)
        self.assertTrue(a.telemetry.tipped)
        self.assertFalse(a.telemetry.complete)
        self.assertFalse(b.telemetry.tipped)
        self.assertTrue(b.telemetry.complete)
        self.assertGreater(b.telemetry.distance-a.telemetry.distance, 10)
        again = benchmark(low)
        self.assertAlmostEqual(b.telemetry.distance, again.telemetry.distance, places=8)

    def test_ground_contact_is_needed_for_propulsion(self):
        bp = preset("Low rider")
        grounded, airborne = Simulation(bp), Simulation(bp, airborne=True)
        gx, ax = grounded.robot.com.x, airborne.robot.com.x
        for _ in range(360):
            grounded.step({"drive": 1})
            airborne.step({"drive": 1})
        self.assertGreater(grounded.robot.com.x-gx, 1)
        self.assertAlmostEqual(airborne.robot.com.x, ax, places=7)
        self.assertAlmostEqual(sum(b.mass*b.velocity.x for b in airborne.robot.bodies), 0, places=6)

    def test_motor_torque_and_battery_budget_are_bounded(self):
        bp = preset("Low rider")
        for p in bp.parts:
            if p.kind == "wheel":
                p.torque = 100
        sim = Simulation(bp)
        for _ in range(480):
            sim.step({"drive": 1})
            for _, motor in sim.robot.motors:
                self.assertLessEqual(motor.impulse/DT, motor.max_force+1e-6)
            self.assertLessEqual(sum(m.max_force for _, m in sim.robot.motors), 120+1e-6)

    def test_airborne_motors_exert_reaction_torque(self):
        sim = Simulation(preset("Low rider"), airborne=True)
        for _ in range(60):
            sim.step({"drive": 1})
        self.assertGreater(abs(sim.robot.body.angular_velocity), .02)
        self.assertLess(sim.robot.motors[0][1].b.angular_velocity*sim.robot.body.angular_velocity, 0)

    def test_no_battery_disables_motors(self):
        bp = preset("Low rider")
        bp.parts = [p for p in bp.parts if p.kind != "battery"]
        sim = Simulation(bp)
        for _ in range(60):
            sim.step({"drive": 1})
        self.assertTrue(all(m.max_force == 0 for _, m in sim.robot.motors))

    def test_render_framerate_does_not_change_fixed_step_result(self):
        positions = []
        for fps in (30, 60, 144):
            sim = Simulation(preset("Low rider"), "benchmark")
            for _ in range(fps*12):
                sim.advance(1/fps)
            positions.append(sim.robot.com)
        for pos in positions[1:]:
            self.assertLess((pos-positions[0]).length, 1e-7)

    def test_reset_and_reconstruction_preserve_blueprint(self):
        bp = preset("Forklift")
        original = bp.to_dict()
        initial = Simulation(bp).robot.com
        for _ in range(10):
            sim = Simulation(bp)
            self.assertLess((sim.robot.com-initial).length, 1e-9)
            for _ in range(200):
                sim.step({"drive": 1, "arm": -1})
            self.assertTrue(all(math.isfinite(b.position.x) and math.isfinite(b.angle) for b in sim.robot.bodies))
        self.assertEqual(bp.to_dict(), original)

    def test_arm_pivot_moves_and_has_limits(self):
        sim = Simulation(preset("Forklift"))
        arm, motor = next((p, m) for p, m in sim.robot.motors if p.kind == "arm")
        for _ in range(720):
            sim.step({"arm": -1})
        relative = motor.b.angle-motor.a.angle
        self.assertGreater(relative, .1)
        self.assertLess(relative, math.radians(102))

    def test_invalid_builds_do_not_enter_solver(self):
        with self.assertRaises(ValueError):
            Simulation(Blueprint())
        bp = preset()
        bp.parts[2].x = 6
        with self.assertRaises(ValueError):
            Simulation(bp)

    def test_arena_uses_same_motor_limits_and_ringout_rule(self):
        sim = Simulation(preset("Low rider"), "arena")
        for _ in range(600):
            sim.step({"drive": 1})
        for robot in (sim.robot, sim.opponent):
            for part, motor in robot.motors:
                self.assertLessEqual(motor.impulse/DT, part.torque+1e-6)
        # Explicit rule-unit test: put a robot below the arena floor.
        for body in sim.opponent.bodies:
            body.position += (0, -10)
        sim.step()
        self.assertEqual(sim.result, "YOU WIN")


if __name__ == "__main__":
    unittest.main()
