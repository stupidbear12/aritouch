# tracker.py
import cv2, mediapipe as mp

class HandTracker:
    def __init__(self, model_complexity=1, max_num_hands=1, min_det=0.6, min_track=0.6):
        self.hands = mp.solutions.hands.Hands(
            model_complexity=model_complexity,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_det,
            min_tracking_confidence=min_track
        )

    def process(self, bgr):
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        res = self.hands.process(rgb)
        if not res.multi_hand_landmarks:
            return None
        lm = res.multi_hand_landmarks[0].landmark
        return {
            "index_tip": (lm[8].x, lm[8].y, lm[8].z),
            "thumb_tip": (lm[4].x, lm[4].y, lm[4].z),
            "all": lm
        }

    def close(self):
        try:
            self.hands.close()
        except Exception:
            pass
