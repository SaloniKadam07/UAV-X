# UAV-X Installation Guide

This document explains how to set up and run the UAV-X project.

## 1. Clone the Repository

```bash
git clone https://github.com/SaloniKadam07/UAV-X.git
cd UAV-X

## 2. Branches

Main development branches:

- `main` — stable shared version
- `integration` — combined testing branch
- `simulation` — simulator and UAV movement
- `swarm-communication` — swarm, networking and recovery logic
- `vision` — computer vision and priority detection

## 3. Python Requirements

Check Python:

```bash
python --version

Install project requirements:

```bash
pip install -r requirements.txt

## 4. Run Current Base Tests

Run these commands from the project root:

```bash
python scripts/show_state.py
python scripts/test_allocator.py
python scripts/test_network.py
python scripts/test_relay.py
python scripts/test_recovery.py
python scripts/test_mission_manager.py
python scripts/test_failure_manager.py
python scripts/integration_demo.py

## 5. Simulation Setup

Simulation setup will be handled by the simulation lead.

Expected environment:

- Ubuntu
- ROS 2
- UAV simulation framework
- Required simulator dependencies

Detailed installation commands will be added after the simulation environment is finalized.

## 6. Vision Setup

The vision module will be developed and tested separately before integration.

Expected tools:

- Python
- OpenCV
- NumPy

The vision module should provide outputs in the shared UAV-X format, including:

- Target ID
- Target position
- Priority
- Confidence

Detailed installation commands will be added after the vision module is finalized.

## 7. Integration Flow

Each module should be tested independently before being integrated.

Recommended workflow:

```text
Feature Branch
    ↓
Integration Branch
    ↓
Testing
    ↓
Main Branch

## 8. Notes

Do not commit generated ROS folders such as:

```text
build/
install/
log/