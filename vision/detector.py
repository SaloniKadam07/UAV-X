"""
detector.py
Person 3 - Vision + Priority Detection Lead

Stage 1 proof of concept: detect a predefined target/marker in an image
or video frame, estimate its position, and package the raw detection
geometry that priority.py and mission_event.py build on top of.

Design choice: ArUco fiducial markers are used as the "predefined target".
They give a stable ID, four corner points (for confidence/pose estimation)
and are trivial to print and test with on a laptop webcam - no e-Yantra
arena or custom marker rules required, per the Stage 1 scope.

If your actual target definition differs (color blobs, printed QR codes,
a trained detector, etc.), swap out `_raw_detect()` - everything
downstream (position estimate, confidence, output schema) stays the same.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import cv2
import numpy as np


ARUCO_DICT = cv2.aruco.DICT_4X4_50


@dataclass
class RawDetection:
    """Raw geometric result of finding one marker in a frame."""
    marker_id: int
    corners: np.ndarray          # shape (4, 2), pixel coords, clockwise from top-left
    frame_shape: Tuple[int, int]  # (height, width) of the source frame

    @property
    def center_px(self) -> Tuple[float, float]:
        cx = float(np.mean(self.corners[:, 0]))
        cy = float(np.mean(self.corners[:, 1]))
        return cx, cy

    @property
    def apparent_size_px(self) -> float:
        """Side length of the marker in pixels (avg of the 4 edges)."""
        c = self.corners
        edges = [np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]
        return float(np.mean(edges))


class TargetDetector:
    """
    Wraps OpenCV's ArUco detector and converts pixel detections into an
    estimated ground/world position using a simple pinhole-style scale
    factor. Swap `pixels_to_world()` for real camera calibration /
    homography when the simulation team can provide camera extrinsics.
    """

    def __init__(
        self,
        marker_dict=ARUCO_DICT,
        known_marker_size_m: float = 0.15,
        assumed_altitude_m: float = 10.0,
        horizontal_fov_deg: float = 60.0,
    ):
        """
        known_marker_size_m: real-world side length of the printed marker.
        assumed_altitude_m / horizontal_fov_deg: stand-in camera model used
            to convert pixel offsets into meters until real calibration
            data is wired in from the simulation/flight-control branch.
        """
        aruco_dict = cv2.aruco.getPredefinedDictionary(marker_dict)
        params = cv2.aruco.DetectorParameters()
        self._aruco = cv2.aruco.ArucoDetector(aruco_dict, params)
        self.known_marker_size_m = known_marker_size_m
        self.assumed_altitude_m = assumed_altitude_m
        self.horizontal_fov_deg = horizontal_fov_deg

    # ---------- Step 1-2: accept a frame, detect the marker ----------

    def _raw_detect(self, frame: np.ndarray) -> List[RawDetection]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if frame.ndim == 3 else frame
        corners, ids, _rejected = self._aruco.detectMarkers(gray)

        results = []
        if ids is None:
            return results

        h, w = gray.shape[:2]
        for marker_corners, marker_id in zip(corners, ids.flatten()):
            results.append(
                RawDetection(
                    marker_id=int(marker_id),
                    corners=marker_corners.reshape(4, 2),
                    frame_shape=(h, w),
                )
            )
        return results

    # ---------- Step 3: calculate/assign a target position ----------

    def pixels_to_world(self, det: RawDetection) -> Tuple[float, float, float]:
        """
        Very simple ground-plane projection:
        - pixel offset from image center -> angle (using assumed FOV)
        - angle * altitude -> ground-plane meters offset
        - z is reported as 0 (ground target). Replace with real
          altitude-above-target if/when available.

        This is intentionally simple for Stage 1; the important part for
        integration is the *shape* of the output (x, y, z in meters,
        target-frame or world-frame per docs/data_interfaces.md), not the
        precision of this placeholder projection.
        """
        h, w = det.frame_shape
        cx_px, cy_px = det.center_px

        # offset from principal point, normalized to [-1, 1]
        nx = (cx_px - w / 2) / (w / 2)
        ny = (cy_px - h / 2) / (h / 2)

        half_fov_rad = np.radians(self.horizontal_fov_deg / 2)
        # meters per normalized unit at the assumed altitude
        ground_half_width = self.assumed_altitude_m * np.tan(half_fov_rad)

        x_m = nx * ground_half_width
        y_m = -ny * ground_half_width  # image y grows downward; world y grows "forward"
        z_m = 0.0

        return round(float(x_m), 3), round(float(y_m), 3), round(float(z_m), 3)

    # ---------- confidence ----------

    def estimate_confidence(self, det: RawDetection) -> float:
        """
        Confidence heuristic for Stage 1 (no ML classifier yet):
        - larger, squarer marker in frame -> higher confidence
        - marker partially near frame edge -> lower confidence
        Clamped to [0, 1]. Replace with a real classifier score later
        if detection moves to a learned model.
        """
        h, w = det.frame_shape
        c = det.corners

        # squareness: ratio of shortest to longest edge (1.0 = perfect square)
        edges = [np.linalg.norm(c[i] - c[(i + 1) % 4]) for i in range(4)]
        squareness = min(edges) / max(edges) if max(edges) > 0 else 0.0

        # size score: bigger marker in frame -> more reliable
        size_score = min(det.apparent_size_px / (0.25 * min(h, w)), 1.0)

        # edge-proximity penalty
        margin = 0.03
        cx, cy = det.center_px
        near_edge = (
            cx < margin * w or cx > (1 - margin) * w or
            cy < margin * h or cy > (1 - margin) * h
        )
        edge_penalty = 0.15 if near_edge else 0.0

        confidence = 0.5 * squareness + 0.5 * size_score - edge_penalty
        return round(float(np.clip(confidence, 0.0, 1.0)), 3)

    # ---------- public entry point ----------

    def detect(self, frame: np.ndarray) -> List[dict]:
        """
        Accepts a single image/video frame (BGR numpy array, as read by
        cv2.imread / cv2.VideoCapture) and returns a list of detections:

        [
          {
            "target_id": "T3",
            "position": [x, y, z],   # meters, placeholder ground-plane projection
            "confidence": 0.87,
            "raw": <RawDetection>    # kept for debugging / priority.py use
          },
          ...
        ]
        """
        detections = []
        for det in self._raw_detect(frame):
            x, y, z = self.pixels_to_world(det)
            detections.append(
                {
                    "target_id": f"T{det.marker_id}",
                    "position": [x, y, z],
                    "confidence": self.estimate_confidence(det),
                    "raw": det,
                }
            )
        return detections


def draw_debug(frame: np.ndarray, detections: List[dict]) -> np.ndarray:
    """Optional helper: draw detected markers + labels for visual testing."""
    out = frame.copy()
    for d in detections:
        det: RawDetection = d["raw"]
        pts = det.corners.astype(int)
        cv2.polylines(out, [pts], True, (0, 255, 0), 2)
        cx, cy = map(int, det.center_px)
        label = f'{d["target_id"]} conf={d["confidence"]:.2f}'
        cv2.putText(out, label, (cx - 40, cy - 15), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 0), 2)
    return out
