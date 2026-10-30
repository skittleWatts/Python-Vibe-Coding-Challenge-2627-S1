"""The parts catalogue. Edit these numbers to make ScrapLab your own.

Units: metres, kilograms, seconds, radians, newtons. Density is kg/m²:
an explicit planar approximation, not the bulk density of real materials.
"""
from dataclasses import dataclass
from math import cos, sin, radians, pi

MATERIALS = {"alloy": 12.0, "steel": 28.0, "foam": 3.5}


@dataclass(frozen=True)
class Spec:
    label: str
    width: float
    height: float
    density: float
    color: tuple
    joint: str = "weld"
    description: str = ""
    friction: float = 0.6


CATALOG = {
    "chassis": Spec("Chassis plate", 1.8, .26, 12, (106, 149, 169), description="The backbone. Touch other metal to weld."),
    "plate": Spec("Wide plate", 2.6, .30, 12, (106, 149, 169), description="A wider base increases your wheelbase."),
    "beam": Spec("Short beam", 1.1, .16, 12, (130, 163, 174), description="Light structure. R rotates by 15 degrees."),
    "long_beam": Spec("Long beam", 2.6, .16, 12, (130, 163, 174), description="Reach higher. Tall structures can tip."),
    "wheel": Spec("Drive wheel", .68, .68, 9, (63, 76, 90), "axle", "Integrated axle. Centre must sit on metal.", 1.25),
    "big_wheel": Spec("Trail wheel", .94, .94, 12, (71, 85, 98), "axle", "More grip and clearance; more inertia.", 1.65),
    "battery": Spec("Battery", .64, .48, 190, (119, 231, 181), description="Heavy! Each pack enables 120 N m of motors."),
    "ballast": Spec("Armour / ballast", .50, .42, 65, (170, 154, 134), description="Dense rigid block for armour or balance."),
    "wedge": Spec("Wedge", .90, .50, 28, (235, 180, 88), description="Triangular contact geometry pushes and lifts."),
    "arm": Spec("Powered lifter", 1.35, .16, 28, (237, 166, 89), "motor", "Left end is a motor pivot. Q / E to swing."),
    "pivot": Spec("Passive arm", 1.1, .14, 12, (178, 160, 219), "pivot", "Free hinge at left end; gravity can swing it."),
}


def rotate(point, angle):
    a = radians(angle)
    x, y = point
    return (x*cos(a)-y*sin(a), x*sin(a)+y*cos(a))


def dimensions(part):
    s = CATALOG[part.kind]
    return s.width * part.scale, s.height * part.scale


def vertices(part):
    w, h = dimensions(part)
    pts = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
    if part.kind == "wedge":
        pts.pop(2)
    return [(part.x+x, part.y+y) for x, y in (rotate(p, part.angle) for p in pts)]


def centroid(part):
    if part.kind == "wedge":
        w, h = dimensions(part)
        x, y = rotate((-w/6, -h/6), part.angle)
        return part.x+x, part.y+y
    return part.x, part.y


def mass(part):
    spec = CATALOG[part.kind]
    w, h = dimensions(part)
    density = MATERIALS[part.material] if part.kind in {"chassis", "plate", "beam", "long_beam", "arm", "pivot"} else spec.density
    area = pi*(w/2)**2 if spec.joint == "axle" else w*h
    if part.kind == "wedge":
        area *= .5
    return density*area


def anchor(part):
    if CATALOG[part.kind].joint in {"motor", "pivot"}:
        dx, dy = rotate((-dimensions(part)[0]/2, 0), part.angle)
        return part.x+dx, part.y+dy
    return part.x, part.y


def contains(part, point, margin=0):
    x, y = rotate((point[0]-part.x, point[1]-part.y), -part.angle)
    w, h = dimensions(part)
    if CATALOG[part.kind].joint == "axle":
        return x*x+y*y <= (w/2+margin)**2
    if not (-w/2-margin <= x <= w/2+margin and -h/2-margin <= y <= h/2+margin):
        return False
    return part.kind != "wedge" or y <= -h/w*x + margin


def penetration(a, b):
    """Convex polygon SAT: positive penetration, negative separating gap."""
    aa, bb = vertices(a), vertices(b)
    smallest = float("inf")
    for poly in (aa, bb):
        for i, p in enumerate(poly):
            q = poly[(i+1) % len(poly)]
            dx, dy = q[0]-p[0], q[1]-p[1]
            length = (dx*dx+dy*dy)**.5
            axis = (-dy/length, dx/length)
            pa = [x*axis[0]+y*axis[1] for x, y in aa]
            pb = [x*axis[0]+y*axis[1] for x, y in bb]
            smallest = min(smallest, min(max(pa), max(pb))-max(min(pa), min(pb)))
    return smallest
