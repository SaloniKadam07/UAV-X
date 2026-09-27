#!/usr/bin/env python3
import json
import time
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

BASE_DIR = Path(__file__).resolve().parent.parent
UAVS_PATH = BASE_DIR / "config" / "uavs.json"
MISSION_PATH = BASE_DIR / "config" / "mission.json"

plt.ion()
fig, ax = plt.subplots(figsize=(9, 8))

while True:
    if UAVS_PATH.exists():
        try:
            with open(UAVS_PATH, "r") as f:
                drones = json.load(f)

            pois = []
            if MISSION_PATH.exists():
                with open(MISSION_PATH, "r") as f:
                    pois = json.load(f).get("pois", [])

            ax.clear()
            ax.set_xlim(-50, 1150)
            ax.set_ylim(-100, 1100)
            ax.set_title("UAV Swarm Arena (1000m x 1000m) with 10 POIs", fontsize=12)
            ax.set_xlabel("X (meters)")
            ax.set_ylabel("Y (meters)")
            ax.grid(True, linestyle="--", alpha=0.6)

            # GCS Base
            ax.scatter(0, 500, c="blue", marker="s", s=150, label="Operational Center (GCS)")
            ax.annotate("GCS (0,500)", (-45, 520), color="blue", fontweight="bold")

            # 75m buffer boundary line
            ax.axvline(x=75, color="gray", linestyle=":", label="75m Buffer")

            # 1000m x 1000m Arena Box
            arena = patches.Rectangle((75, 0), 1000, 1000, linewidth=2, edgecolor='black', facecolor='whitesmoke', alpha=0.3)
            ax.add_patch(arena)

            # Draw POIs
            for p in pois:
                px, py = p["position"][0], p["position"][1]
                p_col = "green" if p.get("reported_to_center") else ("orange" if p.get("detected") else "red")
                ax.scatter(px, py, c=p_col, marker="o", s=80, edgecolors="darkred")
                ax.annotate(p["id"], (px + 10, py + 10), fontsize=7, color="darkred")

            # Plot UAVs & 100m Comm Radii
            for d in drones:
                x, y, z = d["position"]
                status = d["status"]
                color = 'green' if status == 'ACTIVE' else ('orange' if status == 'RETURNING' else 'purple')

                comm = patches.Circle((x, y), 100, linewidth=1, edgecolor=color, facecolor=color, alpha=0.08)
                ax.add_patch(comm)

                ax.scatter(x, y, s=110, c=color, edgecolors="black")
                ax.annotate(f"{d['id']}\nAlt:{z}m", (x + 12, y + 12), fontsize=8, fontweight="bold")

            ax.legend(loc="upper right")
            plt.pause(0.2)
        except Exception:
            pass
    time.sleep(0.1)
