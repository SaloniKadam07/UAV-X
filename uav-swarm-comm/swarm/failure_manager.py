"""
swarm/failure_manager.py

Detects and reacts to failures in the swarm:
  - Broken communication links
  - Failed UAVs (hardware / battery critical)
  - UAVs disconnected from GCS
Coordinates with RecoveryManager and MissionManager to handle fallout.
"""

import logging
import copy

from swarm.constants import (
    STATUS_FAILED, BATTERY_CRITICAL, GCS_NODE_ID,
)

logger = logging.getLogger(__name__)


class FailureManager:
    """
    Monitors the swarm for failures and drives recovery.

    Usage from integration script:
        fm = FailureManager(network_graph, recovery_manager, mission_manager)
        fm.process_link_failure("UAV_2", "UAV_3", uav_states, missions)
        fm.process_uav_failure("UAV_4", uav_states, missions)
        report = fm.run_health_check(uav_states, missions)
    """

    def __init__(self, network_graph, recovery_manager, mission_manager):
        self.network = network_graph
        self.recovery = recovery_manager
        self.missions = mission_manager
        self.failure_log: list[dict] = []

    # ── Link failure ──────────────────────────────────────

    def process_link_failure(
        self,
        node_a: str,
        node_b: str,
        uav_states: list[dict],
        mission_states: list[dict] | None = None,
    ) -> dict:
        """
        Handle a detected link failure between two nodes.

        Steps:
          1. Remove the link from the network graph.
          2. Check if any UAVs are now disconnected from GCS.
          3. If disconnected UAVs exist, trigger relay recovery.
          4. If recovery displaced a mission, trigger reassignment.

        Returns a summary dict.
        """
        logger.warning("Link failure reported: %s <-> %s", node_a, node_b)
        self.network.fail_link(node_a, node_b)

        disconnected = self.network.get_disconnected_nodes()
        result = {
            "event": "link_fail",
            "link": [node_a, node_b],
            "disconnected": list(disconnected),
            "recovery": None,
            "reassigned_missions": [],
        }

        if disconnected:
            recovery_result = self.recovery.attempt_recovery(uav_states, mission_states)
            result["recovery"] = recovery_result

            # Handle displaced missions
            for mid in recovery_result.get("missions_to_reassign", []):
                r = self.missions.reassign_mission(mid, uav_states, self.network)
                if r:
                    result["reassigned_missions"].append(r)

        self._log_failure(result)
        return result

    # ── UAV failure ───────────────────────────────────────

    def process_uav_failure(
        self,
        uav_id: str,
        uav_states: list[dict],
        mission_states: list[dict] | None = None,
    ) -> dict:
        """
        Handle a UAV going down (hardware failure, battery dead, etc.).

        Steps:
          1. Mark the UAV as failed.
          2. Remove it from the network graph.
          3. If it had a mission, fail + reassign that mission.
          4. Check for newly disconnected UAVs → relay recovery.

        Returns a summary dict.
        """
        logger.warning("UAV failure reported: %s", uav_id)

        # Mark UAV failed
        affected_mission = None
        for u in uav_states:
            if u["id"] == uav_id:
                u["status"] = STATUS_FAILED
                affected_mission = u.get("current_mission")
                u["current_mission"] = None
                break

        # Remove from network
        affected_neighbors = self.network.remove_node(uav_id)

        result = {
            "event": "uav_fail",
            "uav_id": uav_id,
            "affected_neighbors": affected_neighbors,
            "affected_mission": affected_mission,
            "mission_reassignment": None,
            "recovery": None,
            "reassigned_missions": [],
        }

        # Reassign affected mission
        if affected_mission:
            r = self.missions.fail_mission(
                affected_mission, uav_states, self.network, auto_reassign=True
            )
            result["mission_reassignment"] = r

        # Check connectivity
        disconnected = self.network.get_disconnected_nodes()
        if disconnected:
            recovery_result = self.recovery.attempt_recovery(uav_states, mission_states)
            result["recovery"] = recovery_result

            for mid in recovery_result.get("missions_to_reassign", []):
                r = self.missions.reassign_mission(mid, uav_states, self.network)
                if r:
                    result["reassigned_missions"].append(r)

        self._log_failure(result)
        return result

    # ── Battery check ─────────────────────────────────────

    def check_critical_batteries(
        self,
        uav_states: list[dict],
    ) -> list[str]:
        """
        Return UAV IDs that are below BATTERY_CRITICAL.
        The integration script should trigger RTL for these.
        """
        critical = [
            u["id"] for u in uav_states
            if u["battery"] <= BATTERY_CRITICAL and u["status"] != STATUS_FAILED
        ]
        if critical:
            logger.warning("Critical battery on UAVs: %s", critical)
        return critical

    # ── Full health check ─────────────────────────────────

    def run_health_check(
        self,
        uav_states: list[dict],
        mission_states: list[dict] | None = None,
    ) -> dict:
        """
        Comprehensive health check — call periodically from integration loop.

        Checks:
          - Disconnected UAVs (triggers recovery)
          - Degraded links
          - Critical batteries
          - Failed UAVs with lingering missions

        Returns a report dict.
        """
        report = {
            "disconnected": [],
            "degraded_links": [],
            "critical_batteries": [],
            "recovery_triggered": False,
            "recovery_result": None,
        }

        # Disconnected nodes
        disconnected = self.network.get_disconnected_nodes()
        report["disconnected"] = disconnected

        # Degraded links
        report["degraded_links"] = self.network.get_degraded_links()

        # Critical batteries
        report["critical_batteries"] = self.check_critical_batteries(uav_states)

        # Auto-recover if disconnected
        if disconnected:
            recovery_result = self.recovery.attempt_recovery(uav_states, mission_states)
            report["recovery_triggered"] = True
            report["recovery_result"] = recovery_result

            for mid in recovery_result.get("missions_to_reassign", []):
                self.missions.reassign_mission(mid, uav_states, self.network)

        return report

    # ── Queries ───────────────────────────────────────────

    def get_failure_log(self) -> list[dict]:
        return list(self.failure_log)

    def get_disconnected_uavs(self) -> list[str]:
        return self.network.get_disconnected_nodes()

    # ── Internal ──────────────────────────────────────────

    def _log_failure(self, entry: dict) -> None:
        self.failure_log.append(copy.deepcopy(entry))
