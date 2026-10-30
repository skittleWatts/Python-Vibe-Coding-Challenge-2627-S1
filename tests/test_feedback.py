import unittest
from scraplab.blueprint import preset
from scraplab.physics import Simulation
from scraplab.feedback import arm_feedback


class FeedbackTests(unittest.TestCase):
    def test_unpowered_arm_is_explained(self):
        bp = preset("Forklift")
        bp.parts = [p for p in bp.parts if p.kind != "battery"]
        sim = Simulation(bp, "practice")
        sim.step({"arm": -1})
        self.assertEqual(arm_feedback(sim.robot, sim.dt, {"arm": -1})["title"], "NO BATTERY")

    def test_drive_assignment_is_explained(self):
        bp = preset("Forklift")
        next(p for p in bp.parts if p.kind == "arm").control = "drive"
        sim = Simulation(bp, "practice")
        self.assertEqual(arm_feedback(sim.robot, sim.dt, {})["title"], "LINKED TO DRIVE")

    def test_joint_stop_is_measured(self):
        sim = Simulation(preset("Forklift"), "practice")
        for _ in range(600):
            sim.step({"arm": -1})
        self.assertEqual(arm_feedback(sim.robot, sim.dt, {"arm": -1})["title"], "AT JOINT LIMIT")

    def test_practice_goal_requires_both_actual_angles(self):
        sim = Simulation(preset("Forklift"), "practice")
        for _ in range(300):
            sim.step({"arm": -1})
        self.assertTrue(sim.practice_raised)
        self.assertFalse(sim.telemetry.complete)
        for _ in range(700):
            sim.step({"arm": 1})
        self.assertTrue(sim.practice_lowered)
        self.assertTrue(sim.telemetry.complete)


if __name__ == "__main__":
    unittest.main()
