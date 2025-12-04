"""
Gesture Detection Module
MediaPipe 기반 얼굴 및 손 검출
"""

import cv2
import numpy as np
import mediapipe as mp
import config


class FaceDetector:
    """
    MediaPipe FaceMesh 기반 얼굴 검출
    
    양안 중점의 3D 좌표 (X, Y, Z) 계산
    """
    
    def __init__(self, 
                 detection_confidence=config.FACE_DETECTION_CONFIDENCE,
                 tracking_confidence=config.FACE_TRACKING_CONFIDENCE):
        """
        Args:
            detection_confidence: 검출 신뢰도 임계값
            tracking_confidence: 추적 신뢰도 임계값
        """
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=config.MAX_NUM_FACES,
            refine_landmarks=False,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
    
    def detect(self, rgb_image):
        """
        얼굴 검출 및 처리
        
        Args:
            rgb_image: RGB 이미지 (numpy array)
        
        Returns:
            얼굴 랜드마크 또는 None
        """
        results = self.face_mesh.process(rgb_image)
        
        if results.multi_face_landmarks:
            return results.multi_face_landmarks[0]
        return None
    
    def get_eye_midpoint(self, face_landmarks, image_width, image_height):
        """
        양안 중점의 3D 좌표 계산
        
        Args:
            face_landmarks: MediaPipe 얼굴 랜드마크
            image_width: 이미지 너비
            image_height: 이미지 높이
        
        Returns:
            (right_eye_center_xy, left_eye_center_xy, eye_midpoint_xy, eye_midpoint_z)
            - *_xy: (x, y) 좌표 (numpy array)
            - eye_midpoint_z: Z 좌표 (float)
        """
        lm = face_landmarks.landmark
        
        def get_point_3d(index):
            """랜드마크 인덱스 → 3D 좌표"""
            point_xy = np.array([lm[index].x * image_width, 
                                lm[index].y * image_height], dtype=np.float32)
            point_z = float(lm[index].z) * image_width
            return (point_xy, point_z)
        
        # 오른쪽 눈 (사용자 기준 왼쪽)
        r_outer_xy, r_outer_z = get_point_3d(config.R_EYE_OUTER)
        r_inner_xy, r_inner_z = get_point_3d(config.R_EYE_INNER)
        r_center_xy = 0.5 * (r_outer_xy + r_inner_xy)
        r_center_z = 0.5 * (r_outer_z + r_inner_z)
        
        # 왼쪽 눈 (사용자 기준 오른쪽)
        l_outer_xy, l_outer_z = get_point_3d(config.L_EYE_OUTER)
        l_inner_xy, l_inner_z = get_point_3d(config.L_EYE_INNER)
        l_center_xy = 0.5 * (l_outer_xy + l_inner_xy)
        l_center_z = 0.5 * (l_outer_z + l_inner_z)
        
        # 양안 중점
        eye_midpoint_xy = 0.5 * (r_center_xy + l_center_xy)
        eye_midpoint_z = 0.5 * (r_center_z + l_center_z)
        
        return (r_center_xy, l_center_xy, eye_midpoint_xy, eye_midpoint_z)
    
    def close(self):
        """리소스 해제"""
        self.face_mesh.close()


