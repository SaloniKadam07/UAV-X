"""
demo_stage1.py

Runs the full Stage 1 flow end-to-end using the failure_mission scenario:
  Mission arrives → Select UAV → Monitor network → Link fails →
  Detect disconnected → Select relay → Reassign role → Continue mission

Run:  python demo_stage1.py
"""

import json
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from integration_api import SwarmController

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-7s │ %(name)-35s │ %(message)s",
)
log = logging.getLogger("demo")


def banner(text: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def print_state(ctrl: SwarmController) -> None:
    print("\n  UAV states:")
    for u in ctrl.get_uav_states():
        reach = "✓ GCS" if ctrl.can_uav_reach_gcs(u["id"]) else "✗ DISCONNECTED"
        print(f"    {u['id']:6s}  bat={u['battery']:3.0f}%  "
              f"status={u['status']:12s}  role={u['role']:8s}  "
              f"mission={str(u.get('current_mission', '-')):4s}  {reach}")

    active = ctrl.get_active_missions()
    pending = ctrl.get_pending_missions()
    print(f"\n  Active missions: {[m['id'] for m in active]}")
    print(f"  Pending missions: {[m['id'] for m in pending]}")
    disc = ctrl.get_disconnected_uavs()
    print(f"  Disconnected UAVs: {disc if disc else 'none'}")


def main():
    ctrl = SwarmController()

    base = os.path.dirname(__file__)
    ctrl.initialize(
        uavs_path=os.path.join(base, "config", "uavs.json"),
        missions_path=os.path.join(base, "config", "mission.json"),
        links_path=os.path.join(base, "config", "links.json"),
        settings_path=os.path.join(base, "config", "settings.json"),
    )

    # Load failure scenario
    with open(os.path.join(base, "scenarios", "failure_mission.json")) as f:
        scenario = json.load(f)

    banner("INITIAL STATE")
    print_state(ctrl)

    # ── Process scenario events ───────────────────────────
    for event in scenario["events"]:
        t = event["time"]
        etype = event["type"]

        if etype == "mission_arrive":
            mid = event["mission_id"]
            banner(f"t={t}  MISSION ARRIVES: {mid}")
            result = ctrl.assign_mission(mid)
            if result:
                print(f"  → Assigned {mid} to {result['uav_id']} (score={result['score']:.3f})")
            else:
                print(f"  → Could not assign {mid}")
            print_state(ctrl)

        elif etype == "link_fail":
            a, b = event["link"]["from"], event["link"]["to"]
            banner(f"t={t}  LINK FAILURE: {a} <-> {b}")
            result = ctrl.fail_link(a, b)
            print(f"  → Disconnected after failure: {result['disconnected']}")
            if result.get("recovery"):
                rec = result["recovery"]
                print(f"  → Recovery {'SUCCEEDED' if rec['recovered'] else 'FAILED'}")
                if rec.get("relay_uav_id"):
                    print(f"    Relay: {rec['relay_uav_id']} → pos {rec.get('relay_target_position')}")
                if rec.get("disconnected_after"):
                    print(f"    Still disconnected: {rec['disconnected_after']}")
            if result.get("reassigned_missions"):
                for r in result["reassigned_missions"]:
                    print(f"  → Mission {r['mission_id']} reassigned to {r['uav_id']}")
            print_state(ctrl)

        elif etype == "uav_fail":
            uid = event["uav_id"]
            banner(f"t={t}  UAV FAILURE: {uid}")
            result = ctrl.fail_uav(uid)
            print(f"  → Affected neighbors: {result['affected_neighbors']}")
            if result.get("affected_mission"):
                print(f"  → Lost mission: {result['affected_mission']}")
            if result.get("mission_reassignment"):
                r = result["mission_reassignment"]
                print(f"  → Mission reassigned to {r['uav_id']}")
            if result.get("recovery"):
                rec = result["recovery"]
                print(f"  → Recovery {'SUCCEEDED' if rec['recovered'] else 'FAILED'}")
            print_state(ctrl)

        elif etype == "mission_complete":
            mid = event["mission_id"]
            banner(f"t={t}  MISSION COMPLETE: {mid}")
            ctrl.complete_mission(mid)
            print_state(ctrl)

    # ── Final health check ────────────────────────────────
    banner("FINAL HEALTH CHECK")
    report = ctrl.health_check()
    print(f"  Disconnected: {report['disconnected'] or 'none'}")
    print(f"  Degraded links: {len(report['degraded_links'])}")
    print(f"  Critical batteries: {report['critical_batteries'] or 'none'}")

    banner("DONE — Stage 1 flow complete")


if __name__ == "__main__":
    main()
