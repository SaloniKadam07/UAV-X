"""
priority.py
Person 3 - Vision + Priority Detection Lead

Classifies a detected target by priority: CRITICAL / HIGH / STABLE.

IMPORTANT - read before merging:
config/mission.json is NOT used here. It holds the swarm module's existing
mission points (id/position/priority/status for P1, P2, P3) - a different
schema, already populated, owned by the swarm-communication branch. Reading
a "target_priorities" dict out of it would be wrong.

Instead, this module owns a small local config: marker_priority.json,
sitting next to this file in vision/. It maps a detected marker ID to a
priority level.

KNOWN VOCABULARY MISMATCH - raise this with the team before Stage 2:
Your task brief asks for CRITICAL / STABLE / HIGH, which is what this
module uses. But docs/data_interfaces.md and config/mission.json only
show NORMAL and HIGH in actual use. Options to reconcile:
  (a) swarm module is updated to also accept CRITICAL/STABLE, or
  (b) vision maps its 3 levels down to NORMAL/HIGH before handing off
      (e.g. STABLE -> NORMAL, CRITICAL -> HIGH) via a translation step
      in mission_event.py's to_mission_point().
Not resolved automatically here since it's a cross-module decision -
flag it in the group chat.
"""

import json
import os
from typing import Dict, Tuple

VALID_PRIORITIES = ("CRITICAL", "HIGH", "STABLE")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "marker_priority.json")

_DEFAULT_MAP = {"1": "CRITICAL", "2": "HIGH", "3": "HIGH"}
_DEFAULT_FALLBACK = "STABLE"


def load_priority_map(config_path: str = CONFIG_PATH) -> Tuple[Dict[str, str], str]:
    """
    Returns (priority_map, fallback_priority).
    Falls back to built-in defaults if marker_priority.json isn't present -
    so this module still runs standalone for independent testing.
    """
    try:
        with open(config_path, "r") as f:
            cfg = json.load(f)
        priority_map = cfg.get("target_priorities", _DEFAULT_MAP)
        fallback = cfg.get("default_priority", _DEFAULT_FALLBACK)
        return priority_map, fallback
    except (FileNotFoundError, json.JSONDecodeError):
        return _DEFAULT_MAP, _DEFAULT_FALLBACK


def classify_priority(target_id: str, confidence: float,
                       priority_map: Dict[str, str] = None,
                       fallback: str = None) -> str:
    """
    Assigns CRITICAL / HIGH / STABLE to a target.

    target_id is expected in the form "T<marker_id>" (e.g. "T1"); the
    leading "T" is stripped to look up the raw marker ID in the config.

    Logic:
    1. Look up the marker ID in the configured priority map.
    2. If not found, use the fallback priority.
    3. Safety downgrade: a low-confidence detection shouldn't be allowed
       to trigger an urgent (CRITICAL/HIGH) re-tasking - drop one level
       rather than risk a false-priority mission event.
    """
    if priority_map is None or fallback is None:
        priority_map, fallback = load_priority_map()

    marker_key = target_id[1:] if target_id.startswith("T") else target_id
    priority = priority_map.get(marker_key, fallback)
    if priority not in VALID_PRIORITIES:
        priority = fallback if fallback in VALID_PRIORITIES else "STABLE"

    if confidence < 0.5 and priority == "CRITICAL":
        priority = "HIGH"
    elif confidence < 0.35 and priority == "HIGH":
        priority = "STABLE"

    return priority
