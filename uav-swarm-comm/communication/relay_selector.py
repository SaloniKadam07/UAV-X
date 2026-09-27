"""
communication/relay_selector.py

Picks the best candidate UAV to serve as a relay
when one or more UAVs lose connectivity to GCS.
"""

import math
import logging

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from swarm.constants import (
    GCS_NODE_ID, ROLE_RELAY, ROLE_STANDBY, ROLE_MISSION,
    STATUS_IDLE, STATUS_RELAY, STATUS_FAILED,
    BATTERY_MIN_RELAY,
)

logger = logging.getLogger(__name__)


def _euclidean(p1: dict, p2: dict) -> float:
    return math.sqrt(
        (p1["x"] - p2["x"]) ** 2 +
        (p1["y"] - p2["y"]) ** 2 +
        (p1.get("z", 0) - p2.get("z", 0)) ** 2
    )


def _midpoint(positions: list[dict]) -> dict:
    """Geometric center of a list of {x, y, z} dicts."""
    n = len(positions)
    return {
        "x": sum(p["x"] for p in positions) / n,
        "y": sum(p["y"] for p in positions) / n,
        "z": sum(p.get("z", 0) for p in positions) / n,
    }


def select_relay(
    uav_states: list[dict],
    disconnected_ids: list[str],
    network_graph,
    gcs_position: dict | None = None,
) -> dict | None:
    """
    Choose the best UAV to act as a relay for disconnected UAVs.

    Selection criteria (scored):
      1. Must NOT be failed or already a relay on duty.
      2. Battery >= BATTERY_MIN_RELAY.
      3. Prefer standby/idle UAVs over those on active missions.
      4. Prefer UAVs closer to the ideal relay position (midpoint between
         the closest connected node and the disconnected cluster).
      5. Higher battery is a tiebreaker.

    Returns:
        dict with keys: relay_uav_id, target_position, score, connects_to
        or None if no candidate found.
    """
    if not disconnected_ids:
        logger.debug("select_relay called with no disconnected UAVs")
        return None

    if gcs_position is None:
        gcs_position = {"x": 0, "y": 0, "z": 0}

    # Build lookup
    state_map = {u["id"]: u for u in uav_states}

    # Find the positions of disconnected UAVs
    disc_positions = [
        state_map[uid]["position"]
        for uid in disconnected_ids if uid in state_map
    ]
    if not disc_positions:
        return None

    disc_center = _midpoint(disc_positions)

    # Find the nearest *connected* node to the disconnected cluster
    reachable = network_graph.get_all_reachable_from_gcs()
    connected_uavs = [
        u for u in uav_states
        if u["id"] in reachable and u["id"] != GCS_NODE_ID
           and u["status"] != STATUS_FAILED
    ]

    if not connected_uavs:
        # Only GCS is connected — relay target is midpoint between GCS and disc cluster
        bridge_anchor_pos = gcs_position
        bridge_anchor_id = GCS_NODE_ID
    else:
        # Pick the connected UAV closest to the disconnected cluster
        connected_uavs.sort(key=lambda u: _euclidean(u["position"], disc_center))
        bridge_anchor_pos = connected_uavs[0]["position"]
        bridge_anchor_id = connected_uavs[0]["id"]

    # Ideal relay position: midpoint between bridge anchor and disconnected center
    relay_target = _midpoint([bridge_anchor_pos, disc_center])

    # ── Score candidates ──────────────────────────────────
    candidates = []
    for u in uav_states:
        uid = u["id"]

        # Exclusion filters
        if uid in disconnected_ids:
            continue
        if u["status"] == STATUS_FAILED:
            continue
        if u["status"] == STATUS_RELAY and u["role"] == ROLE_RELAY:
            continue  # already serving as relay
        if u["battery"] < BATTERY_MIN_RELAY:
            continue

        # Score components
        dist_to_target = _euclidean(u["position"], relay_target)
        max_dist = 2000.0  # normalization cap
        dist_score = max(0.0, 1.0 - dist_to_target / max_dist)

        battery_score = u["battery"] / 100.0

        # Role preference: standby > idle-mission > on_mission
        if u["role"] == ROLE_STANDBY:
            role_score = 1.0
        elif u["status"] == STATUS_IDLE:
            role_score = 0.7
        else:
            role_score = 0.3  # on active mission — expensive to pull

        score = (0.40 * dist_score) + (0.30 * battery_score) + (0.30 * role_score)
        candidates.append({
            "uav_id": uid,
            "score": round(score, 4),
            "dist_to_target": round(dist_to_target, 2),
        })

    if not candidates:
        logger.warning("No relay candidate available for disconnected: %s", disconnected_ids)
        return None

    candidates.sort(key=lambda c: c["score"], reverse=True)
    best = candidates[0]

    result = {
        "relay_uav_id": best["uav_id"],
        "target_position": relay_target,
        "score": best["score"],
        "connects_to": {
            "bridge_anchor": bridge_anchor_id,
            "disconnected": disconnected_ids,
        },
    }
    logger.info(
        "Relay selected: %s (score=%.3f) → position (%.0f,%.0f,%.0f)",
        best["uav_id"], best["score"],
        relay_target["x"], relay_target["y"], relay_target["z"],
    )
    return result
