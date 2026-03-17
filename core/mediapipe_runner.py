from dataclasses import dataclass, field

import cv2
import numpy as np
import mediapipe as mp


@dataclass
class MPResult:
    w: int
    h: int
    face_landmarks: object = None
    hand_landmarks: object = None
    eye_mid_z: float = 0.0
    eye_mid_xy: np.ndarray = field(default_factory=lambda: np.zeros(2))
    idx_tip_z: float = 0.0


class MPRunner:

    def __init__(
        self,
        det_face: float = 0.5,
        det_hand: float = 0.7,
        track_hand: float = 0.6,
    ):
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=det_face,
            min_tracking_confidence=det_face,
        )
        self._hands = mp.solutions.hands.Hands(
            max_num_hands=1,
            min_detection_confidence=det_hand,
            min_tracking_confidence=track_hand,
        )
        self._mp_hands = mp.solutions.hands
        self._mp_draw = mp.solutions.drawing_utils
        self._mp_styles = mp.solutions.drawing_styles

    def process(self, rgb_frame: np.ndarray) -> MPResult:
        h, w = rgb_frame.shape[:2]
        rgb_frame.flags.writeable = False

        face_result = self._face_mesh.process(rgb_frame)
        hand_result = self._hands.process(rgb_frame)

        rgb_frame.flags.writeable = True

        face_lm = None
        if face_result.multi_face_landmarks:
            face_lm = face_result.multi_face_landmarks[0]

        hand_lm = None
        if hand_result.multi_hand_landmarks:
            hand_lm = hand_result.multi_hand_landmarks[0]

        return MPResult(
            w=w,
            h=h,
            face_landmarks=face_lm,
            hand_landmarks=hand_lm,
        )

    def draw(self, frame: np.ndarray, result: MPResult) -> np.ndarray:
        if result.hand_landmarks is not None:
            self._mp_draw.draw_landmarks(
                frame,
                result.hand_landmarks,
                self._mp_hands.HAND_CONNECTIONS,
                self._mp_styles.get_default_hand_landmarks_style(),
                self._mp_styles.get_default_hand_connections_style(),
            )

        if result.face_landmarks is not None:
            from utils.constants import R_EYE_OUTER, R_EYE_INNER, L_EYE_OUTER, L_EYE_INNER
            for idx in (R_EYE_OUTER, R_EYE_INNER, L_EYE_OUTER, L_EYE_INNER):
                lm = result.face_landmarks.landmark[idx]
                cx = int(lm.x * result.w)
                cy = int(lm.y * result.h)
                cv2.circle(frame, (cx, cy), 3, (0, 255, 255), -1)

        return frame

    def close(self):
        self._face_mesh.close()
        self._hands.close()
