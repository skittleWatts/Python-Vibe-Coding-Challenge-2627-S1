"""Player-facing motor feedback, derived from actual solver state."""
import math


def arm_feedback(robot, dt, controls):
    arms = [(part, motor) for part, motor in robot.motors if part.kind == "arm"]
    if not arms:
        passive = any(p.kind == "pivot" for p in robot.blueprint.parts)
        return {"title": "PASSIVE HINGE" if passive else "NO POWERED ARM", "detail": "A passive hinge has no motor." if passive else "Add a Powered lifter in the workshop.", "state": "idle", "angle": None}
    part, motor = arms[0]
    angle = math.degrees(motor.b.angle-motor.a.angle)
    command = controls.get(part.control, 0)*part.direction
    torque = motor.impulse/dt
    speed = abs(motor.a.angular_velocity-motor.b.angular_velocity)
    result = {"angle": angle, "torque": torque, "cap": motor.max_force, "count": len(arms), "state": "ready"}
    if robot.power_budget == 0:
        result.update(title="NO BATTERY", detail="Add a battery to power the arm.", state="warning")
    elif part.control == "off" or part.torque == 0:
        result.update(title="MOTOR DISABLED", detail="Set Control: ARM and torque above zero.", state="warning")
    elif part.control != "arm":
        result.update(title="LINKED TO DRIVE", detail="This arm uses A / D. Change Control to ARM for E / Q.", state="warning")
    elif angle >= 98 and command < 0 or angle <= -63 and command > 0:
        result.update(title="AT JOINT LIMIT", detail="Hold the opposite control to swing back.", state="warning")
    elif abs(command) > .01 and motor.max_force > 0 and torque >= motor.max_force*.95 and speed < .15:
        result.update(title="AT TORQUE LIMIT", detail="Try reversing, a shorter arm, or more torque.", state="warning")
    elif abs(command) > .01:
        result.update(title="ARM MOVING", detail="Release to brake. Reverse to swing back.", state="active")
    else:
        result.update(title="ARM READY", detail="Hold E / Up or Q / Down. Tap the buttons to nudge; hold to move.")
    return result
