import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from swarm.failure_manager import fail_uav, fail_link

uavs_path = BASE_DIR / "config" / "uavs.json"
links_path = BASE_DIR / "config" / "links.json"

with open(uavs_path, "r") as f:
    uavs = json.load(f)

with open(links_path, "r") as f:
    links = json.load(f)

print("\n=== FAILURE MANAGER TEST ===")

failed_uav = fail_uav(uavs, "UAV3")

if failed_uav:
    print(f"UAV Failed: {failed_uav['id']}")
    print(f"New Status: {failed_uav['status']}")

failed_link = fail_link(links, "UAV1", "UAV2")

if failed_link:
    print(
        f"Link Failed: {failed_link['from']} -> {failed_link['to']}"
    )
    print(f"Connected: {failed_link['connected']}")