"""Detection wrapper using YOLOv8 (fallback to a no-op detector).

Provides Detector.detect(frame) -> list[dict] with keys:
- bbox: (x1,y1,x2,y2)
- confidence: float
- class_id: int
- class_name: str
"""
from __future__ import annotations

from typing import List, Dict, Tuple
import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except Exception:
    YOLO_AVAILABLE = False


class Detector:
    def __init__(self, model_name: str = "yolov8n.pt", device: str = "cpu"):
        self.model = None
        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(model_name)
                self.model.to(device)
            except Exception:
                self.model = None

    def detect(self, frame: np.ndarray) -> List[Dict]:
        if self.model is None:
            return []

        results = self.model(frame)[0]
        detections: List[Dict] = []
        boxes = getattr(results, "boxes", None)
        if boxes is None:
            return []

        xyxy = boxes.xyxy.cpu().numpy() if hasattr(boxes.xyxy, "cpu") else boxes.xyxy.numpy()
        confs = boxes.conf.cpu().numpy() if hasattr(boxes.conf, "cpu") else boxes.conf.numpy()
        cls = boxes.cls.cpu().numpy() if hasattr(boxes.cls, "cpu") else boxes.cls.numpy()

        for box, conf, c in zip(xyxy, confs, cls):
            x1, y1, x2, y2 = [float(v) for v in box]
            detections.append({
                "bbox": (x1, y1, x2, y2),
                "confidence": float(conf),
                "class_id": int(c),
                "class_name": str(int(c)),
            })
        return detections
