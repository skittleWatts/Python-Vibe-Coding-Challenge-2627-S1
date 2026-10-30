# Explain ScrapLab in your own words

## The idea

ScrapLab makes building the main activity. A player can make a design that looks sensible but fails on a ramp, then use the centre-of-mass marker and measurements to improve it. The arena gives the improved robot another job to do.

## Six ideas to understand

1. **A blueprint is data.** Each part has a type, position, rotation, scale and settings. JSON stores those values. Loading does not execute code. Physics uses a copy so pressing Reset reconstructs the same original machine.
2. **Mass depends on material and area.** In this simplified side view, mass is area times kilograms per square metre. A battery contributes mass at its actual location. Its weight is deliberately exaggerated for a clear experiment.
3. **The centre of mass is a weighted average.** In one dimension, `COM_y = sum(part_mass * part_y) / total_mass`. Moving a heavy battery changes this average much more than moving a light beam. A wedge uses its triangular centroid, not the centre of its bounding rectangle.
4. **Rigid and rotating connections do different jobs.** Welded parts share one rigid body. A wheel has its own body attached by a pivot, so it can rotate without detaching. The motor applies torque between the frame and wheel, and the frame gets the opposite reaction.
5. **Friction produces driving force.** The wheel pushes on the ground. The ground pushes back. In the air, spinning the wheels can rotate the frame but cannot create horizontal momentum for the whole robot. More torque does not help if the wheel cannot grip.
6. **Small fixed timesteps make comparisons fair.** Pymunk advances by 1/240 second every step. A slower graphics frame causes several small physics steps, not one giant step. The benchmark gives both designs the same timed controls.

## Why the tall robot tips

The wheel contacts make a support region. As the robot climbs, the vertical line through its high centre of mass moves toward the downhill contact. Once the contact forces cannot keep it balanced, gravity produces a turning moment and it tips. Acceleration, motor reaction and collisions also matter, so this is a dynamic simulation rather than just a static tipping-angle formula.

The overlay lets you see this geometry. The measured statement is: “the chassis passed 65° from upright.” The explanation about balance comes from the physical model; the app does not claim to diagnose every possible failure.

Lowering the battery changes neither total mass nor motor settings. In the verified experiment it cuts peak tilt from 110.2° to 25.5° and lets the machine climb the incline.

## Questions a teacher might ask

**Why not make every beam a separate body?**

A welded frame should behave as one rigid object. Many stiff constraints can wobble or destabilize a game solver. A compound body is simpler, faster and easier to understand; only moving parts need separate bodies.

**Is the battery realistic?**

Its mass affects the mechanics. Its power rule is a deliberate abstraction: each pack permits a total of 120 N m in motor caps. There is no electrical circuit or battery depletion model.

**What is “motor load” measuring?**

The solver reports angular impulse from its latest step. Dividing by the step duration estimates the average torque over that step. It is useful feedback, but it is not a real torque sensor or engineering-grade stress analysis.

**What did AI do?**

AI helped implement and test the software from the project brief. Explain your role accurately: the concept, the features you chose, the designs you built, the experiments you tried and the changes you understand. Do not claim to have handwritten code you did not write. Keep a short record of your own design experiments.

**How do you know the demonstration is not faked?**

`verify_demo.py` creates two normal blueprints and feeds them into the same physics class. It changes only the battery location. Automated tests check tipping and climbing outcomes, motor limits, horizontal momentum in free fall, and render-rate independence. The desktop drag-and-retest demonstration was also performed.

**What would you add next?**

Choose one: suspension, a second test course, a replay with the old design, or multi-part articulated tools. Explain the tradeoff: suspension needs more joints and tuning; replays need reproducible state; destructibility needs load thresholds and safe constraint removal. Those features are not claimed as implemented.

## Three small personal experiments

- Build a named robot from Blank, save it, and show why every axle is connected.
- Reverse one wheel motor, predict the result, run a test, then explain what happened.
- Change the mast from foam to steel. Record mass and maximum tilt before and after.

Write a few sentences about your own observations. That will make the demonstration yours and give you something concrete to discuss.
