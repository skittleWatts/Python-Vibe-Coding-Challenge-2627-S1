"""Original procedural workshop visuals. Draw the actual physical shapes."""
import math
import pygame as pg
import pymunk as pm
from .parts import CATALOG, dimensions, vertices, anchor, centroid

BG = (12, 20, 29)
PANEL = (20, 32, 44)
PANEL2 = (26, 42, 55)
LINE = (45, 66, 80)
INK = (229, 239, 239)
MUTED = (145, 167, 179)
TEAL = (100, 232, 194)
GOLD = (244, 183, 91)
RED = (255, 119, 116)
PURPLE = (177, 158, 234)


class Painter:
    def __init__(self, surface):
        self.s = surface
        self.fonts = {}

    def font(self, size=18, bold=False):
        key = (size, bold)
        if key not in self.fonts:
            self.fonts[key] = pg.font.SysFont("segoeui,dejavusans,arial", size, bold=bold)
        return self.fonts[key]

    def text(self, text, pos, size=18, color=INK, bold=False, center=False):
        image = self.font(size, bold).render(str(text), True, color)
        rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
        self.s.blit(image, rect)
        return rect

    def fit_text(self, text, pos, width, size=18, color=INK, bold=False):
        value = str(text)
        while self.font(size, bold).size(value)[0] > width and len(value) > 1:
            value = value[:-2].rstrip() + "…"
        return self.text(value, pos, size, color, bold)

    def wrap(self, text, pos, width, size=16, color=MUTED, line_height=23):
        x, y = pos
        for paragraph in str(text).split("\n"):
            line = ""
            for word in paragraph.split():
                if self.font(size).size(line+word)[0] > width and line:
                    self.text(line.strip(), (x, y), size, color)
                    y += line_height
                    line = ""
                line += word+" "
            self.text(line.strip(), (x, y), size, color)
            y += line_height
        return y

    def panel(self, rect, color=PANEL, border=LINE, radius=12):
        pg.draw.rect(self.s, color, rect, border_radius=radius)
        if border:
            pg.draw.rect(self.s, border, rect, 1, border_radius=radius)

    def line(self, a, b, color=LINE, width=1):
        pg.draw.line(self.s, color, a, b, width)

    def com(self, pos, label=True):
        x, y = map(round, pos)
        pg.draw.circle(self.s, BG, (x, y), 13)
        pg.draw.circle(self.s, GOLD, (x, y), 12, 2)
        pg.draw.circle(self.s, GOLD, (x, y), 3)
        self.line((x-18, y), (x+18, y), GOLD, 1)
        self.line((x, y-18), (x, y+18), GOLD, 1)
        if label:
            self.text("CENTRE OF MASS", (x+20, y-12), 12, GOLD, True)


class Camera:
    def __init__(self, rect, scale=105, x=0, y=0):
        self.rect = pg.Rect(rect)
        self.scale = scale
        self.x, self.y = x, y

    def point(self, point):
        return (round(self.rect.centerx+(point[0]-self.x)*self.scale), round(self.rect.bottom-75-(point[1]-self.y)*self.scale))

    def world(self, point):
        return ((point[0]-self.rect.centerx)/self.scale+self.x, (self.rect.bottom-75-point[1])/self.scale+self.y)


def grid(p, camera, editor=False):
    rect = camera.rect
    p.s.set_clip(rect)
    pg.draw.rect(p.s, (15, 27, 38), rect)
    if not editor:
        # Distant industrial ribs: decorative parallax, never collision geometry.
        horizon = rect.top+140
        for i in range(-12, 14):
            x = rect.centerx+i*160-int(camera.x*8) % 160
            pg.draw.rect(p.s, (19, 33, 45), (x, rect.top, 10, rect.height))
            pg.draw.line(p.s, (24, 40, 53), (x+10, horizon-75), (x+157, horizon+30), 3)
            pg.draw.rect(p.s, (38, 61, 67), (x+35, rect.top+72, 52, 3), border_radius=1)
    step = .25 if editor else 1
    left, bottom = camera.world(rect.bottomleft)
    right, top = camera.world(rect.topright)
    for i in range(math.floor(left/step), math.ceil(right/step)+1):
        a = camera.point((i*step, 0))[0]
        pg.draw.line(p.s, (26, 44, 57) if i % 4 else (36, 55, 68), (a, rect.top), (a, rect.bottom))
    for i in range(math.floor(bottom/step), math.ceil(top/step)+1):
        y = camera.point((0, i*step))[1]
        pg.draw.line(p.s, (26, 44, 57) if i % 4 else (36, 55, 68), (rect.left, y), (rect.right, y))
    if editor:
        ox, oy = camera.point((0, 0))
        p.line((ox, rect.top), (ox, rect.bottom), (49, 80, 91))
        p.line((rect.left, oy), (rect.right, oy), (49, 80, 91))
        p.text("0 m", (ox+5, oy+7), 12, MUTED)
    p.s.set_clip(None)


