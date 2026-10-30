"""Exercise real pygame events through the application, using a dummy display."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import tempfile
import unittest
from pathlib import Path
import pygame as pg
import scraplab.app as app_module
from scraplab.app import App
from scraplab.blueprint import preset, load


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_root = app_module.ROOT
        app_module.ROOT = Path(self.temp.name)
        (app_module.ROOT / "saves").mkdir()
        (app_module.ROOT / "examples").mkdir()
        self.app = App(intro=False)

    def tearDown(self):
        pg.quit()
        app_module.ROOT = self.old_root
        self.temp.cleanup()

    def click(self, pos):
        self.app.event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=pos))
        self.app.event(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=pos))
        self.app.render()

    def key(self, key, mod=0):
        self.app.event(pg.event.Event(pg.KEYDOWN, key=key, mod=mod))
        self.app.event(pg.event.Event(pg.KEYUP, key=key, mod=mod))
        self.app.render()

    def test_palette_drag_rotate_duplicate_and_undo_via_events(self):
        app = self.app
        self.click((600, 116))  # Examples
        self.assertEqual(app.modal, "examples")
        self.click((330, 565))  # Blank
        self.assertEqual(len(app.editor.blueprint.parts), 0)
        app.event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(112, 207)))
        app.event(pg.event.Event(pg.MOUSEMOTION, pos=(625, 609), rel=(513, 402), buttons=(1, 0, 0)))
        app.event(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=(625, 609)))
        self.assertEqual(len(app.editor.blueprint.parts), 1)
        self.key(pg.K_r)
        self.assertEqual(app.editor.part.angle, 15)
        self.key(pg.K_d, pg.KMOD_CTRL)
        self.assertEqual(len(app.editor.blueprint.parts), 2)
        self.key(pg.K_DELETE)
        self.assertEqual(len(app.editor.blueprint.parts), 1)
        self.key(pg.K_z, pg.KMOD_CTRL)
        self.assertEqual(len(app.editor.blueprint.parts), 2)

    def test_save_and_load_dialog_preserves_edited_part(self):
        app = self.app
        app.editor.selected = app.editor.blueprint.parts[-1].uid
        app.editor.change("y", .4)
        self.key(pg.K_s, pg.KMOD_CTRL)
        self.key(pg.K_a, pg.KMOD_CTRL)
        app.event(pg.event.Event(pg.TEXTINPUT, text="GUI test robot"))
        self.key(pg.K_RETURN)
        self.assertIsNone(app.modal)
        self.assertAlmostEqual(load(app_module.ROOT / "saves/GUI_test_robot.json").parts[-1].y, .4)
        app.editor.replace(preset("Blank"))
        self.key(pg.K_o, pg.KMOD_CTRL)
        self.click((500, 270))
        self.assertAlmostEqual(app.editor.blueprint.parts[-1].y, .4)

    def test_pause_step_reset_and_edit_transitions(self):
        app = self.app
        original = app.editor.blueprint.to_dict()
        for _ in range(5):
            self.key(pg.K_F5)
            app.update(.05)
            self.key(pg.K_SPACE)
            elapsed = app.sim.time
            app.update(.05)
            self.assertAlmostEqual(app.sim.time, elapsed)
            self.key(pg.K_PERIOD)
            self.assertAlmostEqual(app.sim.time, elapsed+app.sim.dt)
            self.key(pg.K_r)
            self.assertEqual(app.sim.time, 0)
            self.key(pg.K_ESCAPE)
            self.assertEqual(app.mode, "workshop")
        self.assertEqual(original, app.editor.blueprint.to_dict())

    def test_all_screens_render_and_small_window_maps_input(self):
        app = self.app
        for modal in ("intro", "examples", "save", "load", "notes", None):
            app.modal = modal
            app.render()
        for scenario in ("test", "benchmark", "arena"):
            app.start(scenario)
            app.update(.05)
            app.engineering = True
            app.render()
            app.modal = "notes"
            app.render()
            app.modal = None
        app.workshop()
        app.event(pg.event.Event(pg.VIDEORESIZE, w=960, h=600))
        self.assertEqual(app.logical((480, 300)), (640, 400))
        app.render()
        app.present()

    def test_corrupt_save_is_reported_without_crash(self):
        path = app_module.ROOT / "saves/broken.json"
        path.write_text("{broken", encoding="utf-8")
        self.app.load_file(path)
        self.assertIn("Could not load", self.app.notice)
        self.assertEqual(len(self.app.editor.blueprint.parts), 5)

    def test_keyboard_and_arrow_keys_actually_operate_player_arm(self):
        app = self.app
        app.editor.replace(preset("Forklift"))
        app.start("practice")
        motor = next(m for p, m in app.sim.robot.motors if p.kind == "arm")
        app.event(pg.event.Event(pg.KEYDOWN, key=pg.K_UP, mod=0))
        for _ in range(60):
            app.update(1/60)
        self.assertGreater(motor.b.angle-motor.a.angle, .7)
        app.event(pg.event.Event(pg.KEYUP, key=pg.K_UP, mod=0))
        self.assertEqual(app.controls()["arm"], 0)
        app.event(pg.event.Event(pg.KEYDOWN, key=pg.K_q, mod=0))
        for _ in range(120):
            app.update(1/60)
        app.event(pg.event.Event(pg.KEYUP, key=pg.K_q, mod=0))
        self.assertLess(motor.b.angle-motor.a.angle, 0)
        self.assertTrue(app.sim.telemetry.complete)

    def test_mouse_hold_operates_arm_and_release_stops_command(self):
        app = self.app
        app.editor.replace(preset("Forklift"))
        app.start("practice")
        app.render()
        app.event(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=(1085, 676)))
        self.assertEqual(app.controls()["arm"], -1)
        for _ in range(30):
            app.update(1/60)
        motor = next(m for p, m in app.sim.robot.motors if p.kind == "arm")
        self.assertGreater(motor.b.angle-motor.a.angle, .3)
        app.event(pg.event.Event(pg.MOUSEBUTTONUP, button=1, pos=(1085, 676)))
        self.assertEqual(app.controls()["arm"], 0)

    def test_quick_click_nudges_without_latching_the_arm(self):
        app = self.app
        app.editor.replace(preset("Forklift"))
        app.start("practice")
        app.render()
        self.click((1085, 676))
        for _ in range(30):
            app.update(1/60)
        motor = next(m for p, m in app.sim.robot.motors if p.kind == "arm")
        self.assertGreater(motor.b.angle-motor.a.angle, .06)
        self.assertEqual(app.controls()["arm"], 0)

    def test_losing_focus_pauses_and_clears_motor_commands(self):
        app = self.app
        app.start("test")
        app.event(pg.event.Event(pg.KEYDOWN, key=pg.K_d, mod=0))
        app.event(pg.event.Event(pg.WINDOWFOCUSLOST))
        elapsed = app.sim.time
        app.update(.1)
        self.assertEqual(app.sim.time, elapsed)
        self.assertEqual(app.controls(), {"drive": 0, "arm": 0})
        self.assertTrue(app.paused)

    def test_recovery_survives_reopening(self):
        app = self.app
        app.editor.selected = app.editor.blueprint.parts[-1].uid
        app.editor.change("y", .7)
        app.update(3.1)
        restored = App(intro=False)
        self.assertTrue(restored.recovered)
        self.assertEqual(restored.editor.blueprint.to_dict(), app.editor.blueprint.to_dict())

    def test_preview_does_not_replace_existing_recovery(self):
        self.app.recovery_save(force=True)
        path = app_module.ROOT / "session/recovery.json"
        before = path.read_bytes()
        preview = App(intro=False, persist=False)
        preview.editor.replace(preset("Forklift"))
        preview.start("practice")
        preview.recovery_save(force=True)
        self.assertEqual(path.read_bytes(), before)

    def test_opening_notebook_clears_held_inputs(self):
        app = self.app
        app.start("test")
        app.keys.add(pg.K_d)
        app.show_modal("notes")
        self.assertEqual(app.controls()["drive"], 0)

    def test_benchmark_mouse_controls_are_visibly_disabled(self):
        app = self.app
        app.editor.replace(preset("Forklift"))
        app.start("benchmark")
        app.render()
        self.assertTrue(app.hold_buttons)
        self.assertTrue(all(not b[3] for b in app.hold_buttons))


if __name__ == "__main__":
    unittest.main()