class HandDetector:
    """
    MediaPipe Hands 기반 손 검출
    
    손 랜드마크 (21개 점) 검출 및 3D 좌표 추출
    """
    
    def __init__(self,
                 detection_confidence=config.HAND_DETECTION_CONFIDENCE,
                 tracking_confidence=config.HAND_TRACKING_CONFIDENCE):
        """
        Args:
            detection_confidence: 검출 신뢰도 임계값
            tracking_confidence: 추적 신뢰도 임계값
        """
        self.hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_NUM_HANDS,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
        self.drawer = mp.solutions.drawing_utils
    
    def detect(self, rgb_image):
        """
        손 검출 및 처리

        Args:
            rgb_image: RGB 이미지 (numpy array)

        Returns:
            손 랜드마크 리스트 또는 None
        """
        results = self.hands.process(rgb_image)

        if results.multi_hand_landmarks:
            return results.multi_hand_landmarks
        return None
    
    def draw_landmarks(self, image, hand_landmarks):
        """
        이미지에 손 랜드마크 그리기
        
        Args:
            image: 그릴 이미지 (numpy array, BGR)
            hand_landmarks: MediaPipe 손 랜드마크
        """
        self.drawer.draw_landmarks(
            image, 
            hand_landmarks, 
            mp.solutions.hands.HAND_CONNECTIONS
        )
    
    def get_landmarks_2d(self, hand_landmarks, image_width, image_height):
        """
        손 랜드마크의 2D 좌표 추출

        Args:
            hand_landmarks: MediaPipe 손 랜드마크
            image_width: 이미지 너비
            image_height: 이미지 높이

        Returns:
            dict: {landmark_name: (x, y)}
        """
        lm = hand_landmarks.landmark

        def get_point_2d(landmark_enum):
            """랜드마크 enum → 2D 좌표"""
            return np.array([
                lm[landmark_enum].x * image_width,
                lm[landmark_enum].y * image_height
            ], dtype=np.float32)

        # 엄지
        thm_cmc = get_point_2d(mp.solutions.hands.HandLandmark.THUMB_CMC)
        thm_mcp = get_point_2d(mp.solutions.hands.HandLandmark.THUMB_MCP)
        thm_ip = get_point_2d(mp.solutions.hands.HandLandmark.THUMB_IP)
        thm_tip = get_point_2d(mp.solutions.hands.HandLandmark.THUMB_TIP)

        # 검지
        idx_mcp = get_point_2d(mp.solutions.hands.HandLandmark.INDEX_FINGER_MCP)
        idx_pip = get_point_2d(mp.solutions.hands.HandLandmark.INDEX_FINGER_PIP)
        idx_dip = get_point_2d(mp.solutions.hands.HandLandmark.INDEX_FINGER_DIP)
        idx_tip = get_point_2d(mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP)

        # 중지
        mid_mcp = get_point_2d(mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP)
        mid_pip = get_point_2d(mp.solutions.hands.HandLandmark.MIDDLE_FINGER_PIP)
        mid_dip = get_point_2d(mp.solutions.hands.HandLandmark.MIDDLE_FINGER_DIP)
        mid_tip = get_point_2d(mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP)

        # 약지
        ring_mcp = get_point_2d(mp.solutions.hands.HandLandmark.RING_FINGER_MCP)
        ring_pip = get_point_2d(mp.solutions.hands.HandLandmark.RING_FINGER_PIP)
        ring_dip = get_point_2d(mp.solutions.hands.HandLandmark.RING_FINGER_DIP)
        ring_tip = get_point_2d(mp.solutions.hands.HandLandmark.RING_FINGER_TIP)

        # 새끼
        pinky_mcp = get_point_2d(mp.solutions.hands.HandLandmark.PINKY_MCP)
        pinky_pip = get_point_2d(mp.solutions.hands.HandLandmark.PINKY_PIP)
        pinky_dip = get_point_2d(mp.solutions.hands.HandLandmark.PINKY_DIP)
        pinky_tip = get_point_2d(mp.solutions.hands.HandLandmark.PINKY_TIP)

        # 손목
        wrist = get_point_2d(mp.solutions.hands.HandLandmark.WRIST)

        return {
            'wrist': wrist,
            'thm_cmc': thm_cmc,
            'thm_mcp': thm_mcp,
            'thm_ip': thm_ip,
            'thm_tip': thm_tip,
            'idx_mcp': idx_mcp,
            'idx_pip': idx_pip,
            'idx_dip': idx_dip,
            'idx_tip': idx_tip,
            'mid_mcp': mid_mcp,
            'mid_pip': mid_pip,
            'mid_dip': mid_dip,
            'mid_tip': mid_tip,
            'ring_mcp': ring_mcp,
            'ring_pip': ring_pip,
            'ring_dip': ring_dip,
            'ring_tip': ring_tip,
            'pinky_mcp': pinky_mcp,
            'pinky_pip': pinky_pip,
            'pinky_dip': pinky_dip,
            'pinky_tip': pinky_tip
        }

    def get_landmarks_3d(self, hand_landmarks, image_width):
        """
        손 랜드마크의 Z 좌표 추출

        Args:
            hand_landmarks: MediaPipe 손 랜드마크
            image_width: 이미지 너비

        Returns:
            dict: {landmark_name_z: z_coord}
        """
        lm = hand_landmarks.landmark

        idx_tip_z = float(lm[mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP].z) * image_width
        thm_tip_z = float(lm[mp.solutions.hands.HandLandmark.THUMB_TIP].z) * image_width

        return {
            'idx_tip_z': idx_tip_z,
            'thm_tip_z': thm_tip_z
        }

    def get_normalized_landmarks(self, hand_landmarks):
        """
        정규화된 랜드마크 좌표 추출 (0.0~1.0)

        Args:
            hand_landmarks: MediaPipe 손 랜드마크

        Returns:
            dict: {landmark_name: (x, y)} - 정규화된 좌표
        """
        lm = hand_landmarks.landmark

        return {
            'idx_mcp': (lm[mp.solutions.hands.HandLandmark.INDEX_FINGER_MCP].x,
                       lm[mp.solutions.hands.HandLandmark.INDEX_FINGER_MCP].y),
            'mid_mcp': (lm[mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP].x,
                       lm[mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP].y)
        }

    def close(self):
        """리소스 해제"""
        self.hands.close()