"""Versioned editable data, construction validation, and safe JSON persistence."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import math
import re
import uuid
from .parts import CATALOG, MATERIALS, mass, centroid, anchor, contains, penetration, dimensions

SCHEMA_VERSION = 1
MAX_PARTS = 60


@dataclass
class Part:
    kind: str
    x: float = 0
    y: float = 0
    angle: float = 0
    scale: float = 1
    material: str = "alloy"
    speed: float = 5
    torque: float = 35
    direction: int = 1
    control: str = "drive"
    grip: float = 1.0
    uid: str = field(default_factory=lambda: uuid.uuid4().hex[:10])


@dataclass
class Blueprint:
    name: str = "My scrap invention"
    parts: list[Part] = field(default_factory=list)

    def clone(self):
        return Blueprint.from_dict(self.to_dict())

    def to_dict(self):
        return {"schema_version": SCHEMA_VERSION, "name": self.name, "parts": [asdict(p) for p in self.parts]}

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported blueprint version. Expected schema_version: 1.")
        name, raw = data.get("name"), data.get("parts")
        if not isinstance(name, str) or not name.strip() or len(name) > 40:
            raise ValueError("Robot name must contain 1-40 characters.")
        if not isinstance(raw, list) or len(raw) > MAX_PARTS:
            raise ValueError("A blueprint may contain up to 60 parts.")
        parts, ids = [], set()
        for row in raw:
            try:
                p = Part(**row)
            except (TypeError, ValueError) as e:
                raise ValueError("Invalid part fields in JSON.") from e
            if not isinstance(p.kind, str) or p.kind not in CATALOG or not isinstance(p.material, str) or p.material not in MATERIALS:
                raise ValueError("Unknown part type or material.")
            for key, lo, hi in [("x", -8, 8), ("y", -5, 7), ("angle", -360, 360), ("scale", .5, 1.8), ("speed", .5, 12), ("torque", 0, 120), ("grip", .2, 2)]:
                v = getattr(p, key)
                if isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v) or not lo <= v <= hi:
                    raise ValueError(f"{key} must be a finite number between {lo} and {hi}.")
            if isinstance(p.direction, bool) or p.direction not in (-1, 1) or p.control not in ("drive", "arm", "off"):
                raise ValueError("Invalid motor direction or control assignment.")
            if not isinstance(p.uid, str) or not 1 <= len(p.uid) <= 40 or p.uid in ids:
                raise ValueError("Parts must have unique identifiers.")
            ids.add(p.uid)
            parts.append(p)
        return cls(name.strip(), parts)

    @property
    def total_mass(self):
        return sum(mass(p) for p in self.parts)

    @property
    def com(self):
        m = self.total_mass
        return tuple(sum(mass(p)*centroid(p)[i] for p in self.parts)/m for i in (0, 1)) if m else (0, 0)


def validate(bp):
    """Return (part id or None, actionable message) errors; never fix silently."""
    errors = []
    if not bp.parts:
        return [(None, "Start with a chassis plate from the parts drawer.")]
    rigid = [p for p in bp.parts if CATALOG[p.kind].joint == "weld"]
    if not rigid:
        return [(None, "Add a chassis or beam for the axles to attach to.")]
    # Overlapping/touching rigid parts are welded. Beams are mounting rails.
    connections = {p.uid: set() for p in rigid}
    overlaps = {}
    for i, a in enumerate(rigid):
        for b in rigid[i+1:]:
            overlap = penetration(a, b)
            overlaps[(a.uid, b.uid)] = overlap
            if overlap >= -.055:
                connections[a.uid].add(b.uid)
                connections[b.uid].add(a.uid)
    reached, pending = set(), [rigid[0].uid]
    while pending:
        uid = pending.pop()
        if uid not in reached:
            reached.add(uid)
            pending.extend(connections[uid]-reached)
    for p in rigid:
        if p.uid not in reached:
            errors.append((p.uid, "Unattached: move it until it touches connected metal."))
    structural = {"chassis", "plate", "beam", "long_beam"}
    for i, a in enumerate(rigid):
        for b in rigid[i+1:]:
            overlap = overlaps[(a.uid, b.uid)]
            # Rail mounting is intentional side-view overlap, not interpenetration.
            if a.kind not in structural and b.kind not in structural and overlap > .06:
                errors.append((b.uid, "Blocks intersect: separate the battery / ballast / wedge."))
            if a.kind in {"chassis", "plate"} and b.kind in {"chassis", "plate"} and overlap > .10:
                errors.append((b.uid, "Plates intersect: join them at an edge instead."))
    articulated = [p for p in bp.parts if CATALOG[p.kind].joint != "weld"]
    for p in articulated:
        if not any(r.uid in reached and contains(r, anchor(p), .055) for r in rigid):
            errors.append((p.uid, "Unattached pivot: put the gold axle dot onto rigid metal."))
    wheels = [p for p in articulated if CATALOG[p.kind].joint == "axle"]
    for i, a in enumerate(wheels):
        for b in wheels[i+1:]:
            if math.hypot(a.x-b.x, a.y-b.y) < (dimensions(a)[0]+dimensions(b)[0])/2-.02:
                errors.append((b.uid, "Wheels overlap: move the axles farther apart."))
    return errors


def safe_name(name):
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")[:40] or "robot"
    # Windows device names are reserved even when an extension is present.
    if name.upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
        name = "robot_" + name
    return name


def save(bp, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    Blueprint.from_dict(bp.to_dict())  # Validate schema even for unfinished drafts.
    path = directory / (safe_name(bp.name) + ".json")
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(bp.to_dict(), indent=2, allow_nan=False), encoding="utf-8")
    temp.replace(path)
    return path


def load(path):
    path = Path(path)
    if path.stat().st_size > 256_000:
        raise ValueError("Blueprint file is too large (maximum 256 KB).")
    try:
        return Blueprint.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, UnicodeError) as e:
        raise ValueError("This file is not valid UTF-8 blueprint JSON.") from e


def preset(name="Tall order"):
    if name == "Blank":
        return Blueprint("New invention")
    if name in ("Tall order", "Low rider"):
        return Blueprint(name, [
            Part("chassis", scale=1),
            Part("long_beam", 0, 1.25, angle=90, material="foam"),
            Part("wheel", -.70, -.10, torque=55), Part("wheel", .70, -.10, torque=55),
            Part("battery", 0, 2.40 if name == "Tall order" else .38),
        ])
    if name == "Whirlwind":
        return Blueprint(name, [Part("plate"),
            Part("big_wheel", -.92, -.08, torque=35), Part("big_wheel", .92, -.08, torque=35),
            Part("battery", -.45, .34), Part("beam", 1.18, .18),
            Part("spinner", 1.65, .18, torque=50, speed=10, control="arm")])
    if name == "Kickback":
        return Blueprint(name, [Part("plate"),
            Part("big_wheel", -.92, -.08, torque=30), Part("big_wheel", .92, -.08, torque=30),
            Part("battery", -.40, .34), Part("wedge", 1.38, .02, scale=.7),
            Part("flipper", 1.50, .04, torque=60, speed=4, control="arm")])
    return Blueprint("Forklift" if name == "Forklift" else "Copperhead", [
        Part("plate"), Part("big_wheel", -.92, -.08, torque=40), Part("big_wheel", .92, -.08, torque=40),
        Part("battery", -.25, .34),
        Part("wedge", 1.40, .04, scale=.8),
        Part("arm", 1.25, .18, angle=10, torque=30, speed=2, control="arm")
    ])
