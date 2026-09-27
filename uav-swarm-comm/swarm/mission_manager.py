"""
swarm/mission_manager.py

Central mission lifecycle manager.
Handles assignment, tracking, reassignment, completion, and priority events.
"""

import copy
import logging

from swarm.constants import (
    MISSION_PENDING, MISSION_ASSIGNED, MISSION_IN_PROGRESS,
    MISSION_COMPLETED, MISSION_FAILED, MISSION_REASSIGNED,
    STATUS_IDLE, STATUS_ON_MISSION, ROLE_MISSION,
    PRIORITY_MAP, PRIORITY_CRITICAL,
)
from swarm.task_allocator import select_uav

logger = logging.getLogger(__name__)


class MissionManager:
    """
    Owns the mission list and UAV-to-mission mapping.

    Provides:
      - assign_mission()      : allocate a pending mission
      - reassign_mission()    : re-allocate after UAV loss
      - complete_mission()    : mark done, free UAV
      - fail_mission()        : mark failed, optionally reassign
      - handle_priority_event(): preempt lower-priority work for critical tasks
      - get_active_missions() : inspection
    """

    def __init__(self):
        # mission_id → mission dict
        self.missions: dict[str, dict] = {}
        # uav_id → mission_id  (only active assignments)
        self.uav_assignments: dict[str, str] = {}
        # event log
        self.event_log: list[dict] = []

    # ── Load ──────────────────────────────────────────────

    def load_missions(self, missions: list[dict]) -> None:
        """Load mission definitions (from config/mission.json)."""
        for m in missions:
            self.missions[m["id"]] = copy.deepcopy(m)

    # ── Assignment ────────────────────────────────────────

    def assign_mission(
        self,
        mission_id: str,
        uav_states: list[dict],
        network_graph,
    ) -> dict | None:
        """
        Try to assign a pending mission to the best UAV.

        Returns:
            {"mission_id", "uav_id", "score"} on success, else None.
        """
        mission = self.missions.get(mission_id)
        if not mission:
            logger.error("Mission %s not found.", mission_id)
            return None

        if mission["status"] not in (MISSION_PENDING, MISSION_REASSIGNED):
            logger.warning(
                "Mission %s is '%s', not assignable.", mission_id, mission["status"]
            )
            return None

        result = select_uav(uav_states, mission, network_graph)
        if result is None:
            logger.warning("Could not assign mission %s — no eligible UAV.", mission_id)
            return None

        uav_id = result["uav_id"]

        # Update mission state
        mission["status"] = MISSION_ASSIGNED
        mission["assigned_uav"] = uav_id

        # Update UAV state
        for u in uav_states:
            if u["id"] == uav_id:
                u["status"] = STATUS_ON_MISSION
                u["role"] = ROLE_MISSION
                u["current_mission"] = mission_id
                break

        self.uav_assignments[uav_id] = mission_id
        self._log("assign", mission_id=mission_id, uav_id=uav_id, score=result["score"])

        logger.info("Mission %s assigned → UAV %s", mission_id, uav_id)
        return {"mission_id": mission_id, "uav_id": uav_id, "score": result["score"]}

    # ── Reassignment ──────────────────────────────────────

    def reassign_mission(
        self,
        mission_id: str,
        uav_states: list[dict],
        network_graph,
        exclude_uav: str | None = None,
    ) -> dict | None:
        """
        Reassign a mission (e.g. when its UAV failed or was pulled for relay).
        Optionally exclude a specific UAV from candidacy.
        """
        mission = self.missions.get(mission_id)
        if not mission:
            return None

        old_uav = mission.get("assigned_uav")

        # Free old assignment
        if old_uav:
            self.uav_assignments.pop(old_uav, None)
            for u in uav_states:
                if u["id"] == old_uav:
                    u["current_mission"] = None
                    break

        mission["status"] = MISSION_REASSIGNED
        mission["assigned_uav"] = None

        # Filter out the excluded UAV
        candidates = uav_states
        if exclude_uav:
            candidates = [u for u in uav_states if u["id"] != exclude_uav]

        result = select_uav(candidates, mission, network_graph)
        if result is None:
            logger.warning("Reassignment failed for mission %s — no candidate.", mission_id)
            mission["status"] = MISSION_PENDING
            return None

        uav_id = result["uav_id"]
        mission["status"] = MISSION_ASSIGNED
        mission["assigned_uav"] = uav_id

        for u in uav_states:
            if u["id"] == uav_id:
                u["status"] = STATUS_ON_MISSION
                u["role"] = ROLE_MISSION
                u["current_mission"] = mission_id
                break

        self.uav_assignments[uav_id] = mission_id
        self._log("reassign", mission_id=mission_id, uav_id=uav_id,
                  old_uav=old_uav, score=result["score"])

        logger.info("Mission %s reassigned: %s → %s", mission_id, old_uav, uav_id)
        return {"mission_id": mission_id, "uav_id": uav_id, "score": result["score"]}

    # ── Completion / Failure ──────────────────────────────

    def complete_mission(self, mission_id: str, uav_states: list[dict]) -> bool:
        """Mark mission completed, free the UAV."""
        mission = self.missions.get(mission_id)
        if not mission:
            return False

        uav_id = mission.get("assigned_uav")
        mission["status"] = MISSION_COMPLETED
        mission["assigned_uav"] = None

        if uav_id:
            self.uav_assignments.pop(uav_id, None)
            for u in uav_states:
                if u["id"] == uav_id:
                    u["status"] = STATUS_IDLE
                    u["current_mission"] = None
                    break

        self._log("complete", mission_id=mission_id, uav_id=uav_id)
        logger.info("Mission %s completed by UAV %s", mission_id, uav_id)
        return True

    def fail_mission(
        self,
        mission_id: str,
        uav_states: list[dict],
        network_graph,
        auto_reassign: bool = True,
    ) -> dict | None:
        """
        Mark mission as failed. Optionally trigger auto-reassignment.
        """
        mission = self.missions.get(mission_id)
        if not mission:
            return None

        old_uav = mission.get("assigned_uav")
        mission["status"] = MISSION_FAILED
        mission["assigned_uav"] = None

        if old_uav:
            self.uav_assignments.pop(old_uav, None)

        self._log("fail", mission_id=mission_id, uav_id=old_uav)
        logger.warning("Mission %s failed (was on UAV %s)", mission_id, old_uav)

        if auto_reassign:
            return self.reassign_mission(
                mission_id, uav_states, network_graph, exclude_uav=old_uav
            )
        return None

    # ── Priority events ───────────────────────────────────

    def handle_priority_event(
        self,
        new_mission: dict,
        uav_states: list[dict],
        network_graph,
    ) -> dict | None:
        """
        Handle a high-priority mission that arrives mid-simulation.
        If it's CRITICAL and no idle UAV exists, preempt the lowest-priority
        active mission.

        Args:
            new_mission: full mission dict (must include id, priority, target, etc.)

        Returns:
            assignment result or None.
        """
        mid = new_mission["id"]
        self.missions[mid] = copy.deepcopy(new_mission)
        self.missions[mid]["status"] = MISSION_PENDING

        # Try normal assignment first
        result = self.assign_mission(mid, uav_states, network_graph)
        if result is not None:
            return result

        # ── Preemption (critical only) ────────────────────
        pri_val = PRIORITY_MAP.get(new_mission.get("priority", "medium"), 2)
        if pri_val < PRIORITY_CRITICAL:
            logger.info("Mission %s is not critical — won't preempt.", mid)
            return None

        # Find the lowest-priority active mission to preempt
        active = [
            (m_id, m) for m_id, m in self.missions.items()
            if m["status"] in (MISSION_ASSIGNED, MISSION_IN_PROGRESS)
               and m_id != mid
        ]
        if not active:
            return None

        active.sort(key=lambda x: PRIORITY_MAP.get(x[1].get("priority", "medium"), 2))
        victim_id, victim = active[0]

        logger.info(
            "Preempting mission %s (pri=%s) for critical mission %s",
            victim_id, victim.get("priority"), mid,
        )

        # Fail the victim → frees its UAV
        self.fail_mission(victim_id, uav_states, network_graph, auto_reassign=False)

        # Now try assigning the critical mission
        result = self.assign_mission(mid, uav_states, network_graph)

        # Re-queue the victim
        if victim_id in self.missions:
            self.missions[victim_id]["status"] = MISSION_PENDING
        return result

    # ── Queries ───────────────────────────────────────────

    def get_active_missions(self) -> list[dict]:
        return [
            m for m in self.missions.values()
            if m["status"] in (MISSION_ASSIGNED, MISSION_IN_PROGRESS)
        ]

    def get_pending_missions(self) -> list[dict]:
        return [
            m for m in self.missions.values()
            if m["status"] in (MISSION_PENDING, MISSION_REASSIGNED)
        ]

    def get_mission(self, mission_id: str) -> dict | None:
        return self.missions.get(mission_id)

    def get_uav_mission(self, uav_id: str) -> str | None:
        return self.uav_assignments.get(uav_id)

    def get_event_log(self) -> list[dict]:
        return list(self.event_log)

    # ── Internal ──────────────────────────────────────────

    def _log(self, action: str, **kwargs) -> None:
        entry = {"action": action, **kwargs}
        self.event_log.append(entry)
