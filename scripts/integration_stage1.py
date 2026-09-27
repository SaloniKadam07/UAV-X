import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VISION_DIR = ROOT / "vision"
SWARM_DIR = ROOT / "uav-swarm-comm"

# -----------------------------
# 1. Load simulation first
# -----------------------------
sys.path.insert(0, str(ROOT))

from simulation.uav_simulator import UAVSimulator

# simulation imports the root-level swarm package.
# Remove those cached modules before loading Person 2's nested swarm package.
for name in list(sys.modules):
    if name == "swarm" or name.startswith("swarm."):
        del sys.modules[name]

# -----------------------------
# 2. Load Person 2 swarm system
# -----------------------------
sys.path.insert(0, str(SWARM_DIR))

from integration_api import SwarmController

# -----------------------------
# 3. Load Person 3 vision system
# -----------------------------
sys.path.insert(0, str(VISION_DIR))

from interface import get_detection_result, get_mission_points


def sim_uavs_to_swarm(sim):
    """
    Convert Person 1 simulation UAV format into
    Person 2 swarm-controller format.
    """
    converted = []

    for drone in sim.drones.values():
        sim_status = drone.to_dict()["status"]

        if sim_status == "FAILED":
            swarm_status = "failed"
        elif sim_status == "RETURNING":
            swarm_status = "returning"
        else:
            swarm_status = "idle"

        if drone.role == "RELAY":
            swarm_role = "relay"
        elif drone.role == "RESERVE":
            swarm_role = "standby"
        else:
            swarm_role = "mission"

        converted.append(
            {
                "id": drone.id,
                "position": {
                    "x": drone.pos[0],
                    "y": drone.pos[1],
                    "z": drone.pos[2],
                },
                "battery": drone.battery,
                "status": swarm_status,
                "role": swarm_role,
                "current_mission": None,
                "max_speed": drone.speed,
                "comm_range": 100.0,
            }
        )

    return converted


def build_links():
    """
    Communication topology using the same UAV IDs
    used by the simulator.
    """
    return [
        {
            "from": "GCS",
            "to": "UAV1",
            "quality": 1.0,
            "active": True,
        },
        {
            "from": "GCS",
            "to": "UAV4",
            "quality": 0.9,
            "active": True,
        },
        {
            "from": "UAV1",
            "to": "UAV2",
            "quality": 0.9,
            "active": True,
        },
        {
            "from": "UAV2",
            "to": "UAV3",
            "quality": 0.8,
            "active": True,
        },
        {
            "from": "UAV2",
            "to": "UAV4",
            "quality": 0.85,
            "active": True,
        },
    ]

def vision_point_to_swarm_mission(point):
    """
    Convert Person 3 Mission Point format into
    Person 2 mission-manager format.
    """
    priority = point["priority"].lower()

    return {
        "id": point["id"],
        "type": "vision_target",
        "priority": priority,
        "target": {
            "x": point["position"][0],
            "y": point["position"][1],
            "z": point["position"][2],
        },
        "status": "pending",
        "assigned_uav": None,
        "requirements": {
            "min_battery": 20
        },
    }


def swarm_id_to_sim_id(uav_id):
    return uav_id


