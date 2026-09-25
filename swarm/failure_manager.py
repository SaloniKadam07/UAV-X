from swarm.constants import STATUS_FAILED


def fail_uav(uavs, uav_id):
    for uav in uavs:
        if uav["id"] == uav_id:
            uav["status"] = STATUS_FAILED
            return uav

    return None


def fail_link(links, source, target):
    for link in links:
        same_direction = (
            link["from"] == source and link["to"] == target
        )

        reverse_direction = (
            link["from"] == target and link["to"] == source
        )

        if same_direction or reverse_direction:
            link["connected"] = False
            return link

    return None