def draw_part(p, part, camera, shape=None, selected=False, invalid=False, tint=None, ghost=False):
    spec = CATALOG[part.kind]
    color = tint or spec.color
    if part.material == "foam" and spec.joint == "weld" and part.kind != "battery":
        color = (106, 147, 155)
    elif part.material == "steel" and part.kind in {"chassis", "plate", "beam", "long_beam", "arm", "pivot"}:
        color = (144, 154, 171)
    outline = RED if invalid else TEAL if selected else tuple(min(255, c+30) for c in color)
    if shape:
        pos = camera.point(shape.body.local_to_world(shape.offset)) if isinstance(shape, pm.Circle) else camera.point(shape.body.position)
        angle = shape.body.angle
        if not isinstance(shape, pm.Circle):
            pts = [camera.point(shape.body.local_to_world(v)) for v in shape.get_vertices()]
    else:
        pos = camera.point((part.x, part.y))
        angle = math.radians(part.angle)
        if spec.joint != "axle":
            pts = [camera.point(v) for v in vertices(part)]
    if spec.joint == "axle":
        r = max(5, round(dimensions(part)[0]/2*camera.scale))
        pg.draw.circle(p.s, (8, 14, 21), pos, r+3)
        pg.draw.circle(p.s, color, pos, r)
        pg.draw.circle(p.s, outline, pos, r, 3 if selected else 2)
        pg.draw.circle(p.s, (22, 34, 45), pos, max(3, r-9))
        for i in range(12):
            a = angle+i*math.tau/12
            p.line((pos[0]+math.cos(a)*(r-6), pos[1]-math.sin(a)*(r-6)), (pos[0]+math.cos(a)*(r-1), pos[1]-math.sin(a)*(r-1)), (139, 156, 163), 2)
        for i in range(5):
            a = angle+i*math.tau/5
            p.line(pos, (pos[0]+math.cos(a)*(r-13), pos[1]-math.sin(a)*(r-13)), (108, 135, 147), 3)
        pg.draw.circle(p.s, GOLD, pos, 7)
        pg.draw.circle(p.s, BG, pos, 3)
    else:
        pg.draw.polygon(p.s, (6, 12, 20), [(x+3, y+4) for x, y in pts])
        pg.draw.polygon(p.s, color, pts)
        pg.draw.polygon(p.s, outline, pts, 3 if selected or invalid else 1)
        center = (sum(x for x, _ in pts)/len(pts), sum(y for _, y in pts)/len(pts))
        # Rivets and inner seams make material and attachment readable.
        for x, y in pts:
            dot = (round(x*.78+center[0]*.22), round(y*.78+center[1]*.22))
            pg.draw.circle(p.s, (43, 62, 71), dot, 2)
        if part.kind == "battery":
            cx, cy = center
            p.text("+  -", (cx, cy-10), max(12, round(15*part.scale)), BG, True, True)
            p.text("CELL", (cx, cy+10), 11, BG, True, True)
        elif part.kind == "ballast":
            p.text("Fe", center, 16, BG, True, True)
        elif part.kind in {"arm", "pivot"} and len(pts) == 4:
            a = ((pts[0][0]+pts[3][0])/2, (pts[0][1]+pts[3][1])/2)
            b = ((pts[1][0]+pts[2][0])/2, (pts[1][1]+pts[2][1])/2)
            p.line(a, b, (102, 66, 45) if part.kind == "arm" else (91, 75, 126), max(1, round(camera.scale*.025)))
        if spec.joint in {"motor", "pivot"} and not shape:
            pg.draw.circle(p.s, GOLD if spec.joint == "motor" else PURPLE, camera.point(anchor(part)), 7)
    if selected:
        if spec.joint == "axle":
            box = pg.Rect(pos[0]-r-9, pos[1]-r-9, 2*r+18, 2*r+18)
        else:
            xs, ys = zip(*pts)
            box = pg.Rect(min(xs)-8, min(ys)-8, max(xs)-min(xs)+16, max(ys)-min(ys)+16)
        for x, y, sx, sy in [(box.left, box.top, 1, 1), (box.right, box.top, -1, 1), (box.left, box.bottom, 1, -1), (box.right, box.bottom, -1, -1)]:
            p.line((x, y), (x+sx*11, y), TEAL, 2)
            p.line((x, y), (x, y+sy*11), TEAL, 2)


