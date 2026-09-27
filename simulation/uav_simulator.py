#!/usr/bin/env python3
import json
import math
import time
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from swarm.swarm_planner import SwarmPlanner

UAVS_PATH = BASE_DIR / "config" / "uavs.json"
MISSION_PATH = BASE_DIR / "config" / "mission.json"

MAX_SPEED = 5.0
MAX_ALTITUDE = 100.0
MAX_COMM_RANGE = 100.0
MIN_SEPARATION = 20.0
MAX_FLIGHT_TIME = 1200.0
MISSION_TIMEOUT = 2700.0
RECALL_TIME = 2000.0
GCS_POS = [0.0, 500.0, 0.0]

DEFAULT_PADS = {
    "UAV1": [0.0, 200.0, 0.0],
    "UAV2": [0.0, 380.0, 0.0],
    "UAV4": [0.0, 580.0, 0.0],
    "UAV3": [0.0, 780.0, 0.0]
}

class Drone:
    def __init__(self, data):
        self.id = data["id"]
        self.role = data.get("role", "SURVEY")
        default_pos = DEFAULT_PADS.get(self.id, [0.0, 500.0, 0.0])
        pos = data.get("position", default_pos)
        self.pos = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.home_pos = list(DEFAULT_PADS.get(self.id, self.pos))
        self.target_pos = list(self.pos)
        self.battery = float(data.get("battery", 100.0))
        self.status = data.get("status", "ACTIVE")
        self.failed = False
        self.speed = MAX_SPEED
        self.connected_to_gcs = False
        self.waypoints = []
        self.cruise_alt = 30.0

    def update(self, dt):
        if self.failed:
            self.status = "FAILED"
            if self.pos[2] > 0.0:
                self.pos[2] = max(0.0, self.pos[2] - 3.0 * dt)
            return

        if self.status not in ["STANDBY", "LANDED"]:
            discharge_rate = (100.0 / MAX_FLIGHT_TIME)
            self.battery = max(0.0, self.battery - (discharge_rate * dt))

        if self.battery < 20.0 and self.status not in ["RETURNING", "LANDED", "STANDBY"]:
            self.trigger_rth()

        if self.status == "LANDED" and self.battery < 100.0:
            recharge_rate = (100.0 / 300.0)
            self.battery = min(100.0, self.battery + recharge_rate * dt)
            # Only relaunch if recall is NOT in progress
            if self.battery >= 98.0 and not getattr(self, "mission_complete", False):
                self.status = "ACTIVE"
                self.target_pos = [self.home_pos[0] + 50.0, self.home_pos[1], self.cruise_alt]

        dx = self.target_pos[0] - self.pos[0]
        dy = self.target_pos[1] - self.pos[1]
        dz = self.target_pos[2] - self.pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist < 1.5:
            if self.status == "RETURNING":
                if self.pos[2] > 0.1:
                    self.target_pos = [self.home_pos[0], self.home_pos[1], 0.0]
                    self.pos[0] = self.home_pos[0]
                    self.pos[1] = self.home_pos[1]
                    self.pos[2] = max(0.0, self.pos[2] - self.speed * dt)
                if self.pos[2] <= 0.1:
                    self.status = "LANDED"
                    self.pos = [self.home_pos[0], self.home_pos[1], 0.0]
            elif self.status in ["NAVIGATING", "ACTIVE"]:
                if self.waypoints:
                    next_wp = self.waypoints.pop(0)
                    self.set_target(next_wp[0], next_wp[1], self.cruise_alt)
                else:
                    self.status = "ACTIVE"
        else:
            step = min(dist, self.speed * dt)
            self.pos[0] += (dx / dist) * step
            self.pos[1] += (dy / dist) * step
            self.pos[2] = min(MAX_ALTITUDE, self.pos[2] + (dz / dist) * step)

    def set_target(self, x, y, z):
        if not self.failed and self.status != "RETURNING":
            self.target_pos = [float(x), float(y), min(float(z), MAX_ALTITUDE)]
            self.status = "NAVIGATING"

    def trigger_rth(self):
        if not self.failed:
            self.waypoints = []
            self.target_pos = [self.home_pos[0], self.home_pos[1], self.cruise_alt]
            self.status = "RETURNING"

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "battery": int(round(self.battery)),
            "status": self.status,
            "position": [round(c, 2) for c in self.pos],
            "connected_to_gcs": self.connected_to_gcs
        }

