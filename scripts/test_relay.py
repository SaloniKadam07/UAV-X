import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from communication.network_graph import build_graph, is_connected_to_gcs
from communication.relay_selector import find_relay_candidate

uavs_path = BASE_DIR / "config" / "uavs.json"
links_path = BASE_DIR / "config" / "links.json"

with open(uavs_path, "r") as f:
    uavs = json.load(f)

with open(links_path, "r") as f:
    links = json.load(f)

graph = build_graph(links)

disconnected_uavs = []

for uav in uavs:
    if not is_connected_to_gcs(graph, uav["id"]):
        disconnected_uavs.append(uav["id"])

print("\n=== RELAY RECOVERY TEST ===")
print("Disconnected UAVs:", disconnected_uavs)

candidate = find_relay_candidate(uavs, disconnected_uavs)

if candidate:
    print(f"Suggested Relay UAV: {candidate['id']}")
    print(f"Battery: {candidate['battery']}%")
    print(f"Current Role: {candidate['role']}")
else:
    print("No suitable relay candidate found.")