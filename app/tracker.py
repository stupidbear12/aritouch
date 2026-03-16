import os
import cv2
import mediapipe as mp


class HandTracker:
    def __init__(
        self,
        model_path: str | None = None,
        max_num_hands: int = 1,
        min_det: float = 0.6,
    ):
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        base_dir = os.path.dirname(os.path.abspath(__file__))
        if model_path is None:
            model_path = os.path.join(base_dir, "hand_landmarker.task")

        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=max_num_hands,
            min_hand_detection_confidence=min_det,
        )
        self._vision = vision
        self.detector = vision.HandLandmarker.create_from_options(options)

    def process(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb,
        )
        result = self.detector.detect(image)

        if not result.hand_landmarks:
            return None

        lm = result.hand_landmarks[0]
        index_tip = lm[8]
        thumb_tip = lm[4]
        return {
            "index_tip": (index_tip.x, index_tip.y, index_tip.z),
            "thumb_tip": (thumb_tip.x, thumb_tip.y, thumb_tip.z),
            "all": lm,
        }

    def close(self):
        self.detector = None
