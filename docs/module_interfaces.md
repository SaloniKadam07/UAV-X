# UAV-X Module Interfaces

This document defines the basic inputs and outputs expected from each project module.

## 1. Simulation Module

### Input
- UAV target position
- UAV role
- Mission assignment
- Return-to-home command

### Output
- UAV ID
- Current position
- Battery level
- UAV status

Example output:

```json
{
  "id": "UAV1",
  "position": [10, 5, 3],
  "battery": 82,
  "status": "ACTIVE"
}

## 2. Swarm Module

### Input
- UAV states
- Mission points
- Priority level
- Communication status

### Output
- Selected UAV
- Assigned mission
- Updated UAV role

Example output:

```json
{
  "uav_id": "UAV3",
  "mission_id": "P1",
  "role": "SURVEY"
}

## 3. Communication Module

### Input
- UAV positions
- Communication links
- Link quality
- UAV failure status

### Output
- GCS connectivity status
- Disconnected UAV list
- Relay candidate
- Recovery action

Example output:

```json
{
  "disconnected_uavs": ["UAV3"],
  "relay_candidate": "UAV1",
  "recovery_required": true
}

## 4. Vision Module

### Input
- Camera image or video frame

### Output
- Detected target
- Target position
- Priority
- Confidence

Example output:

```json
{
  "target_id": "T1",
  "position": [15, 20, 0],
  "priority": "HIGH",
  "confidence": 0.94
}
