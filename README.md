# UAV-X

Vision-Guided, Priority-Aware and Communication-Resilient BVLOS UAV Swarm for Disaster Response.

## Project Objective

Develop an autonomous UAV swarm capable of:

- Surveying disaster locations
- Maintaining communication with the Ground Control Station
- Dynamically assigning relay UAVs
- Recovering from UAV and communication failures
- Handling high-priority disaster events
- Managing battery and safety constraints

## Current Project Structure

- `simulation/` — UAV simulation and movement
- `swarm/` — mission management, task allocation, roles and failure handling
- `communication/` — network graph, connectivity, relay selection and recovery
- `vision/` — target detection, localization and priority generation
- `config/` — UAV, mission, communication and shared settings
- `scenarios/` — test mission scenarios
- `scripts/` — test and integration scripts
- `docs/` — interface and module documentation
- `tests/` — future automated tests
- `logs/` — generated mission and communication logs

## Shared Base Completed

The current base includes:

- UAV state configuration
- Mission point configuration
- Communication link configuration
- Shared UAV and mission data models
- Basic task allocator
- Mission manager
- Multi-hop connectivity checker
- Relay candidate selector
- Automatic relay role recovery
- UAV and link failure manager
- Shared role and status constants
- Shared system settings
- Normal and failure scenario files
- Data interface documentation
- Module interface documentation
- Basic integration demo

## Current Branches

- `main` — stable shared project base
- `simulation` — simulation and UAV movement development
- `swarm-communication` — swarm, communication and recovery logic
- `vision` — computer vision and priority detection

## Basic Tests

Run the current base tests from the project root:

```bash
python scripts/show_state.py
python scripts/test_allocator.py
python scripts/test_network.py
python scripts/test_relay.py
python scripts/test_recovery.py
python scripts/test_mission_manager.py
python scripts/test_failure_manager.py
python scripts/integration_demo.py