#!/usr/bin/env python3
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MISSION_PATH = BASE_DIR / "config" / "mission.json"

# Operational bounds: arena is 1000m x 1000m offset by 75m buffer from GCS
# X: 75 to 1075m, Y: 0 to 1000m
pois = []
for i in range(1, 11):
    poi = {
        "id": f"POI_{i:02d}",
        "position": [
            round(random.uniform(100.0, 1050.0), 1),
            round(random.uniform(50.0, 950.0), 1),
            0.0
        ],
        "spawn_time_s": random.randint(10, 300),  # spawned dynamically over flight
        "detected": False,
        "reported_to_center": False,
        "detect_time_s": None,
        "report_time_s": None
    }
    pois.append(poi)

mission_data = {
    "arena": {
        "origin_offset_x": 75.0,
        "width_x": 1000.0,
        "height_y": 1000.0,
        "max_altitude": 100.0
    },
    "constraints": {
        "max_comm_range_m": 100.0,
        "min_separation_m": 20.0,
        "max_reporting_delay_s": 10.0,
        "max_speed_mps": 5.0
    },
    "pois": sorted(pois, key=lambda p: p["spawn_time_s"])
}

with open(MISSION_PATH, "w") as f:
    json.dump(mission_data, f, indent=2)

print(f"Generated 10 random POIs in {MISSION_PATH}")