def main():
    print("\n==============================================")
    print(" UAV-X PERSON 4 STAGE 1 INTEGRATION")
    print("==============================================")

    # -------------------------------------------------
    # Phase 1 - Simulation initialization
    # -------------------------------------------------
    print("\n[1] Initializing simulation...")

    sim = UAVSimulator()
    sim.reset_uav_state()

    # small takeoff so simulator is active
    for drone in sim.drones.values():
        drone.set_target(
            drone.home_pos[0],
            drone.home_pos[1],
            5.0,
        )

    for _ in range(10):
        sim.step(0.1)

    print("Simulation initialized.")

    # -------------------------------------------------
    # Phase 2 - Swarm controller initialization
    # -------------------------------------------------
    print("\n[2] Initializing swarm + communication...")

    swarm_uavs = sim_uavs_to_swarm(sim)

    controller = SwarmController()

    controller.initialize_from_dicts(
        uavs=swarm_uavs,
        missions=[],
        links=build_links(),
        settings={
            "gcs_position": {
                "x": 0,
                "y": 500,
                "z": 0,
            }
        },
    )

    print("Swarm controller initialized.")
    print(
        "Disconnected UAVs:",
        controller.get_disconnected_uavs(),
    )

    # -------------------------------------------------
    # Phase 3 - Vision detection
    # -------------------------------------------------
    print("\n[3] Running vision detection...")

    sample_image = (
        VISION_DIR
        / "sample_data"
        / "test_frame.jpg"
    )

    if not sample_image.exists():
        print(
            "Vision sample image not found:",
            sample_image,
        )
        return

    detections = get_detection_result(
        str(sample_image)
    )

    mission_points = get_mission_points(
        str(sample_image)
    )

    print("Vision detections:")
    for detection in detections:
        print(" ", detection)

    if not mission_points:
        print("No mission point detected.")
        return

    vision_point = mission_points[0]

    print(
        "Vision mission point:",
        vision_point,
    )

    # -------------------------------------------------
    # Phase 4 - Vision -> swarm mission
    # -------------------------------------------------
    print("\n[4] Sending vision mission to swarm...")

    mission = vision_point_to_swarm_mission(
        vision_point
    )

    result = controller.handle_priority_event(
        mission
    )

    if result is None:
        print("Mission assignment failed.")
        return

    assigned_uav = result["uav_id"]

    print(
        f"Mission {mission['id']} assigned "
        f"to {assigned_uav}"
    )

    # -------------------------------------------------
    # Phase 5 - Swarm -> simulation command
    # -------------------------------------------------
    print("\n[5] Sending assignment to simulator...")

    sim_id = swarm_id_to_sim_id(
        assigned_uav
    )

    target = mission["target"]

    command_ok = sim.command_waypoint(
        sim_id,
        [
            target["x"],
            target["y"],
            max(target["z"], 10.0),
        ],
    )

    print(
        "Waypoint command accepted:",
        command_ok,
    )

    for _ in range(20):
        sim.step(0.1)

    if sim_id in sim.drones:
        drone = sim.drones[sim_id]
        print(
            f"{sim_id} simulator position:",
            [
                round(v, 2)
                for v in drone.pos
            ],
        )

    # -------------------------------------------------
    # Phase 6 - Communication failure
    # -------------------------------------------------
    print("\n[6] Injecting communication failure...")

    controller.network.fail_link(
        "UAV1",
        "UAV2",
    )

    controller.network.fail_link(
        "UAV2",
        "UAV4",
    )
    print(
        "Disconnected before recovery:",
        controller.get_disconnected_uavs(),
    )

    # -------------------------------------------------
    # Phase 7 - Relay recovery
    # -------------------------------------------------
    print("\n[7] Running relay recovery...")

    recovery = (
        controller
        .recovery_mgr
        .attempt_recovery(
            controller.uav_states
        )
    )

    print("Recovery result:", recovery)

    print(
        "Disconnected after recovery:",
        controller.get_disconnected_uavs(),
    )

    # -------------------------------------------------
    # Phase 8 - Simulate UAV failure
    # -------------------------------------------------
    print("\n[8] Injecting UAV failure...")

    failure_target = assigned_uav

    if failure_target in sim.drones:
        sim.drones[
            failure_target
        ].mark_failed()

    failure_result = controller.fail_uav(
        failure_target
    )

    print(
        "Failure manager result:",
        failure_result,
    )

    # -------------------------------------------------
    # Phase 9 - Final state
    # -------------------------------------------------
    print("\n[9] Final health check...")

    health = controller.health_check()

    print("Health report:", health)

    print("\n==============================================")
    print(" STAGE 1 INTEGRATION FLOW COMPLETED")
    print("==============================================\n")


if __name__ == "__main__":
    main()