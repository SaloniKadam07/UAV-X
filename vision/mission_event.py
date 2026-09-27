"""
mission_event.py
Person 3 - Vision + Priority Detection Lead

Two output shapes, matching the two relevant docs exactly:

1. build_detection_result() -> the Vision Module output contract from
   docs/module_interfaces.md:
     {"target_id", "position", "priority", "confidence"}

2. to_mission_point() -> the shared Mission Point format from
   docs/data_interfaces.md, so the swarm module can drop a detected
   target straight into its mission point list alongside P1/P2/P3:
     {"id", "position", "priority", "status"}

   Mission Point has no "confidence" field in data_interfaces.md, so it's
   dropped here (not lost - it's still in the Vision Module output from
   build_detection_result(), which the swarm module can log/inspect
   separately if useful).
"""

from typing import Dict

from priority import classify_priority, load_priority_map

# See the vocabulary-mismatch note in priority.py. Set this True once the
# team decides vision's CRITICAL/HIGH/STABLE should be translated down to
# the NORMAL/HIGH values actually used in config/mission.json - leave it
# False (pass-through) until that's agreed.
TRANSLATE_TO_SWARM_VOCAB = False

_SWARM_VOCAB_TRANSLATION = {
    "CRITICAL": "HIGH",
    "HIGH": "HIGH",
    "STABLE": "NORMAL",
}


def build_detection_result(detection: dict) -> Dict:
    """
    detection: one item from TargetDetector.detect(), i.e.
        {"target_id": "T1", "position": [x, y, z], "confidence": 0.9, "raw": ...}

    Returns docs/module_interfaces.md's Vision Module output exactly:
        {"target_id", "position", "priority", "confidence"}
    """
    priority_map, fallback = load_priority_map()
    priority = classify_priority(
        detection["target_id"], detection["confidence"], priority_map, fallback
    )

    return {
        "target_id": detection["target_id"],
        "position": detection["position"],
        "priority": priority,
        "confidence": detection["confidence"],
    }


def to_mission_point(detection_result: Dict, status: str = "PENDING") -> Dict:
    """
    Converts a Vision Module output (above) into docs/data_interfaces.md's
    Mission Point format, ready for the swarm module to add to its
    mission point list:
        {"id", "position", "priority", "status"}
    """
    priority = detection_result["priority"]
    if TRANSLATE_TO_SWARM_VOCAB:
        priority = _SWARM_VOCAB_TRANSLATION.get(priority, priority)

    return {
        "id": detection_result["target_id"],
        "position": detection_result["position"],
        "priority": priority,
        "status": status,
    }
