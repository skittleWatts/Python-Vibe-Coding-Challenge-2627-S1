"""Readable simulation HUD: controls explain the current mode and motor state."""
import math
import pygame as pg
from .feedback import arm_feedback
from .parts import WEAPONS
from .battle_ui import draw_battle_score
from .render import (grid, scenery, draw_robot, impacts, BG, PANEL, PANEL2,
                     LINE, INK, MUTED, TEAL, GOLD, RED)
from .scenarios import BENCHMARK_SECONDS


def draw_simulation(app):
    p, sim = app.p, app.sim
    t = sim.telemetry
    auto = sim.scenario == "benchmark"
    practice = sim.scenario == "practice"
    arena = sim.scenario == "arena"
    manual = not auto and not app.paused and not sim.result and not (arena and sim.time < 2)
    title = "The Crucible" if arena else "Arm practice bay" if practice else "Repeatable ramp test" if auto else "Open test ground"
    p.text(title, (24, 91), 28, INK, True)
    subtitle = "HIT FOR POINTS  /  RING-OUT OR 3s OVERTURNED TO FINISH" if arena else "LEARN THE LINKAGE  /  YOUR CONTROLS, REAL PHYSICS" if practice else "AUTOMATIC BENCHMARK  /  MANUAL INPUT IS DISABLED" if auto else "FREE PLAY  /  A & D DRIVE  /  E & Q OR UP & DOWN OPERATE ARMS"
    p.text(subtitle, (25, 134), 11, GOLD if auto else MUTED, True)
    app.button((630, 99, 100, 35), "EDIT  ESC", app.workshop, TEAL)
    app.button((740, 99, 98, 35), "RESET  R", app.reset)
    app.button((848, 99, 150, 35), "FREE PLAY" if auto or practice else "ARM PRACTICE", lambda: app.start("test" if auto or practice else "practice"), GOLD)
    app.button((1020, 99, 236, 35), "LAB NOTEBOOK", lambda: app.show_modal("notes"), TEAL)
    grid(p, app.sim_camera)
    scenery(p, sim, app.sim_camera)
    if sim.opponent:
        draw_robot(p, sim.opponent, app.sim_camera, app.engineering, True)
    draw_robot(p, sim.robot, app.sim_camera, app.engineering)
    impacts(p, sim, app.sim_camera, app.engineering)
    pg.draw.rect(app.surface, LINE, app.sim_camera.rect, 1)

    if not sim.result:
        p.panel((40, 195, 282, 76), (18, 34, 45), LINE, 9)
        p.text("AUTOPILOT / BENCHMARK" if auto else "DRIVE / TAP TO NUDGE, HOLD TO MOVE", (53, 205), 10, GOLD if auto else TEAL, True)
        app.hold_button((50, 228, 125, 31), "A  /  LEFT", "drive", -1, manual)
        app.hold_button((185, 228, 125, 31), "D  /  RIGHT", "drive", 1, manual)
        if auto:
            p.panel((622, 195, 360, 76), PANEL, GOLD, 9)
            p.text("SAME INPUTS. DIFFERENT DESIGN.", (638, 207), 12, GOLD, True)
            p.wrap("To use the arm yourself, click Free Play above.", (638, 231), 324, 14, INK, 20)
        elif practice:
            p.panel((648, 195, 334, 84), PANEL, TEAL if t.complete else LINE, 9)
            p.text("LINKAGE CHECK" + ("  /  COMPLETE" if t.complete else ""), (663, 206), 12, TEAL, True)
            p.text(("DONE" if sim.practice_raised else "01") + "   Rotate past +45 deg (E / Up)", (663, 231), 14, TEAL if sim.practice_raised else INK)
            p.text(("DONE" if sim.practice_lowered else "02") + "   Rotate below -25 deg (Q / Down)", (663, 253), 14, TEAL if sim.practice_lowered else INK)
        elif arena:
            p.panel((726, 195, 256, 76), PANEL, LINE, 9)
            p.text("KNOCKOUT / 3s OVERTURNED", (742, 207), 12, INK, True)
            p.text(f"Overturned   {sim.knockout[0]:.1f} / {sim.knockout[1]:.1f} s", (742, 234), 14, MUTED)
            for x, timer, color in ((742, sim.knockout[0], TEAL), (856, sim.knockout[1], RED)):
                pg.draw.rect(app.surface, BG, (x, 255, 100, 5), border_radius=2)
                pg.draw.rect(app.surface, color, (x, 255, round(100*min(1, timer/3)), 5), border_radius=2)
        else:
            p.text("< WEIGHTS + OBSTACLE     INCLINE + SUMMIT >", (628, 211), 12, MUTED, True)

    if auto:
        pg.draw.rect(app.surface, (29, 55, 61), (24, 675, 974, 9))
        pg.draw.rect(app.surface, TEAL, (24, 675, round(974*min(1, sim.time/BENCHMARK_SECONDS)), 9))
    if arena and sim.time < 2:
        p.text(str(max(1, math.ceil(2-sim.time))), (510, 345), 90, GOLD, True, True)
        p.text("GET READY / YOU ARE THE TEAL ROBOT", (510, 415), 17, GOLD, True, True)
    if app.paused and not sim.result:
        p.panel((332, 310, 358, 126), (17, 34, 45), GOLD, 11)
        p.text("PAUSED", (511, 336), 29, GOLD, True, True)
        p.text("Window lost focus." if app.focus_paused else "Inspect. Think. Try again.", (511, 370), 15, MUTED, False, True)
        app.button((408, 394, 206, 30), "RESUME  /  SPACE", app.toggle_pause, TEAL)
    if sim.result:
        color = TEAL if t.complete or sim.result == "YOU WIN" else GOLD
        p.panel((40, 195, 942, 108), (18, 36, 45), color, 11)
        p.fit_text(sim.result, (57, 207), 680, 29, color, True)
        p.wrap(sim.result_reason, (58, 254), 675, 14, MUTED, 20)
        app.button((776, 209, 188, 34), "RETRY   R", app.reset, color)
        app.button((776, 254, 188, 34), "EDIT DESIGN   ESC", app.workshop, TEAL)

    if arena:
        draw_battle_score(app)

    # The important numbers stay legible without a wall of tiny telemetry.
    p.panel((1020, 180, 236, 554))
    p.text("LIVE TELEMETRY", (1035, 197), 12, TEAL, True)
    p.text("TIME", (1035, 229), 10, MUTED, True)
    p.text("DISTANCE", (1141, 229), 10, MUTED, True)
    p.fit_text(f"{sim.time:.2f} s", (1035, 246), 97, 23, INK, True)
    p.fit_text(f"{t.distance:+.2f} m", (1141, 246), 102, 23, INK, True)
    p.text("PEAK TILT", (1035, 289), 10, MUTED, True)
    p.text("TOTAL MASS", (1141, 289), 10, MUTED, True)
    p.text(f"{t.max_tilt:.1f}°", (1035, 306), 26, RED if t.tipped else GOLD, True)
    p.text(f"{sim.blueprint.total_mass:.1f} kg", (1141, 310), 18, INK, True)
    p.line((1035, 348), (1241, 348))
    p.text("MOTOR LOAD / TORQUE CAP", (1035, 362), 11, MUTED, True)
    motors = sim.robot.motors
    for i, (part, motor) in enumerate(motors[:3]):
        load = motor.impulse/sim.dt
        rate = motor.a.angular_velocity-motor.b.angular_velocity
        y = 386+i*43
        p.text(("WEAPON" if part.kind in WEAPONS else f"AXLE {i+1}") + f"  {load:.1f} / {motor.max_force:.0f} N m", (1035, y), 13, GOLD if motor.max_force > 0 and load >= motor.max_force*.95 else TEAL, True)
        p.text(f"{rate:+.1f} rad/s   |   {part.control}", (1035, y+19), 11, MUTED)
    if len(motors) > 3:
        p.text(f"Showing 3 of {len(motors)} motors", (1035, 516), 10, MUTED)

    feedback = arm_feedback(sim.robot, sim.dt, sim.robot.last_controls)
    if auto:
        feedback.update(title="AUTOMATIC TEST", detail="Manual arm controls are off. Choose Free Play to operate it.", state="warning")
    elif app.paused:
        feedback.update(title="SIMULATION PAUSED", detail="Resume before operating the arm.", state="idle")
    elif sim.result:
        feedback.update(title="ATTEMPT FINISHED", detail="Retry or choose Free Play to take control.", state="idle")
    color = GOLD if feedback["state"] == "warning" else TEAL
    p.panel((1030, 533, 216, 172), (15, 28, 39), color if feedback["state"] == "active" else LINE, 8)
    p.text("WEAPON / ARM", (1040, 542), 10, MUTED, True)
    if "rpm" in feedback:
        p.text(f"{feedback['rpm']:.0f} RPM", (1180, 540), 12, color, True)
    if feedback["angle"] is not None:
        p.text(f"{feedback['angle']:+.0f}°", (1200, 540), 12, color, True)
    p.fit_text(feedback["title"], (1040, 561), 198, 16, color, True)
    p.wrap(feedback["detail"], (1040, 586), 195, 12, MUTED, 17)
    if feedback["angle"] is not None:
        fraction = max(0, min(1, (feedback["angle"]+65)/165))
        pg.draw.rect(app.surface, LINE, (1041, 645, 192, 4), border_radius=2)
        pg.draw.circle(app.surface, color, (1041+round(fraction*192), 647), 4)
    app.hold_button((1040, 662, 94, 32), "E / UP", "arm", -1, manual)
    app.hold_button((1142, 662, 94, 32), "Q / DOWN", "arm", 1, manual)
    p.text(f"BATTERY BUDGET  {sim.robot.power_budget:.0f} N m", (1035, 716), 11, MUTED)

    app.button((24, 698, 155, 36), "RESUME" if app.paused else "PAUSE  SPACE", app.toggle_pause, active=app.paused)
    app.button((189, 698, 113, 36), "STEP  .", app.single_step, tip="Advance exactly one 1/240-second physics step.")
    app.button((312, 698, 142, 36), "SLOW  0.25x", lambda: setattr(app, "slow", not app.slow), active=app.slow)
    app.button((464, 698, 195, 36), "ENGINEERING   TAB", lambda: setattr(app, "engineering", not app.engineering), active=app.engineering)
    app.button((669, 698, 150, 36), "COMPARE", lambda: app.show_modal("notes"), GOLD)
    app.button((829, 698, 169, 36), "EXPORT NOTES", app.export)
