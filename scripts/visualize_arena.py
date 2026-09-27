#!/usr/bin/env python3
import json
import math
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.animation as animation

BASE_DIR = Path(__file__).resolve().parent.parent
UAVS_PATH = BASE_DIR / "config" / "uavs.json"
MISSION_PATH = BASE_DIR / "config" / "mission.json"

fig, ax = plt.subplots(figsize=(9, 8))

def update(frame):
    ax.clear()
    ax.set_xlim(-50, 1050)
    ax.set_ylim(-50, 1050)
    ax.set_xlabel("X (meters)")
    ax.set_ylabel("Y (meters)")
    ax.set_title("UAV Swarm Live Telemetry & Mission Tracking")
    ax.grid(True, linestyle="--", alpha=0.5)

    # Plot GCS & 75m buffer
    ax.scatter([0], [500], c="blue", s=150, marker="s", label="GCS (0, 500)")
    circle = plt.Circle((0, 500), 75, color="blue", fill=False, linestyle=":", label="75m Buffer")
    ax.add_patch(circle)

    # Plot POIs
    if MISSION_PATH.exists():
        try:
            with open(MISSION_PATH, "r") as f:
                data = json.load(f)
                pois = data.get("pois", []) if isinstance(data, dict) else data
                for p in pois:
                    px, py = p["position"][0], p["position"][1]
                    is_detected = p.get("detected", False)
                    color = "limegreen" if is_detected else "gray"
                    ax.scatter(px, py, c=color, s=80, marker="o")
                    status_lbl = " [FOUND]" if is_detected else ""
                    ax.text(px + 10, py + 10, f"{p['id']}{status_lbl}", fontsize=8, color=color, weight="bold" if is_detected else "normal")
        except Exception:
            pass

    # Plot Live Drones
    if UAVS_PATH.exists():
        try:
            with open(UAVS_PATH, "r") as f:
                uavs = json.load(f)
                for d in uavs:
                    x, y, z = d["position"][0], d["position"][1], d["position"][2]
                    status = d.get("status", "ACTIVE")
                    color = "red" if d["role"] == "SURVEY" else "orange"
                    ax.scatter(x, y, c=color, s=120, edgecolors="black", zorder=5)
                    label = f"{d['id']} ({d['role']})\nAlt: {z:.1f}m | Bat: {d['battery']}%\n[{status}]"
                    ax.text(x + 12, y - 10, label, fontsize=8, bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.7))
        except Exception:
            pass

    ax.legend(loc="upper right")

ani = animation.FuncAnimation(fig, update, interval=500)
plt.show()
