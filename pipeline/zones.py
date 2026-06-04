"""Zone manager: load polygon zones from YAML and do point-in-polygon checks."""
from __future__ import annotations

import yaml
from typing import Any, Dict, List, Optional, Tuple


def _point_in_polygon(x: float, y: float, polygon: List[Tuple[float, float]]) -> bool:
    # Ray casting algorithm for point-in-polygon
    inside = False
    n = len(polygon)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        intersect = ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside


class Zone:
    def __init__(self, name: str, ztype: str, polygon: List[Tuple[float, float]]):
        self.name = name
        self.type = ztype
        self.polygon = polygon

    def contains(self, point: Tuple[float, float]) -> bool:
        x, y = point
        return _point_in_polygon(x, y, self.polygon)


class ZoneManager:
    def __init__(self, path: str = "config/store_zones.yaml"):
        self.path = path
        self.camera_zones: Dict[str, List[Zone]] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fp:
                data = yaml.safe_load(fp) or {}
        except FileNotFoundError:
            data = {}

        for camera_id, zones in data.items():
            self.camera_zones[camera_id] = []
            for z in zones:
                poly = [(float(p[0]), float(p[1])) for p in z.get("polygon", [])]
                self.camera_zones[camera_id].append(Zone(z.get("name", "unknown"), z.get("type", "unknown"), poly))

    def get_zone_for_point(self, camera_id: str, point: Tuple[float, float]) -> Optional[Zone]:
        if camera_id not in self.camera_zones:
            return None
        for zone in self.camera_zones[camera_id]:
            if zone.contains(point):
                return zone
        return None


if __name__ == "__main__":
    zm = ZoneManager()
    print({k: [z.name for z in v] for k, v in zm.camera_zones.items()})
