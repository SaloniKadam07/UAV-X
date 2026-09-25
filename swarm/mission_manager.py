from swarm.task_allocator import choose_uav


def assign_mission(uavs, mission_point):
    selected_uav = choose_uav(uavs, mission_point)

    if selected_uav is None:
        return None

    selected_uav["current_mission"] = mission_point["id"]
    mission_point["status"] = "ASSIGNED"

    return selected_uav