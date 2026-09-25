from communication.relay_selector import find_relay_candidate


def recover_network(uavs, disconnected_uavs):
    candidate = find_relay_candidate(uavs, disconnected_uavs)

    if candidate is None:
        return None

    candidate["role"] = "RELAY"

    return candidate