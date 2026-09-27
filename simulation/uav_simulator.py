#!/usr/bin/env python3
import json
import math
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UAVS_PATH = BASE_DIR / "config" / "uavs.json"
MISSION_PATH = BASE_DIR / "config" / "mission.json"

MAX_SPEED = 5.0
MAX_ALTITUDE = 100.0
MAX_COMM_RANGE = 100.0
MIN_SEPARATION = 20.0
MAX_FLIGHT_TIME = 1200.0

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

    def mark_failed(self):
        self.failed = True
        self.status = "FAILED"

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "battery": int(round(self.battery)),
            "status": self.status,
            "position": [round(c, 2) for c in self.pos]
        }

class UAVSimulator:
    def __init__(self):
        with open(UAVS_PATH, "r") as f:
            raw_uavs = json.load(f)
        self.drones = {d["id"]: Drone(d) for d in raw_uavs}

    def check_separation(self):
        active = [d for d in self.drones.values() if d.status not in ["LANDED", "FAILED"]]
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                p1, p2 = active[i].pos, active[j].pos
                dist = math.sqrt(sum((a - b)**2 for a, b in zip(p1, p2)))
                if dist < MIN_SEPARATION:
                    print(f"PROXIMITY ALERT: {active[i].id} & {active[j].id} separation {dist:.1f}m < 20m!")

    def save_state(self):
        data = [drone.to_dict() for drone in self.drones.values()]
        with open(UAVS_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def step(self, dt=0.5):
        for drone in self.drones.values():
            drone.update(dt)
        self.check_separation()
        self.save_state()

    def run_stage1_demo(self):
        print("\n=== UAV-X Mission Area Simulation ===")
        dt = 0.5
        print("--> Drones taking off from Operational Center...")
        if "UAV1" in self.drones:
            self.drones["UAV1"].set_target(200.0, 500.0, 30.0)
        if "UAV2" in self.drones:
            self.drones["UAV2"].set_target(100.0, 500.0, 30.0)
        if "UAV3" in self.drones:
            self.drones["UAV3"].set_target(200.0, 600.0, 30.0)

        for _ in range(40):
            self.step(dt)
            time.sleep(0.02)

        print("--> Updating states in config/uavs.json.")

if __name__ == "__main__":
    sim = UAVSimulator()
    sim.run_stage1_demo()
