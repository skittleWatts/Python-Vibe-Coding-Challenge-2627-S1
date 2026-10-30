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
    # When a shove stalls, physically reverse and take another run at it.
    # This only issues ordinary controls; no teleport, force boost or extra grip.
    if sim.time-sim.ai_probe_time >= 1.4:
        if abs(rival.com.x-sim.ai_probe_x) < .18 and abs(dx) < 3:
            sim.ai_backoff_until = sim.time+.85
        sim.ai_probe_time, sim.ai_probe_x = sim.time, rival.com.x
    if sim.time < sim.ai_backoff_until:
        direction = -direction
    # Same controls, torque limits and battery rule as the player.
    if rival.com.x < -4.8:
        direction = 1
    if rival.com.x > 4.8:
        direction = -1
    spinner = any(p.kind == "spinner" for p in rival.blueprint.parts)
    swing = 1 if spinner or sim.time % 1.8 < 1.0 else -1
    return {"drive": direction * .85, "arm": swing if abs(dx) < 3 else 1}
