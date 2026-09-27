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

MAX_SPEED = 5.0           # 5 m/s max velocity
MAX_ALTITUDE = 100.0       # 100 m ceiling
MAX_COMM_RANGE = 100.0     # 100 m RF comm link
MIN_SEPARATION = 20.0      # 20 m safety buffer
MAX_FLIGHT_TIME = 1200.0   # 20 min battery endurance
MISSION_TIMEOUT = 2700.0   # 45 min mission limit
RECALL_TIME = 2520.0       # Auto-recall at 42 mins
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
        self.status = data.get("status", "STANDBY")
        self.failed = False
        self.speed = MAX_SPEED
        self.connected_to_gcs = False
        self.waypoints = []
        self.sector_id = None
        self.relief_requested = False

    def update(self, dt):
        if self.failed:
            self.status = "FAILED"
            if self.pos[2] > 0.0:
                self.pos[2] = max(0.0, self.pos[2] - 3.0 * dt)
            return

        # Discharge while in flight
        if self.status not in ["STANDBY", "LANDED"]:
            discharge_rate = (100.0 / MAX_FLIGHT_TIME)
            self.battery = max(0.0, self.battery - (discharge_rate * dt))

        # Recharge while landed at base pad
        if self.status == "LANDED" and self.battery < 100.0:
            recharge_rate = (100.0 / 600.0) # 10 min fast recharge
            self.battery = min(100.0, self.battery + recharge_rate * dt)
            if self.battery >= 99.0:
                self.status = "STANDBY"

        dx = self.target_pos[0] - self.pos[0]
        dy = self.target_pos[1] - self.pos[1]
        dz = self.target_pos[2] - self.pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist < 1.0:
            if self.status == "RETURNING":
                self.target_pos[2] = 0.0
                if self.pos[2] <= 0.2:
                    self.status = "LANDED"
                    self.pos[2] = 0.0
                    self.relief_requested = False
            elif self.status in ["NAVIGATING", "ACTIVE"]:
                if self.waypoints:
                    next_wp = self.waypoints.pop(0)
                    self.set_target(next_wp[0], next_wp[1], next_wp[2])
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
            self.target_pos = [self.home_pos[0], self.home_pos[1], 25.0]
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
                if isinstance(loaded, list):
                    self.pois = loaded
                    self.mission_data = {"pois": self.pois}
                elif isinstance(loaded, dict):
                    self.mission_data = loaded
                    self.pois = self.mission_data.get("pois", [])

        self.sim_time = 0.0
        self.dispatch_initial_missions()

    def dispatch_initial_missions(self):
        # Layered flight corridors with non-conflicting climb paths
        if "UAV2" in self.drones:
            self.drones["UAV2"].role = "RELAY"
            self.drones["UAV2"].set_target(85.0, 460.0, 30.0)
        if "UAV4" in self.drones:
            self.drones["UAV4"].role = "RELAY"
            self.drones["UAV4"].set_target(170.0, 520.0, 50.0)

        if "UAV1" in self.drones:
            self.drones["UAV1"].role = "SURVEY"
            self.drones["UAV1"].sector_id = 0
            wps1 = self.planner.generate_survey_corridors(sector_id=0, total_sectors=2)
            wps1 = [[w[0], w[1], 70.0] for w in wps1]
            self.drones["UAV1"].waypoints = wps1[1:]
            self.drones["UAV1"].set_target(175.0, 200.0, 70.0)

        if "UAV3" in self.drones:
            self.drones["UAV3"].role = "SURVEY"
            self.drones["UAV3"].sector_id = 1
            wps2 = self.planner.generate_survey_corridors(sector_id=1, total_sectors=2)
            wps2 = [[w[0], w[1], 90.0] for w in wps2]
            self.drones["UAV3"].waypoints = wps2[1:]
            self.drones["UAV3"].set_target(175.0, 750.0, 90.0)

    def manage_battery_rotation(self):
        """Monitors battery levels and orchestrates reserve swaps."""
        for drone in self.drones.values():
            if drone.status in ["ACTIVE", "NAVIGATING"] and drone.battery <= 25.0 and not drone.relief_requested:
                drone.relief_requested = True
                print(f"⚠️ [{drone.id}] Battery at {drone.battery:.1f}%! Requesting relief rotation.")
                
                # Check for an available standby drone at base
                standby = [d for d in self.drones.values() if d.status == "STANDBY" and d.battery > 80.0]
                if standby:
                    reliever = standby[0]
                    reliever.role = drone.role
                    reliever.sector_id = drone.sector_id
                    reliever.waypoints = list(drone.waypoints)
                    
                    # Handover target waypoint
                    reliever.set_target(drone.target_pos[0], drone.target_pos[1], drone.target_pos[2])
                    print(f"🔄 Swapping: {reliever.id} taking over sector {drone.sector_id} from {drone.id}")
                
                drone.trigger_rth()

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
                if d <= MAX_COMM_RANGE:
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
                    if dist <= 60.0 and not poi.get("detected"):
                        poi["detected"] = True
                        poi["detect_time_s"] = round(self.sim_time, 1)
                        poi["detected_by"] = d.id
                        print(f"🎯 [{d.id}] DETECTED {poi['id']} at ({px:.1f}, {py:.1f})")

                    if poi.get("detected") and not poi.get("reported_to_center"):
                        if d.connected_to_gcs:
                            poi["reported_to_center"] = True
                            poi["report_time_s"] = round(self.sim_time, 1)
                            latency = poi["report_time_s"] - poi["detect_time_s"]
                            flag = "✅ COMPLIANT" if latency <= 10.0 else "❌ VIOLATION (>10s)"
                            print(f"📡 [GCS] REPORT: {poi['id']} via {d.id} | Latency: {latency:.1f}s [{flag}]")

    def check_separation(self):
        active = [d for d in self.drones.values() if d.status not in ["LANDED", "FAILED", "STANDBY"]]
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                dist = math.dist(active[i].pos, active[j].pos)
                if dist < MIN_SEPARATION:
                    print(f"⚠️ PROXIMITY ALERT: {active[i].id} & {active[j].id} ({dist:.1f}m < 20m)")

    def check_mission_timer(self):
        if self.sim_time >= RECALL_TIME:
            for d in self.drones.values():
                if d.status not in ["RETURNING", "LANDED"]:
                    print(f"🛑 Mission approaching 45min limit. Recalling {d.id} to GCS.")
                    d.trigger_rth()

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
        self.manage_battery_rotation()
        self.update_mesh_connectivity()
        self.process_poi_detections()
        self.check_separation()
        self.check_mission_timer()
        self.save_state()

    def run_autonomous_mission(self, steps=80):
        print("\n=== UAV-X Swarm Mission Running (Battery Management Active) ===")
        dt = 0.5
        for _ in range(steps):
            self.step(dt)
            time.sleep(0.03)
        print("--> Mission cycle executed cleanly. Telemetry synced.")

if __name__ == "__main__":
    sim = UAVSimulator()
    sim.run_autonomous_mission()
