# UAV-X Data Interfaces

This document defines the common data formats used by all project modules.

## UAV State

Each UAV is represented using:

- id
- position
- battery
- role
- status

Example:

```json
{
  "id": "UAV1",
  "position": [0, 0, 0],
  "battery": 100,
  "role": "SURVEY",
  "status": "ACTIVE"
}

## Mission Point

Each mission point is represented using:

- id
- position
- priority
- status

Example:

```json
{
  "id": "P1",
  "position": [10, 5, 0],
  "priority": "HIGH",
  "status": "PENDING"
}

## Communication Link

Each communication link is represented using:

- from
- to
- connected
- quality

Example:

```json
{
  "from": "UAV1",
  "to": "UAV2",
  "connected": true,
  "quality": 0.9
}

## Purpose

The simulation, swarm logic, communication system, and vision module should all use these shared data formats so the modules can be integrated later without changing their basic interfaces.