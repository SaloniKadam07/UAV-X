#!/usr/bin/env python3
import json
import math
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
UAVS_PATH = BASE_DIR / "config" / "uavs.json"
MISSION_PATH = BASE_DIR / "config" / "mission.json"

class Drone:
    def __init__(self, data):
        self.id = data["id"]
        self.role = data.get("role", "SURVEY")
        pos = data.get("position", [0, 0, 0])
        self.pos = [float(pos[0]), float(pos[1]), float(pos[2])]
        self.home_pos = list(self.pos)
        self.target_pos = [self.pos[0], self.pos[1], 2.0]  # Takeoff waypoint
        self.battery = float(data.get("battery", 100))
        self.status = data.get("status", "ACTIVE")
        self.failed = False
        self.speed = 2.0  # m/s

    def update(self, dt):
        if self.failed:
            self.status = "FAILED"
            if self.pos[2] > 0.0:
                self.pos[2] = max(0.0, self.pos[2] - 2.5 * dt)
            return

        # Discharge battery during flight
        if self.status != "LANDED":
            self.battery = max(0.0, self.battery - (0.05 * dt * 8.0))

        # Critical battery auto-RTH rule (< 20%) -> maps to RETURNING
        if self.battery < 20.0 and self.status not in ["RETURNING", "LANDED"]:
            print(f"[{self.id}] Critical Battery ({self.battery:.1f}%)! Triggering Auto-RTH.")
            self.trigger_rth()

        # Vector towards target
        dx = self.target_pos[0] - self.pos[0]
        dy = self.target_pos[1] - self.pos[1]
        dz = self.target_pos[2] - self.pos[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)

        if dist < 0.2:
            if self.status in ["NAVIGATING", "ACTIVE"]:
                # HOLDING mapped to ACTIVE per swarm/constants.py
                self.status = "ACTIVE"
            elif self.status == "RETURNING":
                self.target_pos[2] = 0.0
                if self.pos[2] <= 0.05:
                    self.status = "LANDED"
        else:
            step = min(dist, self.speed * dt)
            self.pos[0] += (dx / dist) * step
            self.pos[1] += (dy / dist) * step
            self.pos[2] += (dz / dist) * step

    def set_target(self, x, y, z):
        if not self.failed and self.status != "RETURNING":
            self.target_pos = [float(x), float(y), float(z)]
            self.status = "NAVIGATING"
            print(f"[{self.id}] En route to waypoint: {self.target_pos}")

    def trigger_rth(self):
        if not self.failed:
            self.target_pos = [self.home_pos[0], self.home_pos[1], 2.0]
            # RTH mapped to RETURNING per swarm/constants.py
            self.status = "RETURNING"
            print(f"[{self.id}] RTH engaged -> returning to {self.home_pos}")

    def mark_failed(self):
        self.failed = True
        self.status = "FAILED"
        print(f"[{self.id}] FAILURE INJECTED.")

    def to_dict(self):
        output_status = self.status
        if output_status in ["HOLDING", "NAVIGATING"]:
            output_status = "ACTIVE"
        elif output_status == "RTH":
            output_status = "RETURNING"

        return {
            "id": self.id,
            "role": self.role,
            "battery": int(round(self.battery)),
            "status": output_status,
            "position": [round(c, 2) for c in self.pos]
        }

class UAVSimulator:
    def __init__(self):
        with open(UAVS_PATH, "r") as f:
            raw_uavs = json.load(f)
        self.drones = {d["id"]: Drone(d) for d in raw_uavs}
        print(f"Loaded {len(self.drones)} UAVs from config/uavs.json")

    def save_state(self):
        data = [drone.to_dict() for drone in self.drones.values()]
        with open(UAVS_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def step(self, dt=0.1):
        for drone in self.drones.values():
            drone.update(dt)
        self.save_state()

    def run_stage1_demo(self):
        print("\n=== UAV-X Stage 1 Simulation Verification ===")
        dt = 0.1

        # Phase 1: Takeoff & Hold
        print("\n--> [Phase 1] Taking off to holding altitude (2.0m)...")
        for _ in range(15):
            self.step(dt)
            time.sleep(0.04)

        # Phase 2: Navigation to coordinates
        print("\n--> [Phase 2] Assigning survey and relay target coordinates...")
        if "UAV1" in self.drones:
            self.drones["UAV1"].set_target(10.0, 5.0, 3.0)
        if "UAV2" in self.drones:
            self.drones["UAV2"].set_target(5.0, 2.5, 2.5)

        for _ in range(30):
            self.step(dt)
            time.sleep(0.04)

        # Phase 3: Integration test - failure simulation
        print("\n--> [Phase 3] Integration test: Marking UAV3 as FAILED...")
        if "UAV3" in self.drones:
            self.drones["UAV3"].mark_failed()

        # Phase 4: RTH Command
        print("\n--> [Phase 4] Commanding UAV1 to Return to Home...")
        if "UAV1" in self.drones:
            self.drones["UAV1"].trigger_rth()

        for _ in range(30):
            self.step(dt)
            time.sleep(0.04)

        print("\n--> Demo run complete! Current UAV states updated in config/uavs.json.\n")

if __name__ == "__main__":
    sim = UAVSimulator()
    sim.run_stage1_demo()
