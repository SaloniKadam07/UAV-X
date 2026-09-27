# Module Interfaces

Function-level API reference for all modules in the swarm + communication system.

---

## `integration_api.SwarmController` (Person 4's entry point)

The integration script only needs to import and use this class.

### Initialization

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `initialize(uavs_path, missions_path, links_path, settings_path)` | file paths | `None` | Load from JSON files |
| `initialize_from_dicts(uavs, missions, links, settings)` | lists/dicts | `None` | Load from memory (for simulation) |

### Mission Operations

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `assign_mission(mission_id)` | str | `{mission_id, uav_id, score}` or `None` | Multi-factor allocation |
| `complete_mission(mission_id)` | str | `bool` | Frees the UAV |
| `fail_mission(mission_id, auto_reassign=True)` | str, bool | reassign result or `None` | |
| `handle_priority_event(mission_dict)` | full mission dict | assign result or `None` | Preempts if critical |

### Failure / Recovery

| Method | Args | Returns | Notes |
|--------|------|---------|-------|
| `fail_link(node_a, node_b)` | str, str | result dict | Triggers recovery if needed |
| `fail_uav(uav_id)` | str | result dict | Removes from network + reassigns mission |
| `health_check()` | — | report dict | Full connectivity + battery check |

### Network Queries

| Method | Args | Returns |
|--------|------|---------|
| `get_disconnected_uavs()` | — | `list[str]` |
| `get_network_snapshot()` | — | `{nodes, active_links, disconnected}` |
| `can_uav_reach_gcs(uav_id)` | str | `bool` |
| `get_path_to_gcs(uav_id)` | str | `list[str]` or `None` |

### State Queries

| Method | Returns |
|--------|---------|
| `get_uav_states()` | deep copy of all UAV states |
| `get_uav_state(uav_id)` | single UAV state or `None` |
| `get_active_missions()` | assigned/in-progress missions |
| `get_pending_missions()` | pending/reassigned missions |
| `get_event_log()` | mission lifecycle events |
| `get_failure_log()` | failure events |
| `get_recovery_log()` | recovery actions |

### Manual Overrides (simulation sync)

| Method | Args | Notes |
|--------|------|-------|
| `update_uav_position(uav_id, {x,y,z})` | str, dict | Call each sim tick |
| `update_uav_battery(uav_id, pct)` | str, float | Call each sim tick |
| `restore_link(node_a, node_b, quality)` | str, str, float | After physical repositioning |

---

## `swarm/task_allocator.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `select_uav(uav_states, mission, network_graph)` | lists, dict, NetworkGraph | `{uav_id, score}` or `None` |
| `rank_uavs(uav_states, mission, network_graph)` | same | sorted list of `{uav_id, score}` |
| `score_uav(uav, mission, network_graph)` | single UAV dict, mission dict | `float` or `None` |

**Scoring factors** (weights from `constants.py`):

| Factor | Weight | What it measures |
|--------|--------|------------------|
| Battery | 0.25 | `battery / 100` |
| Distance | 0.30 | Inverse distance to target, capped at 2000m |
| Priority | 0.15 | Mission priority normalized to [0.25, 1.0] |
| Connectivity | 0.15 | Node degree / max_degree |
| Role | 0.15 | Idle standby=1.0, idle mission=0.8, busy=0.2 |

---

## `swarm/mission_manager.MissionManager`

| Method | What it does |
|--------|-------------|
| `assign_mission(mid, uav_states, network)` | Allocate pending mission |
| `reassign_mission(mid, uav_states, network, exclude_uav)` | Re-allocate after failure |
| `complete_mission(mid, uav_states)` | Mark done, free UAV |
| `fail_mission(mid, uav_states, network, auto_reassign)` | Mark failed, optionally re-queue |
| `handle_priority_event(mission_dict, uav_states, network)` | Critical preemption |

---

## `swarm/failure_manager.FailureManager`

| Method | What it does |
|--------|-------------|
| `process_link_failure(a, b, uav_states)` | Handle broken link → recovery |
| `process_uav_failure(uav_id, uav_states)` | Handle UAV down → recovery + reassign |
| `run_health_check(uav_states)` | Periodic full check |
| `check_critical_batteries(uav_states)` | Return UAVs below 15% |

---

## `communication/network_graph.NetworkGraph`

| Method | What it does |
|--------|-------------|
| `load_links(path)` / `load_links_from_list(links)` | Build graph |
| `can_reach_gcs(node_id)` | BFS reachability check |
| `find_path_to_gcs(node_id)` | BFS shortest-hop path |
| `get_disconnected_nodes()` | Nodes without GCS path |
| `fail_link(a, b)` | Remove link |
| `restore_link(a, b, quality)` | Add/restore link |
| `remove_node(node_id)` | Remove node + all edges |
| `add_relay_links(relay_id, neighbors, quality)` | Create relay bridge |
| `get_degraded_links()` | Links below quality threshold |

---

## `communication/relay_selector.select_relay`

```python
select_relay(uav_states, disconnected_ids, network_graph, gcs_position) -> dict | None
```

Scores candidates on: distance to ideal relay position (40%), battery (30%), role preference (30%).

---

## `communication/recovery.RecoveryManager`

| Method | What it does |
|--------|-------------|
| `attempt_recovery(uav_states, mission_states)` | Full recovery lifecycle |
| `release_relay(relay_uav_id, uav_states)` | Free relay back to standby |

---

## Stage 1 Flow

```
Mission arrives
  → SwarmController.assign_mission("M1")
    → task_allocator.select_uav() scores all UAVs
    → best UAV assigned, status updated

Network monitoring (periodic)
  → SwarmController.health_check()
    → network_graph.get_disconnected_nodes()

Link fails
  → SwarmController.fail_link("UAV_2", "UAV_3")
    → network_graph.fail_link()
    → detect disconnected UAVs
    → relay_selector.select_relay()
    → recovery.attempt_recovery()
      → reassign relay UAV role
      → create bridge links
      → verify connectivity restored
    → reassign displaced mission

Continue mission
```
