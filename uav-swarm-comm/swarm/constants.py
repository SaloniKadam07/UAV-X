"""
Shared constants for the UAV swarm system.
Defines roles, statuses, priorities, and tunable thresholds.
"""

# ── UAV Roles ──────────────────────────────────────────────
ROLE_MISSION = "mission"
ROLE_RELAY = "relay"
ROLE_STANDBY = "standby"

ALL_ROLES = [ROLE_MISSION, ROLE_RELAY, ROLE_STANDBY]

# ── UAV Statuses ───────────────────────────────────────────
STATUS_IDLE = "idle"
STATUS_ON_MISSION = "on_mission"
STATUS_RELAY = "relay"
STATUS_FAILED = "failed"
STATUS_RETURNING = "returning"

ALL_STATUSES = [STATUS_IDLE, STATUS_ON_MISSION, STATUS_RELAY, STATUS_FAILED, STATUS_RETURNING]

# ── Mission Priorities (higher number = higher priority) ──
PRIORITY_LOW = 1
PRIORITY_MEDIUM = 2
PRIORITY_HIGH = 3
PRIORITY_CRITICAL = 4

PRIORITY_MAP = {
    "low": PRIORITY_LOW,
    "medium": PRIORITY_MEDIUM,
    "high": PRIORITY_HIGH,
    "critical": PRIORITY_CRITICAL,
}

# ── Mission Statuses ──────────────────────────────────────
MISSION_PENDING = "pending"
MISSION_ASSIGNED = "assigned"
MISSION_IN_PROGRESS = "in_progress"
MISSION_COMPLETED = "completed"
MISSION_FAILED = "failed"
MISSION_REASSIGNED = "reassigned"

# ── Task Allocation Weights ───────────────────────────────
# These control how much each factor matters during UAV selection.
WEIGHT_BATTERY = 0.25
WEIGHT_DISTANCE = 0.30
WEIGHT_PRIORITY = 0.15
WEIGHT_CONNECTIVITY = 0.15
WEIGHT_ROLE = 0.15

# ── Thresholds ────────────────────────────────────────────
BATTERY_MIN_MISSION = 30          # % — refuse mission below this
BATTERY_MIN_RELAY = 20            # % — refuse relay duty below this
BATTERY_CRITICAL = 15             # % — UAV should RTL
LINK_QUALITY_MIN = 0.3            # below this, link is considered degraded
LINK_QUALITY_DEAD = 0.0           # link is fully broken
MAX_COMM_RANGE = 1000.0           # meters — beyond this, link is impossible
CONNECTIVITY_CHECK_INTERVAL = 2.0 # seconds between network health checks

# ── GCS Node ID ───────────────────────────────────────────
GCS_NODE_ID = "GCS"
