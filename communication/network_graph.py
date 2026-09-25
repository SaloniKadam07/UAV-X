from collections import defaultdict, deque


def build_graph(links):
    graph = defaultdict(list)

    for link in links:
        if link["connected"]:
            source = link["from"]
            target = link["to"]

            graph[source].append(target)
            graph[target].append(source)

    return graph


def is_connected_to_gcs(graph, uav_id):
    if uav_id == "GCS":
        return True

    visited = set()
    queue = deque(["GCS"])

    while queue:
        current = queue.popleft()

        if current == uav_id:
            return True

        if current in visited:
            continue

        visited.add(current)

        for neighbor in graph[current]:
            if neighbor not in visited:
                queue.append(neighbor)

    return False