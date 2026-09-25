import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from communication.network_graph import build_graph, is_connected_to_gcs

links_path = BASE_DIR / "config" / "links.json"
uavs_path = BASE_DIR / "config" / "uavs.json"

with open(links_path, "r") as f:
    links = json.load(f)

with open(uavs_path, "r") as f:
    uavs = json.load(f)

graph = build_graph(links)

print("\n=== NETWORK CONNECTIVITY TEST ===")

for uav in uavs:
    connected = is_connected_to_gcs(graph, uav["id"])
    print(f"{uav['id']} -> GCS Connected: {connected}")