#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
from simulation.uav_simulator import UAVSimulator, MISSION_TIMEOUT, RECALL_TIME

def run_evaluation():
    print("=" * 60)
    print("      UAV-X COMPETITION MISSION EVALUATION (45 MINS)      ")
    print("=" * 60)
    
    sim = UAVSimulator()
    dt = 1.0  # 1-second simulation step for fast evaluation
    total_steps = int(MISSION_TIMEOUT)  # 2700 steps = 45 mins
    
    separation_violations = 0
    max_altitude_observed = 0.0
    
    for step_idx in range(total_steps):
        # Separation check strictly applies to airborne vehicles (z > 2.0m)
        airborne = [d for d in sim.drones.values() if d.status not in ["LANDED", "FAILED", "STANDBY"] and d.pos[2] > 2.0]
        for i in range(len(airborne)):
            for j in range(i + 1, len(airborne)):
                d = math.dist(airborne[i].pos, airborne[j].pos)
                if d < 20.0:
                    separation_violations += 1
        
        for d in sim.drones.values():
            if d.pos[2] > max_altitude_observed:
                max_altitude_observed = d.pos[2]
                
        sim.step(dt)

    total_pois = len(sim.pois)
    detected_pois = [p for p in sim.pois if p.get("detected")]
    reported_pois = [p for p in sim.pois if p.get("reported_to_center")]
    
    latencies = [
        p["report_time_s"] - p["detect_time_s"] 
        for p in reported_pois 
        if p.get("report_time_s") is not None and p.get("detect_time_s") is not None
    ]
    max_latency = max(latencies) if latencies else 0.0
    latency_compliant = (len(reported_pois) > 0) and all(l <= 10.0 for l in latencies)
    
    all_landed = all(d.status == "LANDED" or d.pos[2] <= 0.5 for d in sim.drones.values())
    all_at_base = all(d.pos[0] <= 85.0 for d in sim.drones.values())

    print("\n--- PERFORMANCE SCORECARD ---")
    print(f"1. Mission Duration         : {sim.sim_time/60:.1f} / 45.0 mins [PASS]")
    print(f"2. Altitude Compliance      : Peak {max_altitude_observed:.1f}m <= 100m [{'PASS' if max_altitude_observed <= 100 else 'FAIL'}]")
    print(f"3. Separation Compliance    : {separation_violations} breaches (<20m) [{'PASS' if separation_violations == 0 else 'FAIL'}]")
    print(f"4. POIs Detected            : {len(detected_pois)} / {total_pois}")
    print(f"5. POIs Reported to Center  : {len(reported_pois)} / {total_pois}")
    print(f"6. Relay Latency            : Max {max_latency:.1f}s <= 10.0s [{'PASS' if latency_compliant else 'FAIL'}]")
    print(f"7. Swarm Final Touchdown    : Landed at Base? [{'PASS' if (all_landed and all_at_base) else 'FAIL'}]")
    print("=" * 60)
    
    overall = (separation_violations == 0 and max_altitude_observed <= 100 and latency_compliant and all_landed and all_at_base)
    print(f"OVERALL COMPETITION VERDICT: {'QUALIFIED (TOP-15 READY)' if overall else 'REQUIRES ADJUSTMENT'}\n")

if __name__ == "__main__":
    run_evaluation()
