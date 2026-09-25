def choose_uav(uavs, mission_point):
    available_uavs = []

    for uav in uavs:
        if (
            uav["status"] == "ACTIVE"
            and uav["battery"] > 20
            and uav["role"] != "RELAY"
        ):
            available_uavs.append(uav)

    if not available_uavs:
        return None

    selected_uav = max(
        available_uavs,
        key=lambda uav: uav["battery"]
    )

    return selected_uav