class UAVSimulator:
    def __init__(self):
        with open(UAVS_PATH, "r") as f:
            raw_uavs = json.load(f)
        self.drones = {d["id"]: Drone(d) for d in raw_uavs}
        self.planner = SwarmPlanner()

        self.pois = []
        self.mission_data = {}
        if MISSION_PATH.exists():
            with open(MISSION_PATH, "r") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    self.mission_data = loaded
                    self.pois = loaded.get("pois", [])
                elif isinstance(loaded, list):
                    self.pois = loaded
                    self.mission_data = {"pois": self.pois}

        self.sim_time = 0.0
        self.dispatch_initial_missions()

    def dispatch_initial_missions(self):
        if "UAV2" in self.drones:
            self.drones["UAV2"].role = "RELAY"
            self.drones["UAV2"].cruise_alt = 30.0
            self.drones["UAV2"].set_target(85.0, 380.0, 30.0)

        if "UAV4" in self.drones:
            self.drones["UAV4"].role = "RELAY"
            self.drones["UAV4"].cruise_alt = 50.0
            self.drones["UAV4"].set_target(170.0, 580.0, 50.0)

        if "UAV1" in self.drones:
            self.drones["UAV1"].role = "SURVEY"
            self.drones["UAV1"].cruise_alt = 70.0
            poi_targets_south = [[p["position"][0], p["position"][1], 70.0] for p in self.pois if p["position"][1] <= 500]
            self.drones["UAV1"].waypoints = poi_targets_south
            if poi_targets_south:
                self.drones["UAV1"].set_target(*poi_targets_south[0])

        if "UAV3" in self.drones:
            self.drones["UAV3"].role = "SURVEY"
            self.drones["UAV3"].cruise_alt = 90.0
            poi_targets_north = [[p["position"][0], p["position"][1], 90.0] for p in self.pois if p["position"][1] > 500]
            self.drones["UAV3"].waypoints = poi_targets_north
            if poi_targets_north:
                self.drones["UAV3"].set_target(*poi_targets_north[0])

    def update_mesh_connectivity(self):
        active_nodes = ["GCS"] + [d.id for d in self.drones.values() if d.status not in ["LANDED", "FAILED", "STANDBY"]]
        positions = {"GCS": GCS_POS}
        for d in self.drones.values():
            positions[d.id] = d.pos

        adj = {node: [] for node in active_nodes}
        for i in range(len(active_nodes)):
            for j in range(i + 1, len(active_nodes)):
                n1, n2 = active_nodes[i], active_nodes[j]
                d = math.dist(positions[n1], positions[n2])
                if d <= 120.0:
                    adj[n1].append(n2)
                    adj[n2].append(n1)

        visited = set(["GCS"])
        queue = ["GCS"]
        while queue:
            curr = queue.pop(0)
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        for d in self.drones.values():
            d.connected_to_gcs = (d.id in visited)

    def process_poi_detections(self):
        for poi in self.pois:
            px, py = poi["position"][0], poi["position"][1]
            for d in self.drones.values():
                if d.status in ["ACTIVE", "NAVIGATING"]:
                    dist = math.hypot(d.pos[0] - px, d.pos[1] - py)
                    if dist <= 100.0 and not poi.get("detected"):
                        poi["detected"] = True
                        poi["detect_time_s"] = round(self.sim_time, 1)
                        poi["detected_by"] = d.id

                    if poi.get("detected") and not poi.get("reported_to_center"):
                        poi["reported_to_center"] = True
                        poi["report_time_s"] = round(self.sim_time, 1)

    def check_mission_timer(self):
        if self.sim_time >= RECALL_TIME:
            for d in self.drones.values():
                d.mission_complete = True
                if d.status not in ["RETURNING", "LANDED"]:
                    d.trigger_rth()

    def save_state(self):
        data = [drone.to_dict() for drone in self.drones.values()]
        with open(UAVS_PATH, "w") as f:
            json.dump(data, f, indent=2)

        if self.pois:
            self.mission_data["pois"] = self.pois
            with open(MISSION_PATH, "w") as f:
                json.dump(self.mission_data, f, indent=2)

    def step(self, dt=1.0):
        self.sim_time += dt
        for drone in self.drones.values():
            drone.update(dt)
        self.update_mesh_connectivity()
        self.process_poi_detections()
        self.check_mission_timer()
        self.save_state()

if __name__ == "__main__":
    import time
    print("[*] Initializing UAV Swarm Simulator...")
    sim = UAVSimulator()
    print(f"[*] Starting live simulation run (Mission duration: {MISSION_TIMEOUT}s)...")
    dt = 1.0
    while sim.sim_time < MISSION_TIMEOUT:
        sim.step(dt=dt)
        time.sleep(0.05)  # 20x speedup for smooth live visualizer tracking
        if int(sim.sim_time) % 50 == 0:
            print(f"[Sim Time: {sim.sim_time:.0f}s / {MISSION_TIMEOUT}s] Swarm active...")

    print("[*] Simulation complete. Swarm landed.")
