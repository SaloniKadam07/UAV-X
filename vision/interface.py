"""
interface.py
Person 3 - Vision + Priority Detection Lead

This is the single file Person 4 (integration) needs to import.
Everything else (detector.py, priority.py, mission_event.py) is internal
plumbing they don't need to touch.

Usage:
    from interface import get_detection_result, get_mission_points

    results = get_detection_result("sample_data/test_frame.jpg")
    # -> [{"target_id": "T1", "position": [...], "priority": "HIGH", "confidence": 0.92}, ...]
    # This is the exact Vision Module output contract from docs/module_interfaces.md.

    points = get_mission_points("sample_data/test_frame.jpg")
    # -> [{"id": "T1", "position": [...], "priority": "HIGH", "status": "PENDING"}, ...]
    # This is the shared Mission Point format from docs/data_interfaces.md,
    # ready to append to the swarm module's mission point list.

Both functions also accept an already-loaded frame (numpy array) instead
of a file path, e.g. a frame pulled from cv2.VideoCapture in a live loop.
"""

from typing import List, Union
import cv2
import numpy as np

from detector import TargetDetector
from mission_event import build_detection_result, to_mission_point

_detector = TargetDetector()


def _load_frame(image_or_path: Union[str, np.ndarray]) -> np.ndarray:
    if isinstance(image_or_path, np.ndarray):
        return image_or_path
    frame = cv2.imread(image_or_path)
    if frame is None:
        raise FileNotFoundError(f"Could not read image: {image_or_path}")
    return frame


def get_detection_result(image_or_path: Union[str, np.ndarray]) -> List[dict]:
    """
    Accepts an image file path OR an already-loaded BGR frame.
    Returns a list of detections in the Stage 1 required schema:
        [{"target_id", "position", "priority", "confidence"}, ...]
    Empty list if nothing detected.
    """
    frame = _load_frame(image_or_path)
    raw_detections = _detector.detect(frame)
    return [build_detection_result(d) for d in raw_detections]


def get_mission_points(image_or_path: Union[str, np.ndarray]) -> List[dict]:
    """
    Same as get_detection_result(), but reshapes each result into the
    shared Mission Point format (docs/data_interfaces.md), ready for the
    swarm module to append to its mission point list.
    """
    results = get_detection_result(image_or_path)
    return [to_mission_point(r) for r in results]


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python interface.py <path_to_image>")
        sys.exit(1)

    results = get_detection_result(sys.argv[1])
    print(json.dumps(results, indent=2))
