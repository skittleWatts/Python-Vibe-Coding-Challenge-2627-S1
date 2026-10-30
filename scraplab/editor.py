"""Workshop interaction state, independent of window layout and physics."""
from .blueprint import Blueprint, Part, MAX_PARTS
from .parts import contains, WEAPONS
import uuid


class Editor:
    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.selected = None
        self.undo_stack, self.redo_stack = [], []
        self.snap = True
        self.drag = None

    @property
    def part(self):
        return next((p for p in self.blueprint.parts if p.uid == self.selected), None)

    def checkpoint(self):
        self.undo_stack.append(self.blueprint.to_dict())
        self.undo_stack = self.undo_stack[-80:]
        self.redo_stack.clear()

    def undo(self):
        if self.undo_stack:
            self.redo_stack.append(self.blueprint.to_dict())
            self.blueprint = Blueprint.from_dict(self.undo_stack.pop())
            self.selected = None

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append(self.blueprint.to_dict())
            self.blueprint = Blueprint.from_dict(self.redo_stack.pop())
            self.selected = None

    def replace(self, blueprint):
        self.checkpoint()
        self.blueprint = blueprint
        self.selected = None
        self.drag = None

    def hit(self, point):
        return next((p for p in reversed(self.blueprint.parts) if contains(p, point, .025)), None)

    def begin_move(self, point):
        part = self.hit(point)
        self.selected = part.uid if part else None
        if part:
            self.checkpoint()
            self.drag = (part.x-point[0], part.y-point[1], False)

    def begin_new(self, kind, point):
        if len(self.blueprint.parts) >= MAX_PARTS:
            return False
        self.checkpoint()
        part = Part(kind, *point, control="arm" if kind in WEAPONS else "drive",
                    speed=10 if kind == "spinner" else 3 if kind == "flipper" else 2 if kind == "arm" else 5,
                    torque=70 if kind == "flipper" else 40 if kind == "spinner" else 35)
        self.blueprint.parts.append(part)
        self.selected = part.uid
        self.drag = (0, 0, True)
        return True

    def move(self, point):
        if self.drag and self.part:
            x, y = point[0]+self.drag[0], point[1]+self.drag[1]
            if self.snap:
                x, y = round(x*10)/10, round(y*10)/10
            self.part.x = max(-8, min(8, x))
            self.part.y = max(-5, min(7, y))

    def drop(self, inside):
        if self.drag and not inside:
            self.blueprint = Blueprint.from_dict(self.undo_stack.pop())
            self.selected = None
        self.drag = None

    def change(self, field, value):
        if self.part:
            self.checkpoint()
            setattr(self.part, field, value)

    def rotate(self, degrees=15):
        if self.part:
            self.change("angle", (self.part.angle+degrees+180) % 360-180)

    def delete(self):
        if self.part:
            self.checkpoint()
            self.blueprint.parts.remove(self.part)
            self.selected = None

    def duplicate(self):
        if self.part and len(self.blueprint.parts) < MAX_PARTS:
            self.checkpoint()
            copy = Part(**vars(self.part))
            copy.uid = uuid.uuid4().hex[:10]
            copy.x = min(8, copy.x+.2)
            copy.y = min(7, copy.y+.2)
            self.blueprint.parts.append(copy)
            self.selected = copy.uid
