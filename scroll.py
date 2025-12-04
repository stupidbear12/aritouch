"""
Scroll Gesture Module
양손 Pinch 제스처 기반 스크롤 제어
"""

import numpy as np
import win32api
import win32con
import time

# 설정
SCROLL_UNIT = 0.03        # 방향당 최소 이동 거리
SCROLL_AMOUNT = 120       # 스크롤 양
SCROLL_DELAY = 0.2        # 제스처 인식 후 딜레이
PINCH_THRESHOLD = 0.05    # Pinch 거리 임계값


class ScrollGestureManager:
    """양손 Pinch 제스처 기반 스크롤 관리"""

    def __init__(self,
                 scroll_unit=SCROLL_UNIT,
                 scroll_amount=SCROLL_AMOUNT,
                 scroll_delay=SCROLL_DELAY,
                 pinch_threshold=PINCH_THRESHOLD):
        """
        Args:
            scroll_unit: 스크롤 트리거 최소 이동 거리
            scroll_amount: 스크롤 양 (휠 델타)
            scroll_delay: 제스처 인식 후 대기 시간
            pinch_threshold: Pinch 거리 임계값
        """
        self.scroll_unit = scroll_unit
        self.scroll_amount = scroll_amount
        self.scroll_delay = scroll_delay
        self.pinch_threshold = pinch_threshold

        # 상태 추적
        self.last_thumb_pos = None
        self.scroll_start_time = None
        self.scroll_ready = False
        self.last_scroll_text = ""

    @staticmethod
    def get_distance(p1, p2):
        """두 점 사이의 거리 계산"""
        return np.linalg.norm(np.array(p1) - np.array(p2))

    def perform_scroll(self, dx, dy):
        """
        스크롤 실행

        Args:
            dx: X 방향 이동량
            dy: Y 방향 이동량

        Returns:
            str: 스크롤 방향 텍스트
        """
        scrolls = []

        # ↑↓ 수직 스크롤
        if abs(dy) >= self.scroll_unit:
            if dy < 0:
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, self.scroll_amount)
                scrolls.append("UP")
            else:
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -self.scroll_amount)
                scrolls.append("DOWN")

        # ←→ 수평 스크롤 (Shift + 휠 사용)
        if abs(dx) >= self.scroll_unit:
            win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)  # Shift 누름
            if dx < 0:
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, self.scroll_amount)
                scrolls.append("LEFT")
            else:
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, -self.scroll_amount)
                scrolls.append("RIGHT")
            win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)  # Shift 뗌

        return " + ".join(scrolls) if scrolls else ""

    def check_pinch(self, landmarks_2d):
        """
        손의 Pinch 제스처 확인

        Args:
            landmarks_2d: 손 랜드마크 2D 좌표 dict

        Returns:
            bool: Pinch 여부
        """
        thumb_tip = landmarks_2d['thm_tip']
        index_tip = landmarks_2d['idx_tip']

        distance = self.get_distance(
            (thumb_tip[0], thumb_tip[1]),
            (index_tip[0], index_tip[1])
        )

        # 정규화된 좌표이므로 이미지 크기 고려 필요
        # 평균 화면 크기(1280px)로 스케일링
        distance_scaled = distance / 1280.0

        return distance_scaled < self.pinch_threshold

    def process_dual_hand_scroll(self, hand_landmarks_list, hand_detector, image_width, image_height):
        """
        양손 Pinch 제스처 기반 스크롤 처리

        Args:
            hand_landmarks_list: 손 랜드마크 리스트
            hand_detector: HandDetector 인스턴스
            image_width: 이미지 너비
            image_height: 이미지 높이

        Returns:
            str: 스크롤 상태 텍스트
        """
        if not hand_landmarks_list or len(hand_landmarks_list) < 2:
            # 양손이 검출되지 않으면 리셋
            self.scroll_ready = False
            self.last_thumb_pos = None
            self.last_scroll_text = ""
            return ""

        # 양손 랜드마크 추출
        hand1_landmarks = hand_detector.get_landmarks_2d(hand_landmarks_list[0], image_width, image_height)
        hand2_landmarks = hand_detector.get_landmarks_2d(hand_landmarks_list[1], image_width, image_height)

        # 양손 Pinch 확인
        hand1_pinch = self.check_pinch(hand1_landmarks)
        hand2_pinch = self.check_pinch(hand2_landmarks)

        # 양손 모두 Pinch 상태일 때만 스크롤
        if hand1_pinch and hand2_pinch:
            # 첫 번째 손의 엄지를 추적
            current_thumb_pos = hand1_landmarks['thm_tip']

            if not self.scroll_ready:
                # 스크롤 시작
                self.scroll_start_time = time.time()
                self.scroll_ready = True
                self.last_thumb_pos = current_thumb_pos
                self.last_scroll_text = "Scroll Ready"
            elif time.time() - self.scroll_start_time > self.scroll_delay and self.last_thumb_pos is not None:
                # 딜레이 후 스크롤 실행
                dx = (current_thumb_pos[0] - self.last_thumb_pos[0]) / image_width
                dy = (current_thumb_pos[1] - self.last_thumb_pos[1]) / image_height

                scroll_text = self.perform_scroll(dx, dy)
                if scroll_text:
                    self.last_scroll_text = f"Scroll: {scroll_text}"

                self.last_thumb_pos = current_thumb_pos
        else:
            # Pinch 해제 시 리셋
            self.scroll_ready = False
            self.last_thumb_pos = None
            if hand1_pinch or hand2_pinch:
                self.last_scroll_text = "Need both hands pinch"
            else:
                self.last_scroll_text = ""

        return self.last_scroll_text

    def reset(self):
        """상태 초기화"""
        self.last_thumb_pos = None
        self.scroll_start_time = None
        self.scroll_ready = False
        self.last_scroll_text = ""
