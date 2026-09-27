"""
integration_api.py

Clean, top-level functions for Person 4 to call from the integration script.
Wraps all swarm + communication subsystems into a single facade.

Usage:
    from integration_api import SwarmController
    ctrl = SwarmController()
    ctrl.initialize("config/uavs.json", "config/mission.json",
                    "config/links.json", "config/settings.json")
    ctrl.assign_mission("M1")
    ctrl.fail_link("UAV_2", "UAV_3")
    report = ctrl.health_check()
"""

import json
import logging
import copy

from communication.network_graph import NetworkGraph
from communication.recovery import RecoveryManager
from swarm.mission_manager import MissionManager
from swarm.failure_manager import FailureManager
from swarm.task_allocator import select_uav, rank_uavs
from swarm.constants import GCS_NODE_ID

logger = logging.getLogger(__name__)


class SwarmController:
    """
    Facade for Person 4's integration script.

    Initializes all subsystems and exposes simple, self-contained methods
    that operate on shared state (uav_states, missions, network).
    """

    def __init__(self):
        self.network = NetworkGraph()
        self.mission_mgr = MissionManager()
        self.recovery_mgr = None   # set after init
        self.failure_mgr = None    # set after init

        self.uav_states: list[dict] = []
        self.settings: dict = {}
        self._initialized = False

    # ══════════════════════════════════════════════════════
    #  INITIALIZATION
    # ══════════════════════════════════════════════════════

    def initialize(
        self,
        uavs_path: str = "config/uavs.json",
        missions_path: str = "config/mission.json",
        links_path: str = "config/links.json",
        settings_path: str = "config/settings.json",
    ) -> None:
        """Load all configs and wire up subsystems."""
        # Settings
        with open(settings_path) as f:
            self.settings = json.load(f)

        # UAVs
        with open(uavs_path) as f:
            self.uav_states = json.load(f)["uavs"]

        # Missions
        with open(missions_path) as f:
            missions = json.load(f)["missions"]
        self.mission_mgr.load_missions(missions)

        # Network
        self.network.load_links(links_path)
        node_ids = [u["id"] for u in self.uav_states] + [GCS_NODE_ID]
        self.network.register_nodes(node_ids)

        # Recovery + Failure managers
        gcs_pos = self.settings.get("gcs_position", {"x": 0, "y": 0, "z": 0})
        self.recovery_mgr = RecoveryManager(self.network, gcs_pos)
        self.failure_mgr = FailureManager(
            self.network, self.recovery_mgr, self.mission_mgr
        )

        self._initialized = True
        logger.info("SwarmController initialized — %d UAVs, %d missions",
                     len(self.uav_states), len(missions))

    def initialize_from_dicts(
        self,
        uavs: list[dict],
        missions: list[dict],
        links: list[dict],
        settings: dict | None = None,
    ) -> None:
        """Initialize from in-memory dicts instead of files (for simulation)."""
        self.settings = settings or {}
        self.uav_states = copy.deepcopy(uavs)
        self.mission_mgr.load_missions(missions)
        self.network.load_links_from_list(links)
        node_ids = [u["id"] for u in self.uav_states] + [GCS_NODE_ID]
        self.network.register_nodes(node_ids)

        gcs_pos = self.settings.get("gcs_position", {"x": 0, "y": 0, "z": 0})
        self.recovery_mgr = RecoveryManager(self.network, gcs_pos)
        self.failure_mgr = FailureManager(
            self.network, self.recovery_mgr, self.mission_mgr
        )
        self._initialized = True

    # ══════════════════════════════════════════════════════
    #  MISSION OPERATIONS
    # ══════════════════════════════════════════════════════

    def assign_mission(self, mission_id: str) -> dict | None:
        """Assign a pending mission to the best available UAV."""
        return self.mission_mgr.assign_mission(
            mission_id, self.uav_states, self.network
        )

    def complete_mission(self, mission_id: str) -> bool:
        """Mark a mission as completed and free the UAV."""
        return self.mission_mgr.complete_mission(mission_id, self.uav_states)

    def fail_mission(self, mission_id: str, auto_reassign: bool = True) -> dict | None:
        """Mark a mission as failed, optionally reassign."""
        return self.mission_mgr.fail_mission(
            mission_id, self.uav_states, self.network, auto_reassign
        )

    def handle_priority_event(self, mission_dict: dict) -> dict | None:
        """Inject a high-priority mission, preempt if critical."""
        return self.mission_mgr.handle_priority_event(
            mission_dict, self.uav_states, self.network
        )

    # ══════════════════════════════════════════════════════
    #  FAILURE / RECOVERY OPERATIONS
    # ══════════════════════════════════════════════════════

    def fail_link(self, node_a: str, node_b: str) -> dict:
        """Report a broken link and trigger recovery if needed."""
        return self.failure_mgr.process_link_failure(
            node_a, node_b, self.uav_states
        )

    def fail_uav(self, uav_id: str) -> dict:
        """Report a UAV failure and trigger recovery + reassignment."""
        return self.failure_mgr.process_uav_failure(
            uav_id, self.uav_states
        )

    def health_check(self) -> dict:
        """Run a full health check — disconnected nodes, degraded links, batteries."""
        return self.failure_mgr.run_health_check(self.uav_states)

    # ══════════════════════════════════════════════════════
    #  NETWORK QUERIES
    # ══════════════════════════════════════════════════════

    def get_disconnected_uavs(self) -> list[str]:
        return self.network.get_disconnected_nodes()

    def get_network_snapshot(self) -> dict:
        return self.network.snapshot()

    def can_uav_reach_gcs(self, uav_id: str) -> bool:
        return self.network.can_reach_gcs(uav_id)

    def get_path_to_gcs(self, uav_id: str) -> list[str] | None:
        return self.network.find_path_to_gcs(uav_id)

    # ══════════════════════════════════════════════════════
    #  STATE QUERIES
    # ══════════════════════════════════════════════════════

    def get_uav_states(self) -> list[dict]:
        return copy.deepcopy(self.uav_states)

    def get_uav_state(self, uav_id: str) -> dict | None:
        for u in self.uav_states:
            if u["id"] == uav_id:
                return copy.deepcopy(u)
        return None

    def get_active_missions(self) -> list[dict]:
        return self.mission_mgr.get_active_missions()

    def get_pending_missions(self) -> list[dict]:
        return self.mission_mgr.get_pending_missions()

    def get_mission(self, mission_id: str) -> dict | None:
        return self.mission_mgr.get_mission(mission_id)

    def get_event_log(self) -> list[dict]:
        return self.mission_mgr.get_event_log()

    def get_failure_log(self) -> list[dict]:
        return self.failure_mgr.get_failure_log()

    def get_recovery_log(self) -> list[dict]:
        return self.recovery_mgr.get_recovery_log()

    # ══════════════════════════════════════════════════════
    #  MANUAL OVERRIDES (for Person 4)
    # ══════════════════════════════════════════════════════

    def update_uav_position(self, uav_id: str, position: dict) -> None:
        """Manually update a UAV's position (from simulation)."""
        for u in self.uav_states:
            if u["id"] == uav_id:
                u["position"] = copy.deepcopy(position)
                return

    def update_uav_battery(self, uav_id: str, battery: float) -> None:
        """Update battery level from simulation tick."""
        for u in self.uav_states:
            if u["id"] == uav_id:
                u["battery"] = battery
                return

    def restore_link(self, node_a: str, node_b: str, quality: float = 0.8) -> None:
        """Manually restore a link (e.g. after repositioning)."""
        self.network.restore_link(node_a, node_b, quality)
