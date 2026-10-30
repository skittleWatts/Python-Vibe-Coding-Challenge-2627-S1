"""Deterministic scenery and controls; no design-specific physics tricks."""
BENCHMARK_SECONDS = 12.0
RAMP = [(4, 0), (9, 2.35), (13, 2.35)]


def benchmark_controls(t):
    # Settle, smoothly engage, then drive. Same input for every construction.
    return {"drive": min(1.0, max(0.0, (t-.6)/.8)), "arm": 0.0}


def opponent_controls(sim):
    p, rival = sim.robot, sim.opponent
    dx = p.com.x - rival.com.x
    direction = 1 if dx > 0 else -1
    # Same controls, torque limits and battery rule as the player.
    if rival.com.x < -4.8:
        direction = 1
    if rival.com.x > 4.8:
        direction = -1
    return {"drive": direction * .85, "arm": 1 if abs(dx) < 2.6 else -.3}
