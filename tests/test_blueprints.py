import json
import math
import tempfile
import unittest
from pathlib import Path
from scraplab.blueprint import Blueprint, Part, preset, validate, save, load, safe_name
from scraplab.editor import Editor
from scraplab.parts import mass


class BlueprintTests(unittest.TestCase):
    def test_round_trip_keeps_every_construction_setting(self):
        bp = preset("Forklift")
        bp.parts[1].direction = -1
        bp.parts[1].grip = 1.7
        bp.parts[-1].torque = 75
        with tempfile.TemporaryDirectory() as tmp:
            path = save(bp, tmp)
            self.assertEqual(load(path).to_dict(), bp.to_dict())

    def test_moving_only_heavy_part_changes_mass_weighted_com(self):
        high = preset("Tall order")
        low = high.clone()
        battery = next(p for p in low.parts if p.kind == "battery")
        old = battery.y
        battery.y = .38
        self.assertAlmostEqual(high.total_mass, low.total_mass)
        expected = mass(battery)*(old-battery.y)/high.total_mass
        self.assertAlmostEqual(high.com[1]-low.com[1], expected)
        self.assertGreater(expected, 1.5)

    def test_examples_are_valid(self):
        for name in ("Tall order", "Low rider", "Forklift"):
            self.assertEqual(validate(preset(name)), [])

    def test_unattached_axle_is_actionable(self):
        bp = preset("Low rider")
        bp.parts[2].x = 5
        self.assertTrue(any("pivot" in e[1].lower() for e in validate(bp)))

    def test_overlapping_wheels_rejected_mount_overlap_allowed(self):
        bp = preset("Low rider")
        self.assertFalse(validate(bp))
        bp.parts[2].x = bp.parts[3].x
        self.assertTrue(any("Wheels overlap" in e[1] for e in validate(bp)))

    def test_battery_intersections_rejected(self):
        bp = preset("Low rider")
        bp.parts.append(Part("ballast", 0, .38))
        self.assertTrue(any("Blocks intersect" in e[1] for e in validate(bp)))

    def test_corrupt_data_rejected_before_physics(self):
        for field, value in [("x", float("nan")), ("scale", 0), ("kind", "rocket"), ("torque", 999), ("material", ["steel"]), ("speed", True)]:
            data = preset().to_dict()
            data["parts"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                Blueprint.from_dict(data)
        data = preset().to_dict()
        data["schema_version"] = 999
        with self.assertRaises(ValueError):
            Blueprint.from_dict(data)

    def test_duplicate_identifiers_rejected(self):
        data = preset().to_dict()
        data["parts"][1]["uid"] = data["parts"][0]["uid"]
        with self.assertRaises(ValueError):
            Blueprint.from_dict(data)

    def test_save_name_cannot_escape_folder(self):
        self.assertNotIn("/", safe_name("../../outside"))
        self.assertNotEqual(safe_name("CON"), "CON")

    def test_editor_changes_are_undoable(self):
        ed = Editor(preset("Low rider"))
        original = ed.blueprint.to_dict()
        ed.selected = ed.blueprint.parts[-1].uid
        ed.change("y", 2.4)
        ed.undo()
        self.assertEqual(ed.blueprint.to_dict(), original)
        ed.redo()
        self.assertAlmostEqual(ed.blueprint.parts[-1].y, 2.4)

    def test_palette_drop_outside_does_not_leave_stray_part(self):
        ed = Editor(preset())
        original = ed.blueprint.to_dict()
        ed.begin_new("arm", (3, 3))
        ed.drop(False)
        self.assertEqual(ed.blueprint.to_dict(), original)


if __name__ == "__main__":
    unittest.main()
