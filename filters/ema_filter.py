"""
Exponential Moving Average Filter
지수 이동 평균 필터 (떨림 제거)
"""


class EMAFilter:
    """
    지수 이동 평균 필터
    
    손 떨림이나 센서 노이즈를 제거하여 부드러운 값을 출력
    """
    
    def __init__(self, alpha=0.5):
        """
        Args:
            alpha: 필터 계수 (0~1)
                   - 높을수록 현재 값에 민감 (빠른 반응, 노이즈 많음)
                   - 낮을수록 이전 값 유지 (느린 반응, 부드러움)
        """
        self.alpha = float(alpha)
        self._value = None
    
    def update(self, new_value):
        """
        새로운 값으로 필터 업데이트
        
        Args:
            new_value: 새로 측정된 값
        
        Returns:
            필터링된 값
        """
        if self._value is None:
            # 처음 값은 그대로 사용
            self._value = new_value
        else:
            # EMA 공식: new = α × current + (1-α) × previous
            self._value = self.alpha * new_value + (1 - self.alpha) * self._value
        
        return self._value
    
    def get_value(self):
        """현재 필터링된 값 반환"""
        return self._value
    
    def reset(self):
        """필터 초기화"""
        self._value = None
    
    def set_alpha(self, alpha):
        """필터 계수 변경"""
        self.alpha = float(alpha)


class MultiEMAFilter:
    """
    여러 값을 동시에 필터링하는 EMA 필터
    
    예: (x, y) 좌표를 동시에 필터링
    """
    
    def __init__(self, alpha=0.5, dimensions=2):
        """
        Args:
            alpha: 필터 계수
            dimensions: 필터링할 값의 차원 (예: 2D 좌표는 2)
        """
        self.alpha = float(alpha)
        self.dimensions = dimensions
        self._values = None
    
    def update(self, new_values):
        """
        새로운 값들로 필터 업데이트
        
        Args:
            new_values: 새로 측정된 값들 (tuple or list)
        
        Returns:
            필터링된 값들 (tuple)
        """
        if len(new_values) != self.dimensions:
            raise ValueError(f"Expected {self.dimensions} values, got {len(new_values)}")
        
        if self._values is None:
            # 처음 값은 그대로 사용
            self._values = tuple(new_values)
        else:
            # 각 차원에 대해 EMA 적용
            filtered = []
            for i in range(self.dimensions):
                filtered_val = self.alpha * new_values[i] + (1 - self.alpha) * self._values[i]
                filtered.append(filtered_val)
            self._values = tuple(filtered)
        
        return self._values
    
    def get_values(self):
        """현재 필터링된 값들 반환"""
        return self._values
    
    def reset(self):
        """필터 초기화"""
        self._values = None
    
    def set_alpha(self, alpha):
        """필터 계수 변경"""
        self.alpha = float(alpha)