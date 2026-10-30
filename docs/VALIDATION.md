# Validation record

Updated **29 October 2026** for ScrapLab **1.1.0**.

## Tested environment

Windows, CPython **3.14.7**, pygame-ce **2.5.8**, Pymunk **7.3.1**, cffi **2.1.1**, pycparser **3.12**. The project has a dedicated `.venv`. `pip check` passed. No separate `pygame` distribution is installed.

## Automated checks

**38 tests passed** using:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests exercise real behavior:

- JSON round trips; finite/bounded data; invalid, disconnected and overlapping builds; transformed attachments; material mass.
- Compound mass and centre of mass; actual motor torque caps, battery budget, reaction torque, grounded traction and absence of airborne propulsion.
- Identical fixed-step benchmark results under 30, 60 and 144 Hz frame delivery; measured tipping and successful climb for the paired designs; arm limits and arena rules.
- Real pygame events through the application for drag/drop, rotation, duplication, deletion, undo, save/load, pause/step/reset/edit, resize mapping and corrupt-file handling.
- Keyboard and arrow input moving the player's joint in both directions; mouse holds and quick nudges; release, focus-loss and modal input clearing.
- Actual practice angles required for completion; missing battery, drive assignment and joint-stop explanations; benchmark controls visibly disabled.
- Recovery surviving a new application instance; preview mode preserving an existing recovery file.

Application screens and modal dialogs render through the dummy display in tests. Sound generation was checked with SDL's dummy audio driver. Physical speaker output has **not** been assessed. The normal game tolerates an unavailable audio device.

## Measured engineering demonstration

`verify_demo.py` runs the same 12-second controls on both bundled presets. Only battery height differs. It does not read or overwrite the user's recovery draft.

| Design | Displacement | Peak chassis tilt | Outcome |
| --- | ---: | ---: | --- |
| Tall order, battery y = 2.40 m | 2.22 m | 110.2° | Tipped, no summit |
| Low rider, battery y = 0.38 m | 18.23 m | 25.5° | Summit at 7.63 s, no tip |

The desktop demonstration also moved the battery by mouse to the snapped y = 0.40 m mount, then ran the second benchmark and exported the notebook: **18.25 m**, **25.5°**, summit at **7.64 s**. See `gui_demo_results.json` and `gui_demo_measurements.csv`. The original edited blueprint remains in the local user's saves; it is not included in the source release.

## Desktop checks

The game was opened in a native Windows window, including through **launch.cmd**. Checks included workshop part placement/material editing, the battery drag experiment, measured comparison/export, and switching to the arena. Launching from another working directory also succeeded.

For the 1.1 arm controls, clicking the actual visible **E / UP** button moved the arm angle from about -4° to +4°. Clicking **Q / DOWN** then lowered it to about -25°, with geometry visibly moving. Sustained keyboard and mouse holds were verified through the pygame event integration tests; automated native key taps were too brief to establish sustained physical-keyboard behavior.

An idle Forklift versus Copperhead ended at **8.99 s** in the desktop window. The result correctly displayed **COPPERHEAD WINS** and **Your robot fell below the arena**, with Retry and Edit Design controls. This is an observed match, not a guaranteed outcome for a player-controlled robot.

The documentation PNGs are application renders from actual simulated states, not concept art. They show the current UI but are not all screenshots from manual play.

## Release check

The source ZIP passed its ZIP integrity check. A fresh extraction launched the Forklift practice scenario using the existing tested interpreter and dependencies with a dummy display. The archive includes source, tests, examples, documentation and launch/setup scripts; it excludes the virtual environment, recovery data and user saves. Installing dependencies from scratch on a second computer has not been tested.

## Repository and PyCharm handoff

The project was copied into the existing GitHub repository with the original assignment README preserved as `docs/CHALLENGE.md`. A fresh repository-local `.venv` installed the pinned dependencies successfully, `pip check` passed, and all 38 tests passed there. The test runner needed a writable workspace TEMP directory under the automation sandbox; no application change was required.

With `main.py` open in the existing PyCharm project, clicking its green Run button launched the game successfully using the repository's interpreter. Local saves and the recovered draft were retained. Git's ignore rules were checked for the virtual environment, recovery data and named saves. This handoff did not commit or push the project.

## Coverage limits

Only the listed Windows/Python/package combination has been exercised. Other platforms, Python versions, gamepads, long-duration play and unusual display scaling are not verified. This is a complete playable engineering sandbox within the documented 2D scope; it does not implement breakable parts, suspension or arbitrary articulated chains. See the README for the physics assumptions.
