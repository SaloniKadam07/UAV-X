"""
swarm/task_allocator.py

Multi-factor UAV selection for mission assignment.
Goes beyond simple highest-battery by scoring candidates on:
  - battery level
  - distance to mission target
  - mission priority
  - network connectivity (degree)
  - current UAV role / availability
"""

import math
import logging

from swarm.constants import (
    ROLE_RELAY, ROLE_STANDBY, ROLE_MISSION,
    STATUS_IDLE, STATUS_ON_MISSION, STATUS_FAILED, STATUS_RELAY,
    PRIORITY_MAP,
    BATTERY_MIN_MISSION,
    WEIGHT_BATTERY, WEIGHT_DISTANCE, WEIGHT_PRIORITY,
    WEIGHT_CONNECTIVITY, WEIGHT_ROLE,
    GCS_NODE_ID,
)

logger = logging.getLogger(__name__)


def _euclidean(p1: dict, p2: dict) -> float:
    return math.sqrt(
        (p1["x"] - p2["x"]) ** 2 +
        (p1["y"] - p2["y"]) ** 2 +
        (p1.get("z", 0) - p2.get("z", 0)) ** 2
    )


def score_uav(
    uav: dict,
    mission: dict,
    network_graph,
    max_distance: float = 2000.0,
    max_degree: int = 5,
) -> float | None:
    """
    Compute a composite score for assigning *mission* to *uav*.

    Returns float in [0, 1] or None if the UAV is ineligible.
    """
    # ── Hard filters (instant disqualify) ──────────────────
    if uav["status"] == STATUS_FAILED:
        return None
    if uav["status"] == STATUS_RELAY and uav["role"] == ROLE_RELAY:
        return None  # actively relaying — don't pull
    min_bat = mission.get("requirements", {}).get("min_battery", BATTERY_MIN_MISSION)
    if uav["battery"] < min_bat:
        return None
    if not network_graph.can_reach_gcs(uav["id"]):
        return None  # can't communicate — can't accept mission

    # ── Battery score (higher is better) ──────────────────
    battery_score = uav["battery"] / 100.0

    # ── Distance score (closer is better) ─────────────────
    dist = _euclidean(uav["position"], mission["target"])
    distance_score = max(0.0, 1.0 - dist / max_distance)

    # ── Priority multiplier ───────────────────────────────
    # Higher-priority missions weight the *best* factors more aggressively.
    pri_str = mission.get("priority", "medium")
    pri_val = PRIORITY_MAP.get(pri_str, 2)
    priority_score = pri_val / 4.0  # normalized to [0.25, 1.0]

    # ── Connectivity score ────────────────────────────────
    degree = network_graph.node_degree(uav["id"])
    connectivity_score = min(degree / max_degree, 1.0)

    # ── Role / availability score ─────────────────────────
    if uav["status"] == STATUS_IDLE and uav["role"] in (ROLE_MISSION, ROLE_STANDBY):
        role_score = 1.0
    elif uav["status"] == STATUS_IDLE:
        role_score = 0.8
    elif uav["status"] == STATUS_ON_MISSION:
        role_score = 0.2  # already busy
    else:
        role_score = 0.1

    # ── Weighted sum ──────────────────────────────────────
    score = (
        WEIGHT_BATTERY * battery_score
        + WEIGHT_DISTANCE * distance_score
        + WEIGHT_PRIORITY * priority_score
        + WEIGHT_CONNECTIVITY * connectivity_score
        + WEIGHT_ROLE * role_score
    )
    return round(score, 4)


def select_uav(
    uav_states: list[dict],
    mission: dict,
    network_graph,
) -> dict | None:
    """
    Pick the single best UAV for a mission.

    Returns:
        {"uav_id": str, "score": float, "scores_breakdown": {...}}
        or None if nobody qualifies.
    """
    best = None

    for uav in uav_states:
        s = score_uav(uav, mission, network_graph)
        if s is None:
            continue
        entry = {"uav_id": uav["id"], "score": s}
        if best is None or s > best["score"]:
            best = entry

    if best:
        logger.info(
            "Selected UAV %s for mission %s (score=%.3f)",
            best["uav_id"], mission["id"], best["score"],
        )
    else:
        logger.warning("No eligible UAV for mission %s", mission["id"])

    return best


def rank_uavs(
    uav_states: list[dict],
    mission: dict,
    network_graph,
) -> list[dict]:
    """
    Return all eligible UAVs ranked by score (descending).
    Useful for Person 4's integration to inspect alternatives.
    """
    scored = []
    for uav in uav_states:
        s = score_uav(uav, mission, network_graph)
        if s is not None:
            scored.append({"uav_id": uav["id"], "score": s})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
