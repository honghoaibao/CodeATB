"""
╔══════════════════════════════════════════════════════╗
║           core/human_behavior.py - v1.4.5            ║
║   Human-Like Behavior Simulation Engine              ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → HumanBehavior (line ~1439)

Features:
  - Random timing variance
  - Natural tap positions với micro-offset
  - Smooth Bezier-curve swipes
  - Reading / typing speed simulation
  - Fatigue factor (chậm dần theo thời gian)
"""

import time
import random


class HumanBehavior:
    """
    Mô phỏng hành vi người dùng thật.
    Giúp giảm nguy cơ bị TikTok phát hiện là bot.
    """

    def __init__(self):
        self.action_count = 0
        self.last_action_time = time.time()

    # ─────────────────────────────────────────
    # Basic timing
    # ─────────────────────────────────────────

    def random_pause(self, min_seconds: float, max_seconds: float, reason: str = "") -> None:
        """Nghỉ ngẫu nhiên trong khoảng [min, max]"""
        duration = random.uniform(min_seconds, max_seconds)
        if reason:
            print(f"⏳ Nghỉ {duration:.1f}s ({reason})")
        time.sleep(duration)

    def thinking_pause(self) -> None:
        """Dừng lại như đang suy nghĩ / quyết định (0.5 – 2s)"""
        time.sleep(random.uniform(0.5, 2.0))

    def get_natural_delay(self, base_min: float, base_max: float) -> float:
        """Trả về delay có tính đến fatigue factor"""
        return random.uniform(base_min, base_max) * self.fatigue_factor()

    # ─────────────────────────────────────────
    # Tap / touch simulation
    # ─────────────────────────────────────────

    def natural_tap(self, device, x: int, y: int, variance: int = 10) -> None:
        """
        Tap với offset ngẫu nhiên (±variance px) để mô phỏng ngón tay thật.
        Thêm micro-movement trước khi tap.
        """
        self.micro_movement_before_tap(device, x, y)

        actual_x = x + random.randint(-variance, variance)
        actual_y = y + random.randint(-variance, variance)

        device.click(actual_x, actual_y)
        time.sleep(random.uniform(0.05, 0.15))  # Micro pause sau tap

        self.action_count += 1
        self.last_action_time = time.time()

    def micro_movement_before_tap(self, device, target_x: int, target_y: int) -> None:
        """Mô phỏng cử động nhỏ khi 'nhắm' vào target trước khi tap"""
        start_x = target_x + random.randint(-50, 50)
        start_y = target_y + random.randint(-50, 50)
        steps = 3
        for i in range(steps):
            # Interpolate towards target (không cần gửi lệnh touch, chỉ delay nhỏ)
            _ = start_x + (target_x - start_x) * (i + 1) / steps
            time.sleep(0.01)

    # ─────────────────────────────────────────
    # Swipe simulation
    # ─────────────────────────────────────────

    def smooth_swipe(
        self,
        device,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 0.3,
        speed_variance: float = 0.2,
    ) -> None:
        """
        Swipe theo đường cong Bezier bậc 2 với tốc độ ngẫu nhiên.
        Tự nhiên hơn swipe thẳng.
        """
        actual_duration = duration * random.uniform(
            1 - speed_variance, 1 + speed_variance
        )

        # Điểm giữa lệch ngẫu nhiên để tạo đường cong
        mid_x = (x1 + x2) // 2 + random.randint(-20, 20)
        mid_y = (y1 + y2) // 2 + random.randint(-20, 20)

        steps = max(1, int(actual_duration * 100))  # 100 steps/s

        for i in range(steps + 1):
            t = i / steps
            # Quadratic Bezier
            x = int((1 - t) ** 2 * x1 + 2 * (1 - t) * t * mid_x + t**2 * x2)
            y = int((1 - t) ** 2 * y1 + 2 * (1 - t) * t * mid_y + t**2 * y2)

            if i == 0:
                device.touch.down(x, y)
            else:
                device.touch.move(x, y)

            time.sleep(actual_duration / steps)

        device.touch.up(x2, y2)
        time.sleep(random.uniform(0.1, 0.3))

        self.action_count += 1
        self.last_action_time = time.time()

    # ─────────────────────────────────────────
    # Reading / typing simulation
    # ─────────────────────────────────────────

    def reading_delay(self, content_length: int = 100) -> None:
        """
        Dừng mô phỏng thời gian đọc nội dung.
        ~3-5 chars/sec tương đương tốc độ đọc người thật.
        """
        words = content_length / 5
        base_time = words / 3.5  # 3.5 words/sec
        actual_time = base_time * random.uniform(0.7, 1.3)
        actual_time = max(0.5, min(5.0, actual_time))
        time.sleep(actual_time)

    def typing_delay(self, text: str) -> None:
        """
        Dừng mô phỏng thời gian gõ text.
        ~4 chars/sec tương đương tốc độ gõ trung bình.
        """
        chars = len(text)
        base_time = chars / 4.0
        actual_time = base_time * random.uniform(0.8, 1.2)
        actual_time = max(0.5, min(10.0, actual_time))
        time.sleep(actual_time)

    # ─────────────────────────────────────────
    # Screen scan
    # ─────────────────────────────────────────

    def screen_scan_pattern(self, device) -> None:
        """
        Mô phỏng mắt người quét qua màn hình trước khi hành động.
        Nhìn vào 1-2 điểm ngẫu nhiên trên màn hình.
        """
        w, h = device.window_size()
        scan_points = [
            (w // 2, h // 3),
            (w // 3, h // 2),
            (2 * w // 3, h // 2),
            (w // 2, 2 * h // 3),
        ]
        for _ in range(random.randint(1, 2)):
            random.choice(scan_points)  # "look" at point (just a delay)
            time.sleep(random.uniform(0.2, 0.5))

    # ─────────────────────────────────────────
    # Random actions
    # ─────────────────────────────────────────

    def occasional_random_action(self, probability: float = 0.05) -> bool:
        """Ngẫu nhiên quyết định có thực hiện action phụ không (5% mặc định)"""
        return random.random() < probability

    # ─────────────────────────────────────────
    # Fatigue simulation
    # ─────────────────────────────────────────

    def fatigue_factor(self) -> float:
        """
        Hệ số chậm dần theo số lượng action (giống người mệt).
        Trả về multiplier áp dụng lên delay.
        """
        if self.action_count < 50:
            return 1.0   # Fresh
        elif self.action_count < 100:
            return 1.1   # Slightly tired
        elif self.action_count < 200:
            return 1.2   # Moderately tired
        else:
            return 1.3   # Quite tired

    def reset_fatigue(self) -> None:
        """Reset action counter (after break)"""
        self.action_count = 0
        print("💪 Đã nghỉ ngơi, năng lượng đầy!")


class TwoLayerPopupHandler:
    """
    v1.4.4: 2-Layer Popup Detection System
    
    Layer 1 (Priority): AI-powered detection using Gemini
    Layer 2 (Fallback): Traditional XML/pattern-based detection
    
    This ensures maximum success rate by combining AI intelligence
    with proven traditional methods.
    """
    
