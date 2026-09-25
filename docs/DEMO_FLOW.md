# UAV-X Stage 1 Demonstration Flow

## 1. Demo Objective

The Stage 1 demonstration should show that the UAV-X proof-of-concept can perform a basic disaster-response mission using multiple UAVs while maintaining communication with the Ground Control Station.

The demonstration should focus on the core capabilities already implemented or being integrated:

- Multi-UAV mission execution
- Mission assignment
- Communication connectivity monitoring
- Communication failure detection
- Automatic relay selection
- Basic recovery behaviour
- Mission continuation after failure

The demo should remain simple, clear, and reproducible.

The objective is not to show a fully finished system, but to demonstrate that the proposed UAV-X architecture and communication-aware swarm logic are technically feasible.

## 2. Demo Sequence

The demonstration should follow this order:

1. Start the UAV-X simulation environment.

2. Initialize the UAV swarm and Ground Control Station.

3. Display the initial UAV states, including:
   - UAV ID
   - Position
   - Battery
   - Role
   - Status

4. Load the mission points.

5. Assign a mission point to an available UAV.

6. Show that all active UAVs initially have communication connectivity to the Ground Control Station.

7. Trigger a communication-link failure.

8. Detect which UAVs have become disconnected from the Ground Control Station.

9. Select a suitable UAV as the new relay candidate.

10. Change the selected UAV role to `RELAY`.

11. Trigger the recovery process.

12. Show that the mission continues after the failure.

13. Display the final UAV states and mission status.

14. Save or display logs that show:
   - Mission assignment
   - Failure event
   - Disconnected UAVs
   - Relay selection
   - Recovery action
   - Final mission state

## 3. Video Capture Checklist

The demonstration video should clearly capture the following:

- Project/repository name
- Simulation starting successfully
- UAV swarm initialization
- Mission points being loaded
- Mission assignment to a UAV
- Initial communication connectivity
- Triggered communication failure
- Detection of disconnected UAVs
- Relay UAV selection
- Relay role reassignment
- Recovery action
- Mission continuation after the failure
- Final UAV and mission states
- Relevant terminal output or logs

The video should avoid unnecessary setup delays.

Where possible, terminal windows and simulation views should be arranged so that the viewer can easily understand what is happening.

Short text labels or captions can be added during editing to explain important events such as:

- Mission Assigned
- Link Failure
- UAVs Disconnected
- Relay Selected
- Recovery Triggered
- Mission Continued

## 4. Expected Demo Output

At the end of the demonstration, the system should clearly show that:

- A mission point was assigned to an available UAV
- Initial communication connectivity existed between the UAV swarm and the Ground Control Station
- A communication failure was introduced
- The affected UAVs were detected as disconnected
- A suitable UAV was selected as a relay candidate
- The selected UAV role changed to `RELAY`
- The recovery logic was triggered
- The mission remained active after the failure
- Final UAV states were displayed
- Final mission status was displayed

At the current proof-of-concept stage, logical relay recovery is sufficient for the software demo.

Physical UAV repositioning and simulator-based restoration of the communication path may be shown later if completed during integration.



