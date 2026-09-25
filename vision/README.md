# Vision Module

This folder will contain the computer vision and priority-detection components.

## Responsibilities

The vision module should:

- Process camera images or video frames
- Detect disaster targets or survivor markers
- Estimate target location
- Assign a priority level
- Generate a mission event for the swarm module

## Expected Input

- Camera image or video frame

## Expected Output

- Target ID
- Target position
- Priority
- Confidence

Example:

```json
{
  "target_id": "T1",
  "position": [15, 20, 0],
  "priority": "HIGH",
  "confidence": 0.94
}