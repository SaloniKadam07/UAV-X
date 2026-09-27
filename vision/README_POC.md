# Vision + Priority Detection — Stage 1 POC

Matches your actual repo files:
- `docs/module_interfaces.md` → Vision Module output: `{target_id, position, priority, confidence}`
- `docs/data_interfaces.md` → Mission Point format: `{id, position, priority, status}`

## Files
- `detector.py` — accepts a frame, detects ArUco markers as the "predefined
  target/marker", estimates a ground-plane position, computes a confidence score.
- `marker_priority.json` — **vision-owned** config mapping marker ID → priority.
  Not the same file as `config/mission.json` (that one holds the swarm's
  existing mission points P1/P2/P3, a different schema, owned by the
  swarm-communication branch — don't read a priority map out of it).
- `priority.py` — classifies a detected target as CRITICAL / HIGH / STABLE
  using `marker_priority.json`, with a built-in fallback if the file is missing.
- `mission_event.py` — two conversions:
  - `build_detection_result()` → exact Vision Module output contract
  - `to_mission_point()` → exact shared Mission Point format
- `interface.py` — **the only file Person 4 needs**: `get_detection_result()`
  and `get_mission_points()`.
- `test_vision.py` — standalone tests, generates its own sample marker
  images (no external files needed), run with `python test_vision.py`.

## Open question for the team — raise before Stage 2
Your task brief asks for `CRITICAL / STABLE / HIGH`. But `docs/data_interfaces.md`
and `config/mission.json` only show `NORMAL` and `HIGH` in actual use — `CRITICAL`
and `STABLE` aren't defined anywhere in the shared docs. Right now this module
outputs CRITICAL/HIGH/STABLE as-is (`TRANSLATE_TO_SWARM_VOCAB = False` in
`mission_event.py`). Two ways to resolve:
1. Person 2 updates swarm logic to also accept CRITICAL/STABLE, or
2. Flip `TRANSLATE_TO_SWARM_VOCAB = True` in `mission_event.py` to auto-map
   STABLE→NORMAL, CRITICAL→HIGH before handoff.
Decide with the group and pick one — don't let this sit as a silent mismatch.

## Before merging
1. Confirm marker IDs in `marker_priority.json` match whatever physical/test
   markers you're actually printing/using.
2. `requirements.txt` is currently empty — add `opencv-python` (and `numpy`
   if not pulled in automatically) since this is a shared project file.
3. Run `python test_vision.py` from inside `vision/` — should print "All
   Stage 1 vision tests passed."

## What Person 4 imports
```python
from interface import get_detection_result, get_mission_points

get_detection_result("some_frame.jpg")
# -> [{"target_id": "T1", "position": [x, y, z], "priority": "HIGH", "confidence": 0.92}]

get_mission_points("some_frame.jpg")
# -> [{"id": "T1", "position": [x, y, z], "priority": "HIGH", "status": "PENDING"}]
```
Both also accept an already-loaded frame (numpy array) instead of a path —
useful for a live webcam loop via `cv2.VideoCapture`.
