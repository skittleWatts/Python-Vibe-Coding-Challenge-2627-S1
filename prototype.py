"""First runnable stage: a real motor-driven vehicle. A/D drive. Esc exits."""
import pygame as pg
import pymunk.pygame_util
from scraplab.physics import Simulation
from scraplab.blueprint import preset


def main():
    pg.init()
    screen = pg.display.set_mode((1000, 700))
    pg.display.set_caption("ScrapLab / physics prototype")
    sim = Simulation(preset("Low rider"))
    clock = pg.time.Clock()
    running = True
    while running:
        dt = clock.tick(60)/1000
        for e in pg.event.get():
            if e.type == pg.QUIT or e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                running = False
        keys = pg.key.get_pressed()
        sim.advance(dt, {"drive": int(keys[pg.K_d])-int(keys[pg.K_a])})
        screen.fill((13, 23, 33))
        opt = pymunk.pygame_util.DrawOptions(screen)
        opt.transform = pymunk.Transform(a=65, d=-65, tx=180, ty=560)
        sim.space.debug_draw(opt)
        pg.display.flip()
    pg.quit()


if __name__ == "__main__":
    main()
