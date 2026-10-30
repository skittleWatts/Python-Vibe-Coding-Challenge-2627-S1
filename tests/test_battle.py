import math
import tempfile
import unittest
from pathlib import Path
from scraplab.battle import BattleScore, BattleRecord
from scraplab.blueprint import preset, validate, Blueprint
from scraplab.physics import Simulation, DT


class BattleTests(unittest.TestCase):
    def test_weapon_builds_save_and_mount_for_both_sides(self):
        for name in ("Whirlwind", "Kickback"):
            bp = preset(name)
            self.assertEqual(validate(bp), [])
            self.assertEqual(Blueprint.from_dict(bp.to_dict()).to_dict(), bp.to_dict())
            sim = Simulation(bp, "arena", opponent_name=name)
            self.assertEqual(validate(sim.opponent.blueprint), [])
            self.assertEqual(sim.robot.power_budget, sim.opponent.power_budget)

    def test_spinner_makes_full_turns_with_real_torque_and_reaction(self):
        sim = Simulation(preset("Whirlwind"), airborne=True)
        motor = next(m for p, m in sim.robot.motors if p.kind == "spinner")
        for _ in range(360):
            sim.step({"arm": -1})
            self.assertLessEqual(motor.impulse/DT, motor.max_force+1e-6)
            self.assertLessEqual(sum(m.max_force for _, m in sim.robot.motors), 120+1e-6)
        self.assertGreater(motor.b.angle-motor.a.angle, math.tau)
        self.assertLess(sim.robot.body.angular_velocity, 0)
        self.assertAlmostEqual(sum(b.mass*b.velocity.x for b in sim.robot.bodies), 0, places=5)

    def test_flipper_has_stops_and_reverses(self):
        sim = Simulation(preset("Kickback"), "practice")
        motor = next(m for p, m in sim.robot.motors if p.kind == "flipper")
        for _ in range(480):
            sim.step({"arm": -1})
        self.assertGreater(motor.b.angle-motor.a.angle, .7)
        self.assertLess(motor.b.angle-motor.a.angle, math.radians(102))
        for _ in range(480):
            sim.step({"arm": 1})
        self.assertLess(motor.b.angle-motor.a.angle, 0)

    def test_real_robot_contact_scores_without_health_or_force_changes(self):
        sim = Simulation(preset("Whirlwind"), "arena")
        for _ in range(240*8):
            sim.step({"drive": 1, "arm": -1})
        hits = [event for event in sim.battle.events if event[3] in {"RAM", "WEAPON HIT"}]
        self.assertTrue(hits)
        self.assertTrue(any(e[3] == "WEAPON HIT" for e in hits))
        self.assertTrue(all(e[0] >= 2 for e in hits))

    def test_floor_bumps_do_not_award_arena_points(self):
        sim = Simulation(preset("Whirlwind"), "arena")
        for body in sim.opponent.bodies:
            body.position += (15, 100)
        for _ in range(240*3):
            sim.step({"arm": -1})
        self.assertEqual(sim.battle.points, [0, 0])

    def test_each_rival_can_approach_without_grounding_its_weapon(self):
        for name in ("Copperhead", "Whirlwind", "Kickback"):
            sim = Simulation(preset("Whirlwind"), "arena", opponent_name=name)
            initial = sim.opponent.com.x
            for _ in range(240*6):
                sim.step({})
            self.assertGreater(initial-sim.opponent.com.x, 2, name)

    def test_scoring_rejects_settling_and_duplicate_contacts(self):
        score = BattleScore()
        self.assertEqual(score.impact(1, 0, 30, 3, True, (0, 0)), 0)
        self.assertEqual(score.impact(3, 0, 30, .1, True, (0, 0)), 0)
        self.assertEqual(score.impact(3, 0, 1, 3, True, (0, 0)), 0)
        first = score.impact(3, 0, 30, 3, True, (0, 0))
        self.assertGreater(first, 0)
        self.assertEqual(score.impact(3.1, 0, 30, 3, True, (0, 0)), 0)
        self.assertEqual(score.points, [first, 0])
        self.assertGreater(score.impact(4, 1, 30, 3, True, (0, 0)), 0)

    def test_ringout_bonus_once_and_time_limit_judges_points(self):
        sim = Simulation(preset("Forklift"), "arena")
        sim.time = 3
        for body in sim.opponent.bodies:
            body.position += (0, -10)
        sim.step()
        self.assertEqual(sim.winner, 0)
        self.assertEqual(sim.battle.points, [250, 0])
        sim.step()
        self.assertEqual(sim.battle.points, [250, 0])
        for points, winner in (([50, 20], 0), ([10, 20], 1), ([20, 20], None)):
            sim = Simulation(preset("Forklift"), "arena")
            sim.time = 47
            sim.battle.points = points.copy()
            sim._arena_result()
            self.assertEqual(sim.winner, winner)
            self.assertTrue(sim.result)
            self.assertEqual(sim.battle.points, points)

    def test_record_persists_and_corruption_is_recoverable(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = BattleRecord()
            record.complete(0, 300)
            record.complete(0, 400)
            record.save(root)
            restored = BattleRecord.load(root)
            self.assertEqual((restored.wins, restored.streak, restored.best, restored.total_points), (2, 2, 400, 700))
            restored.complete(1, 20)
            self.assertEqual(restored.streak, 0)
            (root / "session/arena.json").write_text('{"wins": "broken"}', encoding="utf-8")
            self.assertEqual(BattleRecord.load(root).wins, 0)
