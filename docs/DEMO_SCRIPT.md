# 60–90 second demonstration

Preparation: launch ScrapLab, dismiss the field guide, choose Examples > Tall order. Keep the default wheel settings. Practice dragging the battery down to x = 0, y = 0.4 m. Use the same benchmark twice. Start with a fresh run so the previous attempt is clear.

| Time | Action | Suggested explanation |
| --- | --- | --- |
| 0–10 s | Show the workshop; point to the parts drawer and inspector. | “ScrapLab is a robot engineering sandbox. I can construct a machine, test it, and use measurements to improve it.” |
| 10–24 s | Press F6; let the 12-second benchmark finish. Toggle Tab. | “This machine has a heavy battery high up. Its wheels have real torque limits and ground friction. On the ramp it tips. The gold marker is its centre of mass.” |
| 24–37 s | Esc. Click the battery, then drag it straight down to the low mount, y about 0.4 m. | “I will change only the battery position. The robot keeps the same mass, wheel size, motor limits and test controls.” |
| 37–51 s | Press F6; wait for the second full benchmark. | “The program repeats the same driving sequence. This time the machine climbs the ramp and passes the summit gate upright.” |
| 51–64 s | Click Compare. Point to both values and traces. | “Peak tilt fell from about 110 degrees to 26 degrees. These are measurements from the simulation, and I can export the data as CSV.” |
| 64–80 s | Close Compare, Esc to edit, then F7 and Enter. Hold D after the countdown. | “Now the design can compete. The opponent uses the same parts and physics. A ring-out or three seconds upside down ends the match; impacts also earn points.” |
| 80–90 s | Pause if useful. | “Python runs the editor and game loop. pygame-ce draws the game, and Pymunk handles the rigid-body physics. This is a simplified 2D model, so it is for experiments and play, not real robot certification.” |

If short on time, end after the comparison at about 65 seconds. If the battery misses the mount, the editor marks the error; drag it onto the mast before starting again. Avoid loading Low rider for the main demonstration: making the change live shows that the editor and simulation really work.

The bundled Low rider is a backup/reference recipe, not a different physics model. The match outcome is not guaranteed or scripted; the benchmark outcome is reproducibly tested for the supplied designs.