def scenery(p, sim, camera):
    p.s.set_clip(camera.rect)
    for segment in sim.terrain:
        a, b = camera.point(segment.a), camera.point(segment.b)
        bottom = camera.rect.bottom
        pg.draw.polygon(p.s, (33, 48, 59), [a, b, (b[0], bottom), (a[0], bottom)])
        p.line(a, b, (122, 150, 155), max(3, round(segment.radius*2*camera.scale)))
        p.line((a[0], a[1]+7), (b[0], b[1]+7), GOLD, 2)
    for shape, weight in sim.props:
        pts = [camera.point(shape.body.local_to_world(v)) for v in shape.get_vertices()]
        pg.draw.polygon(p.s, (132, 102, 72), pts)
        pg.draw.polygon(p.s, GOLD, pts, 2)
        p.text(f"{weight} kg", camera.point(shape.body.position), 14, INK, True, True)
    if sim.scenario == "practice":
        for x, label in [(-2.4, "LINKAGE TRAINING"), (3.2, "1 kg PRACTICE WEIGHT")]:
            pos = camera.point((x, 2.6))
            p.text(label, pos, 13, (87, 128, 142), True)
    elif sim.scenario != "arena":
        for x, y, label in [(4, 0, "25° INCLINE"), (10.2, 2.35, "SUMMIT GATE"), (-4.4, 0, "LIFT / PUSH")]:
            a = camera.point((x, y))
            p.line(a, (a[0], a[1]-100), TEAL, 2)
            p.panel((a[0], a[1]-105, 124, 27), PANEL2, TEAL, 3)
            p.text(label, (a[0]+7, a[1]-100), 12, TEAL, True)
        a, b = camera.point((-6.8, .3)), camera.point((-6.8, .7))
        p.text("OBSTACLE", (b[0], b[1]), 12, GOLD, True)
    else:
        floor = camera.point((0, 0))[1]
        left, right = camera.point((-6, 0))[0], camera.point((6, 0))[0]
        pg.draw.rect(p.s, (77, 65, 43), (left, floor+8, right-left, 14))
        for x in range(left, right, 28):
            pg.draw.polygon(p.s, GOLD, [(x, floor+8), (x+11, floor+8), (x+22, floor+22), (x+11, floor+22)])
        for x in (-6, 6):
            a = camera.point((x, 0))
            p.text("DROP", (a[0], a[1]+25), 13, RED, True, True)
        p.text("THE CRUCIBLE", camera.point((0, 3.2)), 33, (38, 65, 77), True, True)
    p.s.set_clip(None)


def draw_robot(p, robot, camera, engineering=False, rival=False):
    p.s.set_clip(camera.rect)
    for v in robot.visuals:
        draw_part(p, v.part, camera, v.shape, tint=(183, 118, 107) if rival and CATALOG[v.part.kind].joint == "weld" else None)
    for part, joint in robot.joints:
        pos = camera.point(joint.a.local_to_world(joint.anchor_a))
        pg.draw.circle(p.s, GOLD if part.kind != "pivot" else PURPLE, pos, 5)
        if engineering:
            pg.draw.circle(p.s, GOLD, pos, 10, 1)
            if part.kind in {"arm", "pivot"}:
                origin = joint.a.local_to_world(joint.anchor_a)
                base = robot.body.angle+math.radians(part.angle)
                radius = .48
                arc = [camera.point(origin+pm.Vec2d(math.cos(base+math.radians(a)), math.sin(base+math.radians(a)))*radius) for a in range(-65, 101, 5)]
                pg.draw.lines(p.s, (135, 112, 71), False, arc, 1)
                for endpoint in (arc[0], arc[-1]):
                    pg.draw.circle(p.s, GOLD, endpoint, 3)
    if engineering:
        c = camera.point(robot.com)
        p.line(c, (c[0], camera.point((0, 0))[1]), GOLD, 1)
        p.com(c)
        for i, (part, motor) in enumerate(robot.motors):
            joint = next(j for q, j in robot.joints if q.uid == part.uid)
            pos = camera.point(joint.a.local_to_world(joint.anchor_a))
            load = motor.impulse/(1/240)
            ratio = min(1, load/max(motor.max_force, .01))
            pg.draw.rect(p.s, BG, (pos[0]-21, pos[1]+20, 42, 5), border_radius=2)
            pg.draw.rect(p.s, RED if ratio > .95 else TEAL, (pos[0]-21, pos[1]+20, round(42*ratio), 5), border_radius=2)
    p.s.set_clip(None)


def impacts(p, sim, camera, engineering=False):
    p.s.set_clip(camera.rect)
    if engineering:
        for pos, force in sim.contacts:
            pt = camera.point(pos)
            pg.draw.circle(p.s, TEAL, pt, 3)
    for t, pos, strength in sim.impacts:
        age = sim.time-t
        x, y = camera.point(pos)
        radius = age*(30+strength)
        for i in range(6):
            a = i*math.tau/6 + t
            end = (x+math.cos(a)*radius, y-math.sin(a)*radius+70*age*age)
            p.line(end, (end[0]-math.cos(a)*5, end[1]+math.sin(a)*5), GOLD, 2)
    p.s.set_clip(None)
