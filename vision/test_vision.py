"""
test_vision.py
Person 3 - Vision + Priority Detection Lead

Independent test harness - no external sample images needed. It generates
its own synthetic marker images (ArUco markers T1/T2/T3, printed onto a
blank background at known positions), runs them through the full
pipeline, and checks that output matches the required schema.

Run:
    cd vision
    python test_vision.py

This also writes sample_data/*.jpg and sample_data/*_debug.jpg so you can
visually confirm detections, and works the same way with a real photo of
a printed marker or a video file - see test_with_video() below.
"""

import os
import sys
import json
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

from detector import TargetDetector, draw_debug, ARUCO_DICT
from mission_event import build_detection_result, to_mission_point
from interface import get_detection_result, get_mission_points

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_data")


def make_sample_image(marker_id: int, marker_px: int = 200,
                       canvas_size: int = 640, offset=(0, 0)) -> np.ndarray:
    """Generates a synthetic test frame with one ArUco marker in it."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_px)
    marker_bgr = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2BGR)

    canvas = np.full((canvas_size, canvas_size, 3), 200, dtype=np.uint8)
    cx = canvas_size // 2 - marker_px // 2 + offset[0]
    cy = canvas_size // 2 - marker_px // 2 + offset[1]
    canvas[cy:cy + marker_px, cx:cx + marker_px] = marker_bgr
    return canvas


def test_single_frame_detection():
    print("\n--- Test 1: single-frame detection ---")
    frame = make_sample_image(marker_id=1)
    detector = TargetDetector()
    detections = detector.detect(frame)

    assert len(detections) == 1, f"Expected 1 detection, got {len(detections)}"
    d = detections[0]
    assert d["target_id"] == "T1"
    assert 0.0 <= d["confidence"] <= 1.0
    assert len(d["position"]) == 3
    print(f"  OK - detected {d['target_id']} at {d['position']} "
          f"(confidence={d['confidence']})")


def test_output_schema():
    print("\n--- Test 2: output schema matches spec ---")
    frame = make_sample_image(marker_id=2)
    detector = TargetDetector()
    raw = detector.detect(frame)[0]
    result = build_detection_result(raw)

    required_keys = {"target_id", "position", "priority", "confidence"}
    assert set(result.keys()) == required_keys, result.keys()
    assert result["priority"] in ("CRITICAL", "HIGH", "STABLE")
    print(f"  OK - {json.dumps(result)}")


def test_mission_point_conversion():
    print("\n--- Test 3: mission point conversion (docs/data_interfaces.md) ---")
    frame = make_sample_image(marker_id=1)
    detector = TargetDetector()
    raw = detector.detect(frame)[0]
    result = build_detection_result(raw)
    point = to_mission_point(result)

    assert set(point.keys()) == {"id", "position", "priority", "status"}, point.keys()
    assert point["id"] == "T1"
    assert point["status"] == "PENDING"
    print(f"  OK - {json.dumps(point, indent=2)}")


def test_multiple_targets_in_one_frame():
    print("\n--- Test 4: multiple targets in one frame ---")
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    canvas = np.full((640, 640, 3), 200, dtype=np.uint8)
    for marker_id, (x, y) in [(1, (50, 50)), (2, (380, 50)), (3, (200, 380))]:
        m = cv2.aruco.generateImageMarker(aruco_dict, marker_id, 150)
        m_bgr = cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)
        canvas[y:y + 150, x:x + 150] = m_bgr

    detector = TargetDetector()
    detections = detector.detect(canvas)
    ids = sorted(d["target_id"] for d in detections)
    assert ids == ["T1", "T2", "T3"], ids
    print(f"  OK - detected {ids}")

    debug_img = draw_debug(canvas, detections)
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    cv2.imwrite(os.path.join(SAMPLE_DIR, "multi_target_debug.jpg"), debug_img)
    print(f"  wrote debug image to {SAMPLE_DIR}/multi_target_debug.jpg")


def test_no_target_present():
    print("\n--- Test 5: empty frame (no target) ---")
    blank = np.full((480, 640, 3), 220, dtype=np.uint8)
    detector = TargetDetector()
    detections = detector.detect(blank)
    assert detections == []
    print("  OK - empty list returned, no false positives")


def test_public_interface():
    print("\n--- Test 6: interface.py entry point (what Person 4 will call) ---")
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    path = os.path.join(SAMPLE_DIR, "test_frame.jpg")
    cv2.imwrite(path, make_sample_image(marker_id=1))

    results = get_detection_result(path)
    points = get_mission_points(path)
    assert len(results) == 1 and results[0]["target_id"] == "T1"
    assert len(points) == 1
    print(f"  OK - get_detection_result(path) -> {json.dumps(results)}")
    print(f"  OK - get_mission_points(path) -> {json.dumps(points)}")


def test_with_video(video_path: str):
    """
    Optional: run detection across every frame of a video file to sanity
    check performance/consistency over time. Not run by default since it
    needs a real video file - call manually:
        python -c "from test_vision import test_with_video; test_with_video('my_clip.mp4')"
    """
    detector = TargetDetector()
    cap = cv2.VideoCapture(video_path)
    frame_count, detection_count = 0, 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_count += 1
        detection_count += len(detector.detect(frame))
    cap.release()
    print(f"Processed {frame_count} frames, {detection_count} total detections.")


if __name__ == "__main__":
    test_single_frame_detection()
    test_output_schema()
    test_mission_point_conversion()
    test_multiple_targets_in_one_frame()
    test_no_target_present()
    test_public_interface()
    print("\nAll Stage 1 vision tests passed.\n")
