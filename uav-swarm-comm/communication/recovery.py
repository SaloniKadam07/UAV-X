"""
communication/recovery.py

Orchestrates relay recovery: once a relay UAV is selected,
this module handles role reassignment, link creation,
and verification that connectivity is restored.
"""

import logging
import copy

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from swarm.constants import (
    ROLE_RELAY, STATUS_RELAY, STATUS_IDLE,
    MISSION_PENDING, GCS_NODE_ID,
)
from communication.relay_selector import select_relay

logger = logging.getLogger(__name__)


class RecoveryManager:
    """
    Manages the full relay-recovery lifecycle:
      1. Detect that recovery is needed (disconnected nodes exist).
      2. Select a relay via relay_selector.
      3. Reassign the chosen UAV's role to RELAY.
      4. Create new links in the network graph (simulating physical move).
      5. Verify connectivity is restored.
      6. If the relay UAV was on a mission, mark that mission for reassignment.
    """

    def __init__(self, network_graph, gcs_position: dict | None = None):
        self.network = network_graph
        self.gcs_position = gcs_position or {"x": 0, "y": 0, "z": 0}
        # history of recovery actions for audit / replay
        self.recovery_log: list[dict] = []

    def attempt_recovery(
        self,
        uav_states: list[dict],
        mission_states: list[dict] | None = None,
    ) -> dict:
        """
        Top-level entry: detect disconnected UAVs and try to restore connectivity.

        Returns a result dict:
        {
            "recovered": bool,
            "relay_uav_id": str | None,
            "disconnected_before": [...],
            "disconnected_after": [...],
            "missions_to_reassign": [...],
            "relay_target_position": {...} | None,
        }
        """
        disconnected = self.network.get_disconnected_nodes()
        result = {
            "recovered": False,
            "relay_uav_id": None,
            "disconnected_before": list(disconnected),
            "disconnected_after": [],
            "missions_to_reassign": [],
            "relay_target_position": None,
        }

        if not disconnected:
            logger.debug("No disconnected nodes — nothing to recover.")
            result["recovered"] = True
            return result

        logger.warning("Disconnected nodes detected: %s", disconnected)

        # ── Select relay ──────────────────────────────────
        relay_info = select_relay(
            uav_states, disconnected, self.network, self.gcs_position
        )

        if relay_info is None:
            logger.error("Recovery FAILED: no suitable relay candidate.")
            result["disconnected_after"] = list(disconnected)
            return result

        relay_id = relay_info["relay_uav_id"]
        target_pos = relay_info["target_position"]
        bridge_anchor = relay_info["connects_to"]["bridge_anchor"]

        result["relay_uav_id"] = relay_id
        result["relay_target_position"] = target_pos

        # ── Reassign the relay UAV ────────────────────────
        for u in uav_states:
            if u["id"] == relay_id:
                # If it was on a mission, flag that mission for reassignment
                if u.get("current_mission"):
                    result["missions_to_reassign"].append(u["current_mission"])
                    logger.info(
                        "Mission %s will need reassignment (UAV %s pulled for relay)",
                        u["current_mission"], relay_id,
                    )

                u["role"] = ROLE_RELAY
                u["status"] = STATUS_RELAY
                u["position"] = copy.deepcopy(target_pos)
                u["current_mission"] = None
                break

        # ── Create relay links in the graph ───────────────
        # The relay bridges between the anchor and the disconnected cluster.
        neighbors_to_link = [bridge_anchor] + disconnected
        self.network.add_relay_links(relay_id, neighbors_to_link, quality=0.70)

        # ── Verify ────────────────────────────────────────
        still_disconnected = self.network.get_disconnected_nodes()
        result["disconnected_after"] = still_disconnected
        result["recovered"] = len(still_disconnected) == 0

        if result["recovered"]:
            logger.info("Recovery SUCCEEDED — all nodes connected to GCS.")
        else:
            logger.warning(
                "Recovery PARTIAL — still disconnected: %s", still_disconnected
            )

        # ── Log it ────────────────────────────────────────
        self.recovery_log.append(copy.deepcopy(result))
        return result

    def release_relay(self, relay_uav_id: str, uav_states: list[dict]) -> None:
        """
        Release a UAV from relay duty (e.g. when original link is restored).
        Sets it back to idle/standby so the mission manager can reuse it.
        """
        for u in uav_states:
            if u["id"] == relay_uav_id:
                u["role"] = "standby"
                u["status"] = STATUS_IDLE
                logger.info("Relay %s released back to standby.", relay_uav_id)
                break

    def get_recovery_log(self) -> list[dict]:
        return list(self.recovery_log)
