r"""Re-run the genuine demonstration and optionally save screenshots + raw data.

    .venv\Scripts\python.exe verify_demo.py --artifacts
"""
import argparse
import json
from pathlib import Path
from scraplab.blueprint import preset
from scraplab.physics import Simulation, DT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", action="store_true")
    args = parser.parse_args()
    runs = []
    sims = []
    for name in ("Tall order", "Low rider"):
        sim = Simulation(preset(name), "benchmark")
        for _ in range(round(12/DT)):
            sim.step()
        sims.append(sim)
        report = sim.telemetry.to_dict()
        runs.append(report)
        print(f"{name}: {report['distance']:.2f} m, {report['max_tilt']:.1f} deg peak, summit={report['complete']}, tipped={report['tipped']}")
    assert runs[0]["tipped"] and not runs[0]["complete"], "Tall design did not tip as expected"
    assert runs[1]["complete"] and not runs[1]["tipped"], "Low design did not reach the summit upright"
    if args.artifacts:
        import os
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import pygame as pg
        from scraplab.app import App, ROOT
        folder = ROOT / "docs"
        folder.mkdir(exist_ok=True)
        (folder / "benchmark_results.json").write_text(json.dumps(runs, indent=2), encoding="utf-8")
        app = App(intro=False, persist=False)
        app.notice_until = 0
        app.engineering = True
        app.render()
        pg.image.save(app.surface, str(folder / "workshop.png"))
        for sim, name in zip(sims, ("tall_test", "low_test")):
            app.sim = sim
            app.mode = "test"
            app.sim_camera.x = sim.robot.com.x+2
            app.render()
            pg.image.save(app.surface, str(folder / f"{name}.png"))
        app.previous = runs[0]
        app.modal = "notes"
        app.render()
        pg.image.save(app.surface, str(folder / "comparison.png"))
        app.modal = None
        app.editor.replace(preset("Forklift"))
        app.start("arena")
        for _ in range(900):
            app.sim.step({"drive": 1, "arm": -1})
        app.render()
        pg.image.save(app.surface, str(folder / "arena.png"))
        app.start("practice")
        for _ in range(120):
            app.sim.step({"arm": -1})
        app.notice_until = 0
        app.render()
        pg.image.save(app.surface, str(folder / "practice.png"))
        pg.quit()


if __name__ == "__main__":
    main()
