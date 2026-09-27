# Data Interfaces

All data structures used across the swarm + communication system.

---

## UAV State

```json
{
  "id": "UAV_1",
  "position": { "x": 0, "y": 0, "z": 100 },
  "battery": 95,
  "status": "idle | on_mission | relay | failed | returning",
  "role": "mission | relay | standby",
  "current_mission": "M1 | null",
  "max_speed": 15.0,
  "comm_range": 800
}
```

| Field            | Type   | Mutated By                          |
|------------------|--------|-------------------------------------|
| `status`         | str    | MissionManager, FailureManager, RecoveryManager |
| `role`           | str    | MissionManager, RecoveryManager     |
| `position`       | dict   | Integration script (simulation)     |
| `battery`        | float  | Integration script (simulation)     |
| `current_mission`| str?   | MissionManager                      |

---

## Mission

```json
{
  "id": "M1",
  "type": "surveillance | delivery | inspection",
  "priority": "low | medium | high | critical",
  "target": { "x": 500, "y": 300, "z": 100 },
  "status": "pending | assigned | in_progress | completed | failed | reassigned",
  "assigned_uav": "UAV_1 | null",
  "requirements": {
    "min_battery": 40
  }
}
```

---

## Communication Link

```json
{
  "from": "GCS | UAV_x",
  "to": "UAV_y",
  "quality": 0.85,
  "active": true
}
```

- Links are **bidirectional** in the network graph.
- `quality` range: `0.0` (dead) to `1.0` (perfect).
- `active: false` means the link has been failed.

---

## Recovery Result (returned by `RecoveryManager.attempt_recovery`)

```json
{
  "recovered": true,
  "relay_uav_id": "UAV_5",
  "disconnected_before": ["UAV_3", "UAV_4"],
  "disconnected_after": [],
  "missions_to_reassign": ["M2"],
  "relay_target_position": { "x": 250, "y": 200, "z": 100 }
}
```

---

## Relay Selection Result (returned by `relay_selector.select_relay`)

```json
{
  "relay_uav_id": "UAV_5",
  "target_position": { "x": 250, "y": 200, "z": 100 },
  "score": 0.72,
  "connects_to": {
    "bridge_anchor": "UAV_2",
    "disconnected": ["UAV_3", "UAV_4"]
  }
}
```

---

## Health Check Report (returned by `FailureManager.run_health_check`)

```json
{
  "disconnected": ["UAV_4"],
  "degraded_links": [{ "from": "UAV_3", "to": "UAV_5", "quality": 0.2 }],
  "critical_batteries": ["UAV_4"],
  "recovery_triggered": true,
  "recovery_result": { "..." }
}
```

---

## Scenario Event (from `scenarios/*.json`)

```json
{
  "time": 10,
  "type": "mission_arrive | mission_complete | link_fail | uav_fail",
  "mission_id": "M1",
  "uav_id": "UAV_4",
  "link": { "from": "UAV_2", "to": "UAV_3" }
}
```

Only the fields relevant to the event `type` are required.
