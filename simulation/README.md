# Simulation Module

This folder will contain the UAV simulation-related files.

## Responsibilities

The simulation module should:

- Spawn multiple UAVs
- Maintain UAV positions
- Move UAVs toward assigned target coordinates
- Provide battery and status information
- Support return-to-home behavior
- Expose UAV state information to the swarm module

## Expected Input

- UAV ID
- Target position
- Assigned role
- Mission ID
- Return-to-home command

## Expected Output

- UAV ID
- Current position
- Battery level
- UAV status

## Initial Goal

Create a basic multi-UAV simulation where each UAV can:

1. Spawn
2. Take off
3. Move to a given coordinate
4. Hold position
5. Return home