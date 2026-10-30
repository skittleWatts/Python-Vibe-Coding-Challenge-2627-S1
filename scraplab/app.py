"""Pygame application: straightforward event loop and explicit screen states."""
from pathlib import Path
import csv
import json
import math
import time
import pygame as pg
from .blueprint import preset, validate, save, load, Blueprint
from .parts import CATALOG, MATERIALS, mass, dimensions, anchor
from .editor import Editor
from .physics import Simulation
from .scenarios import BENCHMARK_SECONDS
from .feedback import arm_feedback
from .storage import recover, store_recovery, store_preferences, sound_preference
from .audio import Audio
from .render import (Painter, Camera, grid, draw_part, scenery, draw_robot, impacts,
                     BG, PANEL, PANEL2, LINE, INK, MUTED, TEAL, GOLD, RED, PURPLE)

ROOT = Path(__file__).resolve().parent.parent
SIZE = (1280, 800)


class App:
    def __init__(self, intro=True, size=(1280, 800), persist=True):
        pg.display.init()
        pg.font.init()  # Audio is optional; no mixer initialization required.
        self.window = pg.display.set_mode(size, pg.RESIZABLE)
        pg.display.set_caption("ScrapLab 1.1: Build. Break. Understand.")
        icon = pg.Surface((32, 32), pg.SRCALPHA)
        pg.draw.rect(icon, TEAL, (3, 8, 26, 16), border_radius=4)
        pg.draw.circle(icon, GOLD, (8, 24), 5)
        pg.draw.circle(icon, GOLD, (24, 24), 5)
        pg.display.set_icon(icon)
        self.surface = pg.Surface(SIZE)
        self.p = Painter(self.surface)
        self.persist = persist
        recovered, recovery_error = recover(ROOT) if persist else (None, "")
        self.editor = Editor(recovered or preset("Tall order"))
        self.recovered = recovered is not None
        self.recovery_snapshot = self.editor.blueprint.to_dict()
        self.recovery_clock = 0
        self.recovery_failed = False
        self.saved_snapshot = self.editor.blueprint.to_dict() if recovered else None
        self.audio = Audio()
        self.audio.enable(sound_preference(ROOT))
        self.mode = "workshop"
        self.sim = None
        self.previous = None
        self.history = []
        self.engineering = False
        self.paused = False
        self.slow = False
        self.recorded = False
        self.running = True
        self.buttons = []
        self.hold_buttons = []
        self.held_control = None
        self.control_nudge = None
        self.packet_key = None
        self.last_result = ""
        self.last_impact = -1
        self.focus_paused = False
        self.palette = []
        self.mouse = (0, 0)
        self.modal = "intro" if intro else None
        self.input = ""
        self.load_page = 0
        self.notice = recovery_error or ("Your last workshop draft has been recovered." if self.recovered else "Welcome to the lab. Drag a part, change a design, discover why.")
        self.notice_until = time.monotonic()+7
        self.edit_camera = Camera((252, 180, 746, 504), 110)
        self.sim_camera = Camera((24, 180, 974, 504), 87, 2)
        self.keys = set()
        self.render()

    def recovery_save(self, force=False):
        if not self.persist:
            return
        data = self.editor.blueprint.to_dict()
        if force or data != self.recovery_snapshot:
            try:
                store_recovery(ROOT, self.editor.blueprint)
                self.recovery_snapshot = data
                self.recovery_failed = False
            except (OSError, ValueError):
                if not self.recovery_failed:
                    self.toast("Auto-recovery could not save. Use Save to keep your design.")
                self.recovery_failed = True

    def toggle_audio(self):
        enabled = self.audio.enable(not self.audio.enabled)
        try:
            store_preferences(ROOT, enabled)
        except OSError:
            pass
        self.toast("Sound on." if enabled else "Sound off." if self.audio.available else "Audio device unavailable. The game works silently.")
        self.audio.play("click")

    def show_modal(self, name):
        self.keys.clear()
        self.held_control = None
        self.control_nudge = None
        self.modal = name

    def toggle_pause(self):
        self.paused = not self.paused
        self.focus_paused = False
        self.keys.clear()
        self.held_control = None
        self.control_nudge = None

    def fit_build(self):
        from .parts import vertices
        pts = [v for part in self.editor.blueprint.parts for v in vertices(part)]
        if pts:
            xs, ys = zip(*pts)
            self.edit_camera.scale = min(130, 630/max(3, max(xs)-min(xs)), 360/max(3, max(ys)-min(ys)))
            self.edit_camera.x = (min(xs)+max(xs))/2
            self.edit_camera.y = min(ys)+.4

    def hold_button(self, rect, label, channel, value, enabled=True):
        rect = pg.Rect(rect)
        active = self.controls().get(channel) == value and enabled
        self.p.panel(rect, (40, 74, 73) if active else PANEL2, TEAL if active else LINE, 7)
        self.p.text(label, rect.center, 14, TEAL if active else INK if enabled else MUTED, True, True)
        self.hold_buttons.append((rect, channel, value, enabled))

    def toast(self, text):
        self.notice = text
        self.notice_until = time.monotonic()+5

    def logical(self, pos):
        w, h = self.window.get_size()
        factor = min(w/1280, h/800)
        return ((pos[0]-(w-1280*factor)/2)/factor, (pos[1]-(h-800*factor)/2)/factor)

    def button(self, rect, label, action, accent=None, active=False, enabled=True, tip=""):
        rect = pg.Rect(rect)
        hover = rect.collidepoint(self.mouse)
        fill = (35, 58, 68) if active or hover else PANEL2
        self.p.panel(rect, fill, accent if accent else TEAL if active else LINE, 7)
        self.p.text(label, rect.center, 15, (accent or INK) if enabled else (78, 97, 110), True, True)
        self.buttons.append((rect, action, enabled, tip))

    def start(self, scenario):
        errors = validate(self.editor.blueprint)
        if errors:
            self.toast(errors[0][1])
            self.editor.selected = errors[0][0]
            return
        self.finish_attempt()
        try:
            self.sim = Simulation(self.editor.blueprint, scenario)
        except ValueError as exc:
            self.toast(str(exc))
            return
        self.mode = "arena" if scenario == "arena" else "test"
        self.paused, self.slow, self.recorded = False, False, False
        self.keys.clear()
        self.held_control = None
        self.last_result = ""
        self.last_impact = -1
        self.focus_paused = False
        self.control_nudge = None
        self.modal = None
        self.sim_camera.x = 0 if scenario == "arena" else 2
        self.sim_camera.scale = 68 if scenario == "arena" else 87
        self.recovery_save()
        self.toast("AUTOMATIC TEST: manual controls are disabled. Use Free Play to operate the arm." if scenario == "benchmark" else "You are in control. Hold A / D to drive; E / Up and Q / Down operate the arm.")

    def finish_attempt(self):
        if self.sim and not self.recorded and self.sim.time > .2:
            result = self.sim.telemetry.to_dict()
            self.history.append(result)
            self.history = self.history[-20:]
            self.previous = result
            self.recorded = True

    def workshop(self):
        self.finish_attempt()
        self.mode = "workshop"
        self.sim = None
        self.keys.clear()
        self.held_control = None
        self.control_nudge = None

    def reset(self):
        if self.sim:
            # The workshop blueprint has not been mutated by physics.
            self.start(self.sim.scenario)

    def choose_preset(self, name):
        self.editor.replace(preset(name))
        self.modal = None
        self.edit_camera = Camera((252, 180, 746, 504), 110)
        self.toast("Editable example loaded. Ctrl+Z brings back your previous build.")

    def save_dialog(self):
        self.input = self.editor.blueprint.name
        self.modal = "save"
        pg.key.start_text_input()

    def save_named(self):
        if not self.input.strip():
            self.toast("Give this robot a name first.")
            return
        try:
            self.editor.checkpoint()
            self.editor.blueprint.name = self.input.strip()
            path = save(self.editor.blueprint, ROOT / "saves")
            self.saved_snapshot = self.editor.blueprint.to_dict()
            self.recovery_save()
            self.modal = None
            pg.key.stop_text_input()
            self.toast(f"Saved: saves/{path.name}")
        except (OSError, ValueError) as exc:
            self.toast(f"Could not save: {exc}")

    def load_file(self, path):
        try:
            self.editor.replace(load(path))
            self.saved_snapshot = self.editor.blueprint.to_dict()
            self.fit_build()
            self.modal = None
            self.toast("Blueprint loaded. Construction and motor settings restored.")
        except (OSError, ValueError) as exc:
            self.toast(f"Could not load: {exc}")

    def export(self):
        results = self.history[:]
        if self.sim and not self.recorded:
            results.append(self.sim.telemetry.to_dict())
        if not results:
            self.toast("Run a test before exporting your lab notes.")
            return
        path = ROOT / "lab_notes"
        try:
            path.mkdir(exist_ok=True)
            (path / "attempts.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
            with (path / "measurements.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["attempt", "robot", "scenario", "time_s", "distance_m", "tilt_deg"])
                for i, run in enumerate(results, 1):
                    for sample in run["samples"]:
                        writer.writerow([i, run["name"], run["scenario"], *sample])
            self.toast("Exported lab_notes/attempts.json and measurements.csv")
        except OSError as exc:
            self.toast(f"Could not export notes: {exc}")

    def event(self, event):
        if event.type == pg.QUIT:
            self.recovery_save(force=True)
            self.running = False
            return
        if event.type == pg.WINDOWFOCUSLOST:
            self.keys.clear()
            self.held_control = None
            self.control_nudge = None
            if self.sim and not self.sim.result and not self.paused:
                self.paused = True
                self.focus_paused = True
        if event.type == pg.VIDEORESIZE:
            self.window = pg.display.set_mode((max(800, event.w), max(500, event.h)), pg.RESIZABLE)
        if hasattr(event, "pos"):
            self.mouse = self.logical(event.pos)
        if event.type == pg.KEYUP:
            self.keys.discard(event.key)
            if event.key == 0 and self.packet_key:
                self.keys.discard(self.packet_key)
                self.packet_key = None
        if event.type == pg.KEYDOWN:
            # Some Windows accessibility keyboards send VK_PACKET / unicode.
            if event.key == 0 and len(getattr(event, "unicode", "")) == 1:
                event.key = ord(event.unicode.lower())
                self.packet_key = event.key
            if self.modal:
                self.modal_key(event)
                return
            self.keys.add(event.key)
            self.key(event)
        if event.type == pg.TEXTINPUT and self.modal == "save":
            self.input = (self.input+event.text)[:40]
        if event.type == pg.MOUSEBUTTONDOWN and event.button == 1:
            if not self.modal:
                for rect, channel, value, enabled in self.hold_buttons:
                    if rect.collidepoint(self.mouse):
                        if enabled:
                            self.held_control = (channel, value, rect)
                            # A quick click produces one small nudge; a hold continues.
                            self.control_nudge = (channel, value, .16)
                        else:
                            self.toast("Use Free Play for manual control." if self.sim and self.sim.scenario == "benchmark" else "Resume the simulation to use these controls.")
                        return
            for rect, action, enabled, _ in reversed(self.buttons):
                if rect.collidepoint(self.mouse):
                    if enabled:
                        self.audio.play("click")
                        action()
                        if self.modal:
                            self.keys.clear()
                            self.held_control = None
                            self.control_nudge = None
                    return
            if self.modal:
                return
            if self.mode == "workshop":
                for rect, kind in self.palette:
                    if rect.collidepoint(self.mouse):
                        if not self.editor.begin_new(kind, self.edit_camera.world(self.mouse)):
                            self.toast("The lab can simulate up to 60 parts per robot.")
                        return
                if self.edit_camera.rect.collidepoint(self.mouse):
                    self.editor.begin_move(self.edit_camera.world(self.mouse))
        if event.type == pg.MOUSEMOTION and self.mode == "workshop" and not self.modal:
            self.editor.move(self.edit_camera.world(self.mouse))
        if event.type == pg.MOUSEBUTTONUP and event.button == 1:
            self.held_control = None
            if self.mode == "workshop":
                self.editor.drop(self.edit_camera.rect.collidepoint(self.mouse))
        if event.type == pg.MOUSEWHEEL and not self.modal:
            cam = self.edit_camera if self.mode == "workshop" else self.sim_camera
            if cam.rect.collidepoint(self.mouse):
                cam.scale = max(45, min(180, cam.scale+event.y*8))
        if event.type == pg.MOUSEMOTION and self.held_control and not self.held_control[2].collidepoint(self.mouse):
            self.held_control = None
            self.control_nudge = None

    def modal_key(self, e):
        if e.key == pg.K_ESCAPE:
            self.modal = None
            pg.key.stop_text_input()
        elif self.modal == "save":
            if e.key == pg.K_BACKSPACE:
                self.input = self.input[:-1]
            elif e.key == pg.K_a and e.mod & pg.KMOD_CTRL:
                self.input = ""
            elif e.key == pg.K_RETURN:
                self.save_named()
        elif e.key in (pg.K_RETURN, pg.K_F1):
            self.modal = None

    def key(self, e):
        ctrl = e.mod & pg.KMOD_CTRL
        if e.key == pg.K_F1:
            self.show_modal("intro")
        elif e.key == pg.K_m:
            self.toggle_audio()
        elif e.key == pg.K_TAB:
            self.engineering = not self.engineering
        elif e.key == pg.K_ESCAPE and self.mode != "workshop":
            self.workshop()
        elif self.mode == "workshop":
            if ctrl and e.key == pg.K_z:
                self.editor.undo()
            elif ctrl and e.key == pg.K_y:
                self.editor.redo()
            elif ctrl and e.key == pg.K_d:
                self.editor.duplicate()
            elif ctrl and e.key == pg.K_s:
                self.save_dialog()
            elif ctrl and e.key == pg.K_o:
                self.modal = "load"
            elif e.key in (pg.K_DELETE, pg.K_BACKSPACE):
                self.editor.delete()
            elif e.key == pg.K_r:
                self.editor.rotate(-15 if e.mod & pg.KMOD_SHIFT else 15)
            elif e.key == pg.K_g:
                self.editor.snap = not self.editor.snap
            elif e.key == pg.K_HOME:
                self.fit_build()
            elif e.key == pg.K_F5:
                self.start("test")
            elif e.key == pg.K_F6:
                self.start("benchmark")
            elif e.key == pg.K_F7:
                self.start("arena")
        else:
            if e.key == pg.K_SPACE:
                self.toggle_pause()
            elif e.key == pg.K_PERIOD:
                self.paused = True
                self.sim.step(self.controls())
            elif e.key == pg.K_r:
                self.reset()
            elif e.key == pg.K_l:
                self.slow = not self.slow

    def controls(self):
        controls = {"drive": int(pg.K_d in self.keys or pg.K_RIGHT in self.keys)-int(pg.K_a in self.keys or pg.K_LEFT in self.keys),
                    "arm": int(pg.K_q in self.keys or pg.K_DOWN in self.keys)-int(pg.K_e in self.keys or pg.K_UP in self.keys)}
        if self.control_nudge:
            channel, value, _ = self.control_nudge
            if controls[channel] == 0:
                controls[channel] = value
        if self.held_control:
            channel, value, _ = self.held_control
            controls[channel] = value
        return controls

    def update(self, elapsed):
        self.recovery_clock += elapsed
        if self.recovery_clock >= 3 and not self.editor.drag:
            self.recovery_clock = 0
            self.recovery_save()
        if self.sim and not self.paused and not self.modal:
            self.sim.advance(elapsed*(.25 if self.slow else 1), self.controls())
            if self.control_nudge:
                channel, value, remaining = self.control_nudge
                remaining -= elapsed*(.25 if self.slow else 1)
                self.control_nudge = (channel, value, remaining) if remaining > 0 else None
        if self.sim:
            if self.sim.result and self.sim.result != self.last_result:
                self.audio.play("success" if self.sim.telemetry.complete or self.sim.result == "YOU WIN" else "finish")
                self.last_result = self.sim.result
                self.held_control = None
                self.control_nudge = None
                self.keys.clear()
            if self.sim.impacts:
                t, _, strength = self.sim.impacts[-1]
                if t > self.last_impact+.15 and strength > 6:
                    self.audio.play("impact")
                    self.last_impact = t
            if self.mode != "arena":
                target = self.sim.robot.com.x+2
                self.sim_camera.x += (target-self.sim_camera.x)*min(1, elapsed*5)

    def render(self):
        p = self.p
        self.surface.fill(BG)
        self.buttons, self.palette, self.hold_buttons = [], [], []
        self.header()
        if self.mode == "workshop":
            self.draw_workshop()
        else:
            self.draw_simulation()
        self.footer()
        if self.modal:
            self.draw_modal()
        else:
            for rect, _, _, tip in self.buttons:
                if tip and rect.collidepoint(self.mouse):
                    width = min(590, p.font(14).size(tip)[0]+24)
                    x = max(12, min(1268-width, self.mouse[0]-width/2))
                    p.panel((x, 748, width, 31), PANEL2, TEAL, 5)
                    p.text(tip, (x+12, 754), 14)
                    break
        if self.modal and time.monotonic() < self.notice_until:
            p.panel((190, 742, 900, 35), PANEL2, GOLD, 6)
            p.text(self.notice[:106], (205, 749), 16, GOLD)

    def present(self):
        w, h = self.window.get_size()
        scale = min(w/1280, h/800)
        size = (round(1280*scale), round(800*scale))
        self.window.fill((8, 13, 19))
        image = pg.transform.smoothscale(self.surface, size) if size != SIZE else self.surface
        self.window.blit(image, ((w-size[0])//2, (h-size[1])//2))
        pg.display.flip()

    def header(self):
        p = self.p
        pg.draw.rect(self.surface, (16, 27, 38), (0, 0, 1280, 76))
        p.line((0, 75), (1280, 75))
        p.panel((24, 19, 38, 38), TEAL, None, 9)
        p.text("S", (43, 37), 28, BG, True, True)
        p.text("SCRAPLAB", (75, 12), 28, INK, True)
        p.text("BUILD. BREAK. UNDERSTAND.", (76, 45), 11, TEAL, True)
        for x, label, mode, action in [(553, "01  WORKSHOP", "workshop", self.workshop), (732, "02  TEST GROUND", "test", lambda: self.start("test")), (929, "03  ARENA", "arena", lambda: self.start("arena"))]:
            self.button((x, 21, 169 if mode != "test" else 187, 36), label, action, active=self.mode == mode)
        self.button((1113, 21, 142, 36), "FIELD GUIDE  ?", lambda: setattr(self, "modal", "intro"))

    def draw_workshop(self):
        p, ed, bp = self.p, self.editor, self.editor.blueprint
        errors = validate(bp)
        invalid = {uid for uid, _ in errors}
        title = bp.name
        while p.font(27, True).size(title)[0] > 490:
            title = title[:-2].rstrip() + "…"
        p.text(title, (24, 91), 27, INK, True)
        p.text(f"{len(bp.parts):02d} PARTS   /   {bp.total_mass:.1f} kg   /   {len(errors):02d} ASSEMBLY ISSUES", (25, 130), 12, RED if errors else TEAL, True)
        for x, w, label, action in [(548, 116, "Examples", lambda: setattr(self, "modal", "examples")), (674, 72, "Save", self.save_dialog), (756, 72, "Load", lambda: setattr(self, "modal", "load")), (838, 74, "Undo", ed.undo), (922, 74, "Redo", ed.redo)]:
            self.button((x, 99, w, 35), label, action)
        self.button((1020, 99, 236, 35), "RUN BENCHMARK   F6", lambda: self.start("benchmark"), TEAL, tip="12 seconds of identical input. Compare designs fairly.")
        p.text("PARTS DRAWER", (24, 160), 12, MUTED, True)
        p.text("ASSEMBLY TABLE", (253, 160), 12, MUTED, True)
        self.button((862, 146, 135, 26), "FIT BUILD  HOME", self.fit_build, tip="Frame every part, including pieces outside the current view.")
        p.text("PART INSPECTOR", (1020, 160), 12, MUTED, True)
        p.panel((24, 180, 208, 504))
        for i, (kind, spec) in enumerate(CATALOG.items()):
            rect = pg.Rect(32, 190+i*43, 192, 38)
            hover = rect.collidepoint(self.mouse)
            p.panel(rect, PANEL2 if hover else PANEL, TEAL if hover else None, 5)
            if spec.joint == "axle":
                pg.draw.circle(self.surface, spec.color, (49, rect.centery), 10)
                pg.draw.circle(self.surface, GOLD, (49, rect.centery), 4)
            else:
                pg.draw.rect(self.surface, spec.color, (39, rect.centery-6, 20, 12), border_radius=2)
            p.text(spec.label, (68, rect.y+4), 15, INK, True)
            label = {"weld": "RIGID / WELD", "axle": "DRIVEN AXLE", "motor": "MOTOR PIVOT", "pivot": "FREE PIVOT"}[spec.joint]
            p.text(label, (68, rect.y+23), 9, MUTED)
            self.palette.append((rect, kind))
        grid(p, self.edit_camera, True)
        self.surface.set_clip(self.edit_camera.rect)
        if not bp.parts:
            p.text("EVERY INVENTION STARTS HERE.", (625, 380), 22, MUTED, True, True)
            p.text("Drag a chassis plate from the drawer.", (625, 415), 17, MUTED, False, True)
        for part in bp.parts:
            draw_part(p, part, self.edit_camera, selected=part.uid == ed.selected, invalid=part.uid in invalid)
        for part in bp.parts:
            if CATALOG[part.kind].joint == "weld":
                pg.draw.circle(self.surface, (49, 80, 83), self.edit_camera.point((part.x, part.y)), 3, 1)
            else:
                pos = self.edit_camera.point(anchor(part))
                pg.draw.circle(self.surface, RED if part.uid in invalid else GOLD, pos, 5)
        if bp.parts and self.engineering:
            p.com(self.edit_camera.point(bp.com))
        if ed.part and ed.part.kind == "battery" and bp.name in {"Tall order", "Low rider"}:
            point = self.edit_camera.point((0, .38))
            pg.draw.rect(self.surface, TEAL, (point[0]-37, point[1]-28, 74, 56), 1, border_radius=5)
            p.text("TRY A LOW MOUNT", (point[0]+48, point[1]-49), 11, TEAL, True)
        self.surface.set_clip(None)
        pg.draw.rect(self.surface, LINE, self.edit_camera.rect, 1)
        self.draw_inspector(errors)
        self.button((252, 698, 151, 36), "GRID  " + ("ON" if ed.snap else "OFF"), lambda: setattr(ed, "snap", not ed.snap), active=ed.snap, tip="G toggles 0.10 m grid snapping. Mouse wheel zooms.")
        self.button((413, 698, 196, 36), "ENGINEERING   TAB", lambda: setattr(self, "engineering", not self.engineering), active=self.engineering)
        self.button((619, 698, 180, 36), "FREE TEST   F5", lambda: self.start("test"), GOLD)
        self.button((809, 698, 189, 36), "ENTER ARENA   F7", lambda: self.start("arena"), GOLD)
        p.text("DRAG TO BUILD", (25, 702), 12, TEAL, True)
        p.text("Scroll canvas to zoom", (25, 721), 12, MUTED)

    def adjust_row(self, y, label, field, value, step, lo, hi, suffix=""):
        p = self.p
        p.text(label, (1034, y), 12, MUTED)
        p.text(f"{value:g}{suffix}", (1034, y+18), 19, INK, True)
        self.button((1162, y+10, 34, 30), "-", lambda: self.editor.change(field, round(max(lo, value-step), 4)))
        self.button((1205, y+10, 34, 30), "+", lambda: self.editor.change(field, round(min(hi, value+step), 4)))

    def draw_inspector(self, errors):
        p, part = self.p, self.editor.part
        p.panel((1020, 180, 236, 554))
        if not part:
            p.text("Make it yours.", (1035, 198), 23, TEAL, True)
            p.wrap("Select a part to tune its size, material or motor.", (1035, 240), 200, 17)
            p.wrap("Touch rigid pieces to weld them. Gold dots are rotating axles; place these on metal.", (1035, 325), 200, 16)
            p.text("QUICK KEYS", (1035, 450), 12, GOLD, True)
            p.wrap("R / Shift+R  rotate\nCtrl+D  duplicate\nDelete  remove part\nCtrl+Z / Y  undo / redo\nTab  centre of mass", (1035, 478), 206, 15, line_height=27)
            if errors:
                p.wrap(errors[0][1], (1035, 631), 200, 14, RED, 20)
            else:
                p.text("READY TO TEST", (1035, 660), 15, TEAL, True)
            return
        spec = CATALOG[part.kind]
        p.text(spec.label, (1035, 194), 21, TEAL, True)
        w, h = dimensions(part)
        p.text(f"{mass(part):.2f} kg  /  {w:.2f} x {h:.2f} m", (1035, 224), 13, MUTED)
        self.adjust_row(252, "SIZE MULTIPLIER", "scale", part.scale, .1, .5, 1.8, "x")
        self.adjust_row(303, "ANGLE", "angle", part.angle, 15, -180, 180, " deg")
        if spec.joint in ("axle", "motor"):
            self.adjust_row(354, "TARGET MOTOR SPEED", "speed", part.speed, .5, .5, 12, " rad/s")
            self.adjust_row(405, "TORQUE LIMIT", "torque", part.torque, 5, 0, 120, " N m")
            options = ["drive", "arm", "off"]
            control = options[(options.index(part.control)+1) % 3]
            control_label = {"arm": "ARM  E / Q", "drive": "DRIVE  A / D", "off": "OFF / FREE"}[part.control]
            self.button((1034, 462, 207, 32), control_label, lambda: self.editor.change("control", control), tip="Click to cycle: Drive A/D, Arm E/Q + Up/Down, Off.")
            self.button((1034, 503, 207, 32), "Direction: " + ("NORMAL" if part.direction == 1 else "REVERSED"), lambda: self.editor.change("direction", -part.direction))
            self.adjust_row(548, "GRIP MULTIPLIER", "grip", part.grip, .1, .2, 2, "x")
        else:
            if part.kind in {"chassis", "plate", "beam", "long_beam", "pivot"}:
                mats = list(MATERIALS)
                nxt = mats[(mats.index(part.material)+1) % len(mats)]
                self.button((1034, 365, 207, 35), f"Material: {part.material.upper()}", lambda: self.editor.change("material", nxt), tip="Alloy, steel, foam change mass and rotational inertia.")
            p.wrap(spec.description, (1035, 425), 200, 16)
            p.text(f"Position  {part.x:.2f}, {part.y:.2f} m", (1035, 525), 14, MUTED)
        issue = next((message for uid, message in errors if uid == part.uid), None)
        note = "Connected. Ready for a test."
        if part.kind == "arm":
            note = "Hold E / Up or Q / Down in Free Play or the arena." if part.control == "arm" else "This motor uses A / D." if part.control == "drive" else "Motor off. Click OFF above to change its controls."
        elif part.kind == "pivot":
            note = "Passive hinge: no controls. Use Powered lifter for a motor."
        p.wrap(issue or note, (1035, 606), 200, 12, RED if issue else TEAL, 17)
        if part.kind in {"arm", "pivot"}:
            self.button((1034, 646, 207, 27), "TRY IN PRACTICE BAY", lambda: self.start("practice"), GOLD)
        self.button((1034, 682, 101, 35), "Duplicate", self.editor.duplicate)
        self.button((1145, 682, 96, 35), "Delete", self.editor.delete)

    def draw_simulation(self):
        from .hud import draw_simulation
        draw_simulation(self)

    def single_step(self):
        self.paused = True
        self.sim.step(self.controls())

    def footer(self):
        self.p.line((24, 749), (1256, 749))
        default = "Rigid parts weld on contact. Wheel centres and arm pivots mount onto rigid parts."
        if self.mode != "workshop":
            default = "Hold controls to move. Release to brake. Tab: Engineering View. M: sound. F1: guide."
        text = self.notice if time.monotonic() < self.notice_until else default
        self.p.fit_text(text, (24, 762), 1068, 14, MUTED)
        self.p.text("RECOVERY OFF" if self.recovery_failed else "AUTO-RECOVERY ON" if self.persist else "PREVIEW SESSION", (1123, 764), 10, RED if self.recovery_failed else TEAL, True)

    def draw_modal(self):
        p = self.p
        shade = pg.Surface(SIZE, pg.SRCALPHA)
        shade.fill((4, 10, 16, 215))
        self.surface.blit(shade, (0, 0))
        self.buttons = []
        self.hold_buttons = []
        p.panel((190, 104, 900, 626), PANEL, LINE, 18)
        self.button((1027, 123, 42, 33), "X", lambda: setattr(self, "modal", None))
        if self.modal == "intro":
            p.text("WELCOME BACK / DRAFT RECOVERED" if self.recovered else "WELCOME TO THE SCRAPLAB", (230, 140), 12, TEAL, True)
            p.text("Good ideas need a crash test.", (230, 178), 38, INK, True)
            p.wrap("Build a robot from real working parts. Test a theory. Watch the physics. Then make it better.", (230, 242), 740, 21, MUTED, 29)
            for x, n, title, body in [(230, "01", "BUILD", "Drag parts into the table. Touch metal to weld. Put gold pivots on a rigid part."), (505, "02", "UNDERSTAND", "Tab reveals mass and motors. Pause, slow down, and inspect why a machine tips."), (780, "03", "COMPETE", "Drive with A / D. Swing arms with Q / E. Push Copperhead out of the arena.")]:
                p.text(n, (x, 339), 35, TEAL, True)
                p.text(title, (x, 389), 18, INK, True)
                p.wrap(body, (x, 427), 230, 17, MUTED, 25)
            p.panel((230, 554, 820, 77), PANEL2, GOLD, 8)
            p.text("TRY THIS FIRST", (247, 567), 12, GOLD, True)
            p.wrap("Run Tall order's benchmark. Move its battery to the low mount. Run again. Same inputs, different balance.", (247, 589), 770, 16, INK, 22)
            self.button((230, 657, 280, 44), "LET'S BUILD  /  ENTER", lambda: setattr(self, "modal", None), TEAL)
            self.button((540, 657, 184, 44), "SOUND: " + ("ON" if self.audio.enabled else "OFF"), self.toggle_audio)
            self.button((740, 657, 310, 44), "HOW DO I USE THE ARM?", lambda: self.show_modal("controls"), GOLD)
        elif self.modal == "controls":
            p.text("Take control of the linkage.", (230, 151), 34, INK, True)
            p.wrap("Hold E / Up to rotate the arm counterclockwise. Hold Q / Down for clockwise. Release to brake. For a right-facing arm, E raises it.", (230, 213), 790, 20, MUTED, 29)
            rows = [("01  USE MANUAL PLAY", "Choose Free Play, Arm Practice or Arena. The ramp benchmark drives automatically and locks out manual input."), ("02  CHECK THE PART", "Use Powered lifter, attach its gold pivot to rigid metal, and include a battery. Passive arm is an unpowered hinge."), ("03  CHECK THE INSPECTOR", "Set the arm's control to ARM E / Q and torque above zero. Reversed direction swaps which way each key turns it.")]
            for i, (title, body) in enumerate(rows):
                y = 326+i*91
                p.text(title, (230, y), 13, GOLD, True)
                p.wrap(body, (230, y+27), 775, 17, MUTED, 23)
            p.text("Watch the Linkage panel for power, angle limits and torque feedback.", (230, 612), 16, TEAL)
            self.button((230, 657, 320, 44), "OPEN PRACTICE BAY", lambda: self.start("practice"), TEAL)
            self.button((570, 657, 245, 44), "BACK TO FIELD GUIDE", lambda: self.show_modal("intro"))
        elif self.modal == "examples":
            p.text("Pick a starting point.", (230, 146), 34, INK, True)
            p.text("Every example is fully editable. Undo restores your last build.", (230, 199), 17, MUTED)
            for i, (name, detail) in enumerate([("Tall order", "The centre-of-mass experiment. A little too ambitious."), ("Low rider", "Same machine, lower battery. Compare your own fix."), ("Forklift", "Wide base, trail wheels, wedge and a powered arm."), ("Blank", "An empty table. Your idea starts here.")]):
                y = 255+i*93
                self.button((230, y, 215, 61), name.upper(), lambda n=name: self.choose_preset(n), TEAL)
                p.wrap(detail, (478, y+9), 535, 18, MUTED, 25)
        elif self.modal == "save":
            p.text("Name your invention.", (230, 155), 34, INK, True)
            p.wrap("Blueprints save as editable, versioned JSON in the saves folder. Saving the same name replaces that saved draft.", (230, 218), 740, 19, MUTED, 28)
            p.panel((230, 336, 780, 67), BG, TEAL, 7)
            p.text(self.input + ("|" if int(time.monotonic()*2)%2 else ""), (248, 351), 27)
            p.text("Ctrl+A clears the name. Enter saves. Esc cancels.", (230, 426), 16, MUTED)
            self.button((230, 510, 260, 48), "SAVE BLUEPRINT", self.save_named, TEAL)
        elif self.modal == "load":
            p.text("Blueprint library", (230, 147), 34, INK, True)
            p.text("Your drafts and the editable examples. Nothing runs from a JSON file.", (230, 201), 16, MUTED)
            files = sorted((ROOT / "saves").glob("*.json")) + sorted((ROOT / "examples").glob("*.json"))
            max_page = max(0, (len(files)-1)//7)
            self.load_page = min(self.load_page, max_page)
            for i, path in enumerate(files[self.load_page*7:self.load_page*7+7]):
                self.button((230, 251+i*52, 795, 42), f"{path.parent.name.upper()}  /  {path.stem}", lambda f=path: self.load_file(f))
            if not files:
                p.text("No saved blueprints yet. Build something worth keeping.", (230, 291), 19, GOLD)
            self.button((230, 657, 140, 36), "PREVIOUS", lambda: setattr(self, "load_page", max(0, self.load_page-1)))
            self.button((385, 657, 140, 36), "NEXT", lambda: setattr(self, "load_page", min(max_page, self.load_page+1)))
            p.text(f"Page {self.load_page+1} / {max_page+1}", (556, 665), 15, MUTED)
        elif self.modal == "notes":
            self.draw_notes()

    def draw_notes(self):
        p = self.p
        p.text("The lab notebook", (230, 140), 34, INK, True)
        p.text("Measured attempts. Change one thing; learn something real.", (230, 192), 18, MUTED)
        current = self.sim.telemetry.to_dict() if self.sim else (self.history[-1] if self.history else None)
        previous = self.previous
        if self.recorded and len(self.history) > 1:
            previous = self.history[-2]
        if not current:
            p.text("Run a test to start your notebook.", (230, 280), 24, GOLD)
            return
        for x, title, run, color in [(230, "PREVIOUS ATTEMPT", previous, PURPLE), (650, "CURRENT ATTEMPT", current, TEAL)]:
            p.text(title, (x, 245), 12, color, True)
            if not run:
                p.wrap("No previous attempt. Return to editing and run another test.", (x, 279), 340, 18)
                continue
            p.fit_text(run["name"], (x, 276), 365, 23, INK, True)
            p.text(f"{run['scenario']}  /  {run['elapsed']:.2f} s", (x, 311), 14, MUTED)
            p.text(f"{run['distance']:+.2f} m    {run['max_tilt']:.1f} deg peak", (x, 345), 22, color, True)
            p.text(("Linkage check complete" if run["scenario"] == "practice" else "Summit crossed") if run["complete"] else "Tipping threshold crossed" if run["tipped"] else "No threshold event", (x, 383), 16, color)
        if previous and (previous["scenario"] != current["scenario"] or abs(previous["elapsed"]-current["elapsed"]) > .1):
            p.text("Different scenario / duration: use two complete benchmarks for a fair comparison.", (230, 421), 14, GOLD)
        else:
            p.text("CHASSIS TILT OVER TIME / degrees", (230, 421), 12, MUTED, True)
        rect = pg.Rect(266, 460, 740, 128)
        p.panel(rect, BG, LINE, 4)
        for tilt in (0, 65, 130, 180):
            y = rect.bottom-tilt/180*rect.height
            p.line((rect.left, y), (rect.right, y), (62, 54, 46) if tilt == 65 else LINE)
            p.text(str(tilt), (230, y-8), 11, GOLD if tilt == 65 else MUTED)
        duration = max(12, current["elapsed"], previous["elapsed"] if previous else 0)
        for run, color in [(previous, PURPLE), (current, TEAL)]:
            if run and len(run["samples"]) > 1:
                pts = [(rect.left+t/duration*rect.width, rect.bottom-min(180, tilt)/180*rect.height) for t, _, tilt in run["samples"]]
                pg.draw.lines(self.surface, color, False, pts, 2)
        for fraction in (0, .5, 1):
            p.text(f"{duration*fraction:g} s", (rect.left+fraction*rect.width, 605), 12, MUTED, center=True)
        event = current["events"][-1] if current["events"] else "No tipping or summit event measured in this attempt."
        p.text(event, (230, 629), 16, GOLD)
        self.button((230, 667, 243, 37), "EXPORT JSON + CSV", self.export, TEAL)
        self.button((490, 667, 243, 37), "BACK TO EXPERIMENT", lambda: setattr(self, "modal", None))

    def run(self, frames=None, screenshot=None):
        clock = pg.time.Clock()
        count = 0
        while self.running:
            elapsed = clock.tick(60)/1000
            for event in pg.event.get():
                self.event(event)
            self.update(elapsed)
            self.render()
            self.present()
            count += 1
            if frames and count >= frames:
                break
        if screenshot:
            pg.image.save(self.surface, str(screenshot))
        self.finish_attempt()
        self.recovery_save(force=True)
        pg.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ScrapLab desktop robot workshop")
    parser.add_argument("--no-intro", action="store_true")
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--preset", choices=["Tall order", "Low rider", "Forklift", "Blank"])
    parser.add_argument("--practice", action="store_true", help="Open the manual arm practice bay")
    parser.add_argument("--no-recovery", action="store_true", help="Do not read/write the recovery draft (preview/testing)")
    parser.add_argument("--frames", type=int, help="Exit after N frames (smoke test)")
    parser.add_argument("--screenshot", type=Path, help="Save the last rendered frame")
    args = parser.parse_args()
    app = App(intro=not args.no_intro, persist=not args.no_recovery)
    if args.preset:
        app.editor.replace(preset(args.preset))
    if args.benchmark:
        app.start("benchmark")
    elif args.practice:
        app.start("practice")
    app.run(args.frames, args.screenshot)
