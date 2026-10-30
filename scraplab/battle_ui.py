"""Battle lobby, score broadcasts, and match rewards."""
from .render import PANEL, PANEL2, LINE, INK, MUTED, GOLD, TEAL, RED


def draw_lobby(app):
    p, record = app.p, app.battle_record
    p.text("THE CRUCIBLE / BATTLE WORKS", (230, 142), 12, GOLD, True)
    p.text("Build a rival. Become a rival.", (230, 177), 33, INK, True)
    p.text("YOUR RECORD", (230, 235), 11, MUTED, True)
    p.text(f"{record.wins} W   {record.losses} L   {record.draws} D", (230, 258), 25, TEAL, True)
    p.text(f"BEST {record.best}    /    STREAK {record.streak}", (580, 263), 18, GOLD, True)
    p.text(f"{record.rank}  /  {record.total_points} CAREER POINTS", (230, 302), 13, MUTED, True)
    for i, (name, style) in enumerate([("Copperhead", "Wedge + lifter"), ("Whirlwind", "Continuous spinner"), ("Kickback", "Power flipper")]):
        x = 230+i*275
        app.button((x, 346, 258, 47), name.upper(), lambda n=name: setattr(app, "rival_name", n),
                   TEAL if app.rival_name == name else None, active=app.rival_name == name)
        p.text(style, (x+12, 404), 15, MUTED)
    p.panel((230, 449, 808, 122), PANEL2, LINE, 9)
    p.text("SCORE THE HIT. FINISH THE FIGHT.", (247, 464), 13, GOLD, True)
    p.wrap("Rams: 10–30 pts. Weapon contact: +15. Ring-out or 3s overturned: win +250. At 45s, impact points decide; equal points draw. Ground contact earns nothing.", (247, 491), 764, 16, INK, 23)
    p.fit_text("YOUR BUILD / " + app.editor.blueprint.name, (230, 592), 800, 17, TEAL, True)
    p.text("A / D drive. E / Q operate weapons. Same parts and limits for both robots.", (230, 622), 14, MUTED)
    app.button((230, 661, 390, 40), "START MATCH  /  ENTER", lambda: app.start("arena"), GOLD)
    app.button((638, 661, 400, 40), "BACK", lambda: setattr(app, "modal", None))


def draw_battle_score(app):
    p, sim = app.p, app.sim
    a, b = sim.battle.points
    if sim.result:
        p.panel((40, 317, 942, 117), PANEL, GOLD, 10)
        p.text(f"YOU  {a:03d}     :     {b:03d}  {sim.opponent_name.upper()}", (60, 331), 26, TEAL, True)
        bonus = "FINISH BONUS +250" if any(e[3] == "FINISH BONUS" for e in sim.battle.events) else "NO FINISH BONUS"
        p.text(f"{sim.battle.hits[0]} clean hits   /   {sim.battle.hits[1]} rival hits     |     {bonus}", (60, 373), 15, MUTED)
        record = app.battle_record
        p.text(f"{record.rank}   /   {record.wins} W  {record.losses} L  {record.draws} D   /   BEST {record.best}", (60, 404), 13, GOLD, True)
        app.button((776, 337, 188, 36), "CHANGE RIVAL", lambda: app.show_modal("battle"), GOLD)
    else:
        p.panel((338, 195, 372, 82), PANEL, LINE, 9)
        p.text("YOU", (353, 205), 11, TEAL, True)
        p.fit_text(sim.opponent_name.upper(), (567, 205), 126, 11, RED, True)
        p.text(f"{a:03d}", (353, 226), 29, TEAL, True)
        p.text(f"{b:03d}", (622, 226), 29, RED, True)
        p.text(f"{min(45, max(0, 47-sim.time)):04.1f}s", (520, 242), 21, GOLD, True, True)
        p.text("MATCH POINTS", (520, 268), 9, MUTED, True, True)
        events = [e for e in sim.battle.events if sim.time-e[0] < 1.7][-2:]
        for i, (_, side, points, label, _) in enumerate(events):
            color = TEAL if side == 0 else RED
            p.panel((338, 291+i*37, 372, 31), PANEL2, color, 6)
            p.text(f"{'YOU' if side == 0 else 'RIVAL'}  /  {label}  +{points}", (524, 306+i*37), 14, color, True, True)
