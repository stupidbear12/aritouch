"""
Mathematical Utility Functions
수학 관련 유틸리티 함수
"""

import numpy as np
import math


def clamp(value, min_val, max_val):
    """
    값을 최소/최대 범위로 제한
    
    Args:
        value: 제한할 값
        min_val: 최솟값
        max_val: 최댓값
    
    Returns:
        제한된 값
    """
    return min_val if value < min_val else max_val if value > max_val else value


def l2_distance(point_a, point_b):
    """
    두 점 사이의 L2 거리 (유클리드 거리) 계산
    
    Args:
        point_a: 첫 번째 점 (numpy array or tuple)
        point_b: 두 번째 점 (numpy array or tuple)
    
    Returns:
        거리 (float)
    """
    return float(np.linalg.norm(np.array(point_a) - np.array(point_b)))


def angle_at_joint(point_a, point_b, point_c):
    """
    세 점으로 이루어진 각도 계산 (point_b를 중심으로)
    
    Args:
        point_a: 첫 번째 점
        point_b: 중심점 (관절)
        point_c: 세 번째 점
    
    Returns:
        각도 (degree)
    
    Example:
        손가락 각도 계산:
        angle_at_joint(MCP, PIP, DIP) → PIP 관절의 구부림 정도
    """
    # 벡터 계산
    v1 = np.array(point_a) - np.array(point_b)
    v2 = np.array(point_c) - np.array(point_b)
    
    # 벡터 크기
    norm_v1 = np.linalg.norm(v1) + 1e-9  # 0으로 나누기 방지
    norm_v2 = np.linalg.norm(v2) + 1e-9
    
    # 코사인 값 계산
    cos_angle = np.dot(v1, v2) / (norm_v1 * norm_v2)
    
    # -1 ~ 1 범위로 제한 (부동소수점 오차 방지)
    cos_angle = max(-1.0, min(1.0, float(cos_angle)))
    
    # 라디안 → 도(degree) 변환
    angle_rad = math.acos(cos_angle)
    angle_deg = math.degrees(angle_rad)
    
    return angle_deg


def normalize_coordinates(x, y, width, height):
    """
    픽셀 좌표를 0~1 범위로 정규화
    
    Args:
        x: X 좌표 (픽셀)
        y: Y 좌표 (픽셀)
        width: 이미지 너비
        height: 이미지 높이
    
    Returns:
        (normalized_x, normalized_y)
    """
    norm_x = x / width if width > 0 else 0.0
    norm_y = y / height if height > 0 else 0.0
    return (norm_x, norm_y)


def denormalize_coordinates(norm_x, norm_y, width, height):
    """
    정규화된 좌표를 픽셀 좌표로 변환
    
    Args:
        norm_x: 정규화된 X 좌표 (0~1)
        norm_y: 정규화된 Y 좌표 (0~1)
        width: 화면 너비
        height: 화면 높이
    
    Returns:
        (pixel_x, pixel_y)
    """
    pixel_x = int(norm_x * width)
    pixel_y = int(norm_y * height)
    return (pixel_x, pixel_y)