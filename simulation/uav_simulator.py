#!/usr/bin/env python3
import json
import math
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UAVS_PATH = BASE_DIR / "config" / "uavs.json"
MISSION_PATH = BASE_DIR / "config" / "mission.json"

MAX_SPEED = 5.0          # 5 m/s max velocity
MAX_ALTITUDE = 100.0      # 100 m operational ceiling
MAX_COMM_RANGE = 100.0    # 100 m max direct RF link
MIN_SEPARATION = 20.0     # 20 m safety buffer
MAX_FLIGHT_TIME = 1200.0  # 20 min endurance (seconds)
GCS_POS = [0.0, 500.0, 0.0]

class Drone:
    def __init__(self, data):
        self.id = data["id"]
        self.role = data.get("role", "SURVEY")
        pos = data.get("position", [0.0, 500.0, 0.0])
        self.pos = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.home_pos = list(self.pos)
        self.target_pos = list(self.pos)
        self.battery = float(data.get("battery", 100.0))
        self.status = data.get("status", "ACTIVE")
        self.failed = False
        self.speed = MAX_SPEED
        self.connected_to_gcs = False

    def update(self, dt):
        if self.failed:
            self.status = "FAILED"
            if self.pos[2] > 0.0:
                self.pos[2] = max(0.0, self.pos[2] - 3.0 * dt)
            return

        if self.status != "LANDED":
            discharge_rate = (100.0 / MAX_FLIGHT_TIME)
            self.battery = max(0.0, self.battery - (discharge_rate * dt))

        if self.battery < 20.0 and self.status not in ["RETURNING", "LANDED"]:
            print(f"[{self.id}] Critical battery ({self.battery:.1f}%)! Returning to home.")
            self.trigger_rth()

        dx = self.target_pos[0] - self.pos[0]
        dy = self.target_pos[1] - self.pos[1]
        dz = self.target_pos[2] - self.pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist < 0.5:
            if self.status == "NAVIGATING":
                self.status = "ACTIVE"
            elif self.status == "RETURNING":
                self.target_pos[2] = 0.0
                if self.pos[2] <= 0.2:
                    self.status = "LANDED"
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
            self.target_pos = [self.home_pos[0], self.home_pos[1], 20.0]
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
        
        self.pois = []
        if MISSION_PATH.exists():
            with open(MISSION_PATH, "r") as f:
                self.mission_data = json.load(f)
                self.pois = self.mission_data.get("pois", [])
        else:
            self.mission_data = {}

        self.sim_time = 0.0

    def update_mesh_connectivity(self):
        """Build ad-hoc topology graph and find multi-hop routes back to GCS."""
        nodes = ["GCS"] + [d.id for d in self.drones.values() if d.status not in ["LANDED", "FAILED"]]
        positions = {"GCS": GCS_POS}
        for d in self.drones.values():
            positions[d.id] = d.pos

        # Adjacency list within 100m range
        adj = {node: [] for node in nodes}
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1, n2 = nodes[i], nodes[j]
                p1, p2 = positions[n1], positions[n2]
                dist = math.sqrt(sum((a - b)**2 for a, b in zip(p1, p2)))
                if dist <= MAX_COMM_RANGE:
                    adj[n1].append(n2)
                    adj[n2].append(n1)

        # BFS from GCS to find reachable UAVs
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

    def check_poi_detections(self):
        """Sensors detect POIs within 60m. Reports must reach GCS via mesh within 10s."""
        for poi in self.pois:
            px, py = poi["position"][0], poi["position"][1]
            
            # Check detection by active survey drones
            for d in self.drones.values():
                if d.status in ["ACTIVE", "NAVIGATING"]:
                    dist = math.hypot(d.pos[0] - px, d.pos[1] - py)
                    if dist <= 60.0 and not poi.get("detected"):
                        poi["detected"] = True
                        poi["detect_time_s"] = round(self.sim_time, 1)
                        poi["detected_by"] = d.id
                        print(f"🎯 [{d.id}] DETECTED {poi['id']} at ({px:.1f}, {py:.1f})! Seeking GCS route...")

                    # Relay through connected mesh to GCS
                    if poi.get("detected") and not poi.get("reported_to_center"):
                        if d.connected_to_gcs:
                            poi["reported_to_center"] = True
                            poi["report_time_s"] = round(self.sim_time, 1)
                            latency = poi["report_time_s"] - poi["detect_time_s"]
                            flag = "✅ COMPLIANT" if latency <= 10.0 else "❌ VIOLATION (>10s)"
                            print(f"📡 [GCS] REPORT RECEIVED: {poi['id']} via {d.id} | Latency: {latency:.1f}s [{flag}]")

    def check_separation(self):
        active = [d for d in self.drones.values() if d.status not in ["LANDED", "FAILED"]]
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                p1, p2 = active[i].pos, active[j].pos
                dist = math.sqrt(sum((a - b)**2 for a, b in zip(p1, p2)))
                if dist < MIN_SEPARATION:
                    print(f"⚠️ PROXIMITY ALERT: {active[i].id} & {active[j].id} ({dist:.1f}m < 20m)")

    def save_state(self):
        data = [drone.to_dict() for drone in self.drones.values()]
        with open(UAVS_PATH, "w") as f:
            json.dump(data, f, indent=2)

        if self.pois:
            self.mission_data["pois"] = self.pois
            with open(MISSION_PATH, "w") as f:
                json.dump(self.mission_data, f, indent=2)

    def step(self, dt=0.5):
        self.sim_time += dt
        for drone in self.drones.values():
            drone.update(dt)
        self.update_mesh_connectivity()
        self.check_poi_detections()
        self.check_separation()
        self.save_state()

    def run_mission(self):
        print("\n=== Executing Swarm Relay & POI Search Mission ===")
        dt = 0.5

        # Dispatch UAV2 & UAV4 as relay chain stations across the 75m buffer line
        self.drones["UAV2"].set_target(80.0, 485.0, 30.0)
        self.drones["UAV4"].set_target(160.0, 450.0, 40.0)

        # Dispatch UAV1 and UAV3 on deep survey vector towards nearest POIs
        self.drones["UAV1"].set_target(220.0, 420.0, 40.0)
        self.drones["UAV3"].set_target(210.0, 550.0, 45.0)

        for _ in range(60):
            self.step(dt)
            time.sleep(0.02)

        print("--> Mission iteration complete. Telemetry saved.")

if __name__ == "__main__":
    sim = UAVSimulator()
    sim.run_mission()
