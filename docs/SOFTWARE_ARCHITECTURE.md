# UAV-X Software Architecture

## 1. System Overview

UAV-X is designed as a modular multi-UAV disaster-response system.

The system is divided into four main modules:

- Simulation and Flight Control
- Swarm and Mission Management
- Communication and Relay Management
- Vision and Priority Detection

These modules exchange information through shared data formats so that each part can be developed and tested independently before final integration.

The Ground Control Station (GCS) acts as the mission-level reference point for monitoring swarm connectivity and mission progress.

## 2. High-Level Data Flow

The overall UAV-X data flow is:

```text
Vision / Mission Input
        ↓
Mission Manager
        ↓
Task Allocation
        ↓
Simulation / UAV Control
        ↓
UAV State Updates
        ↓
Communication Network Monitor
        ↓
Relay / Recovery Logic
        ↓
Updated Swarm Roles and Mission State
        ↓
Ground Control Station

## 3. Module Responsibilities

### 3.1 Simulation and Flight Control

Responsible for:

- Spawning and managing multiple UAVs
- UAV movement and waypoint execution
- Hover and position control
- Battery and UAV status updates
- Return-to-home behaviour
- Providing current UAV state to other modules

### 3.2 Swarm and Mission Management

Responsible for:

- Managing mission points
- Assigning missions to available UAVs
- Considering UAV availability and battery state
- Updating UAV roles
- Handling mission reassignment when required

### 3.3 Communication and Relay Management

Responsible for:

- Building the communication network graph
- Checking UAV connectivity to the Ground Control Station
- Detecting communication failures
- Identifying disconnected UAVs
- Selecting relay candidates
- Triggering network recovery logic

### 3.4 Vision and Priority Detection

Responsible for:

- Processing camera images or video frames
- Detecting targets or survivor indicators
- Estimating target locations
- Assigning mission priority
- Sending detected events to the mission-management module

## 4. Shared Data Interfaces

All modules communicate using common data structures so that independently developed components remain compatible.

### 4.1 UAV State

Each UAV provides:

- UAV ID
- Current position
- Battery level
- Current role
- Current status

Example:

```json
{
  "id": "UAV1",
  "position": [0, 0, 0],
  "battery": 65,
  "role": "SURVEY",
  "status": "ACTIVE"
}

### 4.2 Mission Point

Each mission location is represented using a common mission-point structure.

It contains:

- `id` — unique mission-point identifier
- `position` — mission location in `[x, y, z]` format
- `priority` — importance level of the mission
- `status` — current state of the mission

Example:

```json
{
  "id": "P1",
  "position": [10, 5, 0],
  "priority": "NORMAL",
  "status": "PENDING"
}

### 4.3 Communication Link

Communication between the Ground Control Station and UAVs is represented using a communication-link structure.

It contains:

- `from` — source node
- `to` — destination node
- `connected` — whether the communication link is currently active
- `quality` — current quality of the communication link

Example between two UAVs:

```json
{
  "from": "UAV1",
  "to": "UAV2",
  "connected": true,
  "quality": 0.9
}

## 5. Failure and Recovery Flow

UAV-X is designed to respond to communication failures and UAV failures during a mission.

The recovery sequence is:

```text
Failure Detected
      ↓
Update UAV or Link Status
      ↓
Rebuild Communication Graph
      ↓
Check Connectivity to GCS
      ↓
Identify Disconnected UAVs
      ↓
Select Relay Candidate
      ↓
Update UAV Role
      ↓
Trigger Recovery Action
      ↓
Continue Mission

## 6. Integration and Testing

The `integration` branch is used to combine and test independently developed UAV-X modules before stable changes are merged into `main`.

The integration process follows this sequence:

```text
Simulation Branch
Swarm-Communication Branch
Vision Branch
        ↓
Integration Branch
        ↓
Combined Testing
        ↓
Stable Main Branch

## 7. Overall Software Architecture

The UAV-X software system follows a modular architecture in which perception, mission planning, swarm coordination, communication monitoring, and UAV control operate as connected components.

```text
                +----------------------+
                |   Vision / Mission   |
                |        Input         |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |   Mission Manager    |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |    Task Allocator    |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Swarm / Role Manager |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Simulation / Flight  |
                |       Control        |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |      UAV States      |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Communication Graph  |
                |      Monitoring      |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Relay / Failure      |
                | Recovery Logic       |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Ground Control       |
                | Station / Mission    |
                |      Status          |
                +----------------------+