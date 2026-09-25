from dataclasses import dataclass
from typing import List


@dataclass
class UAV:
    id: str
    position: List[float]
    battery: float
    role: str
    status: str


@dataclass
class MissionPoint:
    id: str
    position: List[float]
    priority: str
    status: str