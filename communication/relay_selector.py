def find_relay_candidate(uavs, disconnected_uavs):
    candidates = []

    for uav in uavs:
        if (
            uav["status"] == "ACTIVE"
            and uav["battery"] > 20
            and uav["id"] not in disconnected_uavs
            and uav["role"] != "RELAY"
        ):
            candidates.append(uav)

    if not candidates:
        return None

    return max(candidates, key=lambda uav: uav["battery"])