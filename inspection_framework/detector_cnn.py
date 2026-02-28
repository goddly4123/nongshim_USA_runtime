"""
detector_cnn.py — CNN Image Classifier Plugin
===============================================

[Role]
    Classifies the entire image into categories (e.g., ok / ng).
    No bounding boxes — uses full image as the detection region.

[Install]
    pip install torch torchvision

[detector_config keys]
    input_size   : list  = [224, 224]     — Model input dimensions [W, H]
    class_names  : list  = ["ok", "ng"]   — Index-to-name mapping

[Usage]
    Automatically loaded by create_detector("cnn", ...).
"""

import cv2
import numpy as np
from typing import Dict, List, Optional

from detector import BaseDetector, DetectionResult, register_detector


@register_detector("cnn")
class CnnClassifier(BaseDetector):
    """CNN whole-image classifier."""

    def __init__(
        self,
        model_path: str,
        class_thresholds: Optional[Dict[str, float]] = None,
        device: str = 'cuda',
        detector_config: Optional[Dict] = None,
    ):
        import torch

        dc = detector_config or {}
        self.class_thresholds = class_thresholds
        self.class_names = dc.get("class_names", ["ok", "ng"])
        self.input_size = tuple(dc.get("input_size", [224, 224]))

        print(f"[Detector:CNN] Loading model: {model_path}")
        self._device = torch.device(device if torch.cuda.is_available() else "cpu")
        self._model = torch.load(model_path, map_location=self._device, weights_only=False)
        self._model.eval()
        print(f"[Detector:CNN] Ready. Classes: {self.class_names}, Device: {self._device}")

    def detect(self, image_bgr: np.ndarray) -> List[DetectionResult]:
        if image_bgr is None:
            return []

        import torch

        h, w = image_bgr.shape[:2]

        # Preprocess: resize → RGB → tensor → normalize
        resized = cv2.resize(image_bgr, self.input_size)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().unsqueeze(0) / 255.0
        tensor = tensor.to(self._device)

        # Inference
        with torch.no_grad():
            output = self._model(tensor)
            probs = torch.softmax(output, dim=1)[0]
            confidence = float(probs.max())
            class_idx = int(probs.argmax())

        label = (
            self.class_names[class_idx]
            if class_idx < len(self.class_names)
            else f"class_{class_idx}"
        )

        # Threshold logic
        # class_thresholds에 등록된 클래스만 불량으로 판정 (미등록 클래스는 정상)
        if self.class_thresholds is not None:
            if label not in self.class_thresholds:
                # 명시적 threshold 목록에 없는 클래스는 항상 정상
                is_defect = False
                threshold = 0.0
            else:
                threshold = self.class_thresholds[label]
                is_defect = confidence >= threshold
        else:
            # class_thresholds=None: 모든 클래스를 0.5 기준으로 판정 (기존 동작 유지)
            threshold = 0.5
            is_defect = confidence >= threshold

        return [DetectionResult(
            label=label,
            confidence=confidence,
            bbox_xyxy=[0, 0, w, h],  # full image as bbox
            is_defect=is_defect,
            class_threshold=threshold,
        )]

    def draw(
        self,
        image_bgr: np.ndarray,
        detections: List[DetectionResult],
    ) -> np.ndarray:
        """Overlay classification result on image (no bounding box)."""
        annotated = image_bgr.copy()

        if not detections:
            return annotated

        det = detections[0]
        color = (0, 0, 255) if det.is_defect else (0, 200, 0)
        text = f"{det.label} {det.confidence:.2f}"

        # Large text at top-left corner
        cv2.putText(
            annotated, text,
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3,
        )

        # Thin border around image to indicate status
        h, w = annotated.shape[:2]
        cv2.rectangle(annotated, (0, 0), (w - 1, h - 1), color, 3)

        return annotated

    def set_class_thresholds(self, class_thresholds: Optional[Dict[str, float]]) -> None:
        """
        Update class thresholds at runtime.

        Parameters
        ----------
        class_thresholds : dict or None
            New class thresholds (e.g., {"ok": 0.7, "ng": 0.5})
        """
        self.class_thresholds = class_thresholds
        if class_thresholds:
            print(f"[Detector:CNN] Updated class thresholds: {class_thresholds}")
        else:
            print(f"[Detector:CNN] Cleared class thresholds")
