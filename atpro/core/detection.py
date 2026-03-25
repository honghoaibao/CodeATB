"""
from __future__ import annotations
╔══════════════════════════════════════════════════════╗
║           core/detection.py - v1.4.5                 ║
║   🔮 Divine Eye - AI Vision Detection System         ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → ScreenState + DetectionResult + DivineEye (line ~1841)

Features:
  - Screen state detection (Lost / Popup / Normal / Error)
  - Memory-optimized image processing (< 100MB RAM)
  - Fast detection (< 100ms)
  - Detection caching (0.5s TTL)
  - OpenCV + PIL based (no Gemini needed)
"""

import gc
import io
import time
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

# ── Optional heavy deps ──────────────────────────────
try:
    import cv2
    import numpy as np
    from PIL import Image
    DIVINE_EYE_AVAILABLE = True
except ImportError:
    DIVINE_EYE_AVAILABLE = False
    cv2 = None  # type: ignore
    np = None   # type: ignore
    Image = None  # type: ignore


# ═══════════════════════════════════════════════════════
# ENUMS & DATACLASSES
# ═══════════════════════════════════════════════════════

class ScreenState(Enum):
    """Trạng thái màn hình"""
    NORMAL_VIDEO         = "normal_video"
    LOST                 = "lost"
    POPUP_ACCOUNT_SWITCH = "popup_account_switch"
    POPUP_GENERIC        = "popup_generic"
    FOLLOWING_TAB        = "following_tab"
    FOR_YOU_TAB          = "for_you_tab"
    PROFILE_PAGE         = "profile_page"
    ERROR_SCREEN         = "error_screen"
    NO_INTERNET          = "no_internet"
    LOADING              = "loading"
    UNKNOWN              = "unknown"


@dataclass
class DetectionResult:
    """Kết quả detection từ DivineEye"""
    state: ScreenState
    confidence: float            # 0.0 – 1.0
    detected_elements: List[str] # Các element được phát hiện
    is_lost: bool
    has_popup: bool
    needs_action: bool
    action_suggestion: str
    ram_usage_mb: float
    detection_time_ms: float

    def __str__(self):
        return (
            f"\n🔮 Divine Eye Detection Result:\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"State:      {self.state.value}\n"
            f"Confidence: {self.confidence * 100:.1f}%\n"
            f"Lost:       {'✅ YES' if self.is_lost else '❌ NO'}\n"
            f"Popup:      {'✅ YES' if self.has_popup else '❌ NO'}\n"
            f"Elements:   {', '.join(self.detected_elements)}\n"
            f"Action:     {self.action_suggestion}\n"
            f"RAM:        {self.ram_usage_mb:.1f}MB\n"
            f"Time:       {self.detection_time_ms:.1f}ms\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )


# ═══════════════════════════════════════════════════════
# DIVINE EYE
# ═══════════════════════════════════════════════════════

class DivineEye:
    """
    🔮 Divine Eye – AI Vision System

    Phát hiện trạng thái màn hình bằng OpenCV với RAM tối thiểu.
    Không cần Gemini / cloud AI – chạy hoàn toàn local.
    """

    def __init__(self, enable_advanced_ocr: bool = False):
        self.enable_advanced_ocr = enable_advanced_ocr

        # Memory limits
        self.max_screenshot_width  = 720
        self.max_screenshot_height = 1600
        self.jpeg_quality          = 85

        # Detection cache
        self.last_screenshot_hash    = None
        self.last_detection_result   = None
        self.cache_ttl_seconds       = 0.5
        self.last_detection_time     = 0

        # Perf stats
        self.total_detections = 0
        self.total_time_ms    = 0
        self.cache_hits       = 0

        self._init_ui_patterns()

    def _init_ui_patterns(self):
        """Khởi tạo UI pattern matchers"""
        self.ui_patterns = {
            "account_switch_popup": {
                "description": "Popup chuyển account",
                "color_ranges": [(200, 200, 200), (255, 255, 255)],
                "position": "center",
                "size_ratio": (0.3, 0.6),
            },
            "generic_popup": {
                "description": "Popup chung",
                "color_ranges": [(180, 180, 180), (255, 255, 255)],
                "position": "center",
                "size_ratio": (0.2, 0.8),
            },
            "following_tab": {
                "description": "Tab Following",
                "text_indicators": ["Following", "Đang follow"],
                "position": "top",
                "color_ranges": [(255, 255, 255), (255, 255, 255)],
            },
            "for_you_tab": {
                "description": "Tab For You",
                "text_indicators": ["For You", "Dành cho bạn"],
                "position": "top",
                "color_ranges": [(255, 255, 255), (255, 255, 255)],
            },
            "no_internet": {
                "description": "Không có mạng",
                "text_indicators": ["No internet", "Không có kết nối"],
                "color_ranges": [(100, 100, 100), (200, 200, 200)],
            },
            "error_screen": {
                "description": "Màn hình lỗi",
                "text_indicators": ["Error", "Lỗi", "Something went wrong"],
                "color_ranges": [(100, 100, 100), (200, 200, 200)],
            },
        }

    # ─────────────────────────────────────────
    # Main detection entry
    # ─────────────────────────────────────────

    def detect(self, screenshot, device=None) -> DetectionResult:
        """
        🔮 Phát hiện trạng thái màn hình.

        Args:
            screenshot: PIL Image | numpy array | None
            device:     uiautomator2 device (dùng khi screenshot=None)

        Returns:
            DetectionResult
        """
        if not DIVINE_EYE_AVAILABLE:
            return DetectionResult(
                state=ScreenState.UNKNOWN,
                confidence=0.0,
                detected_elements=["divine_eye_unavailable"],
                is_lost=False,
                has_popup=False,
                needs_action=False,
                action_suggestion="continue",
                ram_usage_mb=0.0,
                detection_time_ms=0.0,
            )

        start_time = time.time()

        # Get screenshot
        if screenshot is None and device is not None:
            screenshot = device.screenshot()

        # Normalize to PIL Image
        if isinstance(screenshot, np.ndarray):
            screenshot = Image.fromarray(screenshot)
        elif not isinstance(screenshot, Image.Image):
            try:
                screenshot = Image.open(screenshot)
            except Exception:
                raise ValueError("Invalid screenshot format")

        # Cache check
        screenshot_hash = self._hash_image(screenshot)
        current_time = time.time()

        if (
            screenshot_hash == self.last_screenshot_hash
            and self.last_detection_result is not None
            and current_time - self.last_detection_time < self.cache_ttl_seconds
        ):
            self.cache_hits += 1
            cached = self.last_detection_result
            cached.detection_time_ms = (time.time() - start_time) * 1000
            return cached

        # Optimize → numpy
        optimized = self._optimize_image(screenshot)
        img_np = np.array(optimized)

        # ── Detection pipeline ──
        detected_elements: List[str] = []
        state     = ScreenState.UNKNOWN
        confidence = 0.0
        has_popup  = False

        # 1. Popup detection
        has_popup, popup_type, popup_conf = self._detect_popup(img_np)
        if has_popup:
            detected_elements.append(f"popup_{popup_type}")
            state      = (
                ScreenState.POPUP_ACCOUNT_SWITCH
                if popup_type == "account_switch"
                else ScreenState.POPUP_GENERIC
            )
            confidence = popup_conf

        # 2. Error screens
        if not has_popup:
            has_error, error_type, error_conf = self._detect_error_screen(img_np)
            if has_error:
                detected_elements.append(f"error_{error_type}")
                state      = ScreenState.NO_INTERNET if error_type == "no_internet" else ScreenState.ERROR_SCREEN
                confidence = error_conf

        # 3. Tab detection
        if state == ScreenState.UNKNOWN:
            tab_type, tab_conf = self._detect_tab(img_np)
            if tab_conf > 0.5:
                detected_elements.append(f"tab_{tab_type}")
                state      = ScreenState.FOLLOWING_TAB if tab_type == "following" else ScreenState.FOR_YOU_TAB
                confidence = tab_conf

        # 4. TikTok app check
        if state == ScreenState.UNKNOWN:
            is_tiktok, tiktok_conf = self._detect_tiktok_app(img_np)
            if not is_tiktok:
                state      = ScreenState.LOST
                detected_elements.append("not_tiktok")
                confidence = 1.0 - tiktok_conf
            else:
                state      = ScreenState.NORMAL_VIDEO
                detected_elements.append("tiktok_video")
                confidence = tiktok_conf

        is_lost         = state in {ScreenState.LOST, ScreenState.ERROR_SCREEN, ScreenState.NO_INTERNET}
        action_suggestion = self._suggest_action(state, has_popup)
        needs_action    = action_suggestion != "continue"
        ram_usage_mb    = img_np.nbytes / (1024 * 1024)
        detection_time_ms = (time.time() - start_time) * 1000

        result = DetectionResult(
            state=state,
            confidence=confidence,
            detected_elements=detected_elements,
            is_lost=is_lost,
            has_popup=has_popup,
            needs_action=needs_action,
            action_suggestion=action_suggestion,
            ram_usage_mb=ram_usage_mb,
            detection_time_ms=detection_time_ms,
        )

        # Update cache & stats
        self.last_screenshot_hash  = screenshot_hash
        self.last_detection_result = result
        self.last_detection_time   = current_time
        self.total_detections     += 1
        self.total_time_ms        += detection_time_ms

        # Free memory
        del img_np, optimized
        gc.collect()

        return result

    # ─────────────────────────────────────────
    # Image processing helpers
    # ─────────────────────────────────────────

    def _optimize_image(self, img: "Image.Image") -> "Image.Image":
        """Downscale + convert to RGB để tiết kiệm RAM"""
        width, height = img.size
        if width > self.max_screenshot_width or height > self.max_screenshot_height:
            ratio = min(
                self.max_screenshot_width / width,
                self.max_screenshot_height / height,
            )
            img = img.resize(
                (int(width * ratio), int(height * ratio)), Image.LANCZOS
            )
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img

    def _hash_image(self, img: "Image.Image") -> str:
        """Fast hash of 64×64 thumbnail for cache key"""
        thumb = img.copy()
        thumb.thumbnail((64, 64))
        buf = io.BytesIO()
        thumb.save(buf, format="JPEG", quality=50)
        return hashlib.md5(buf.getvalue()).hexdigest()

    # ─────────────────────────────────────────
    # Sub-detectors
    # ─────────────────────────────────────────

    def _detect_popup(self, img_np: "np.ndarray") -> Tuple[bool, str, float]:
        """
        Detect popup using color and position analysis
        
        Returns:
            (has_popup, popup_type, confidence)
        """
        height, width = img_np.shape[:2]
        
        # Get center region (where popups usually appear)
        center_y1 = int(height * 0.25)
        center_y2 = int(height * 0.75)
        center_x1 = int(width * 0.1)
        center_x2 = int(width * 0.9)
        
        center_region = img_np[center_y1:center_y2, center_x1:center_x2]
        
        # Calculate average brightness in center
        gray = cv2.cvtColor(center_region, cv2.COLOR_RGB2GRAY)
        avg_brightness = np.mean(gray)
        
        # Popups usually have bright background (> 200)
        if avg_brightness > 200:
            # Likely a popup
            # Check if it's account switch popup (has specific layout)
            # Simple heuristic: if center region is > 40% of screen
            center_area = (center_y2 - center_y1) * (center_x2 - center_x1)
            total_area = height * width
            coverage = center_area / total_area
            
            if coverage > 0.4:
                # Large popup - likely account switch
                return True, 'account_switch', 0.7
            else:
                # Smaller popup
                return True, 'generic', 0.6
        
        return False, 'none', 0.0
    
    def _detect_error_screen(self, img_np: "np.ndarray") -> Tuple[bool, str, float]:
        """Detect error screens"""
        # Error screens usually have gray/dark colors and centered text
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        avg_brightness = np.mean(gray)
        
        # Error screens tend to be darker (< 100) or grayish (100-150)
        if avg_brightness < 150:
            # Check for uniform color (error screens are usually plain)
            std_dev = np.std(gray)
            
            if std_dev < 30:  # Very uniform color
                # Likely an error screen
                # Distinguish between no internet vs other errors
                # No internet screens are usually lighter gray
                if avg_brightness > 100:
                    return True, 'no_internet', 0.7
                else:
                    return True, 'generic', 0.6
        
        return False, 'none', 0.0
    
    def _detect_tab(self, img_np: "np.ndarray") -> Tuple[str, float]:
        """Detect active tab (Following vs For You) by white pixel distribution"""
        height, width = img_np.shape[:2]
        top_region    = img_np[0 : int(height * 0.1), :]
        left          = top_region[:, : int(width * 0.3)]
        right         = top_region[:, int(width * 0.7) :]

        left_white  = np.sum(left  > 240)
        right_white = np.sum(right > 240)

        if left_white > right_white * 1.5:
            return "following", 0.6
        if right_white > left_white * 1.5:
            return "for_you", 0.6

        return "unknown", 0.3

    def _detect_tiktok_app(self, img_np: "np.ndarray") -> Tuple[bool, float]:
        """
        Detect if we're in TikTok app
        
        Returns:
            (is_tiktok, confidence)
        """
        # TikTok has characteristic black background for videos
        # Check if image has significant black areas
        
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        
        # Count dark pixels (< 30)
        dark_pixels = np.sum(gray < 30)
        total_pixels = gray.size
        dark_ratio = dark_pixels / total_pixels
        
        # TikTok video screens usually have > 40% dark pixels
        if dark_ratio > 0.4:
            return True, min(dark_ratio / 0.6, 1.0)
        
        # Also check for video-like aspect ratio content
        # Videos usually have consistent vertical bars on sides
        height, width = img_np.shape[:2]
        
        # Check left and right edges
        left_edge = img_np[:, :int(width*0.05)]
        right_edge = img_np[:, int(width*0.95):]
        
        left_avg = np.mean(left_edge)
        right_avg = np.mean(right_edge)
        
        # If both edges are dark (< 50), likely a video
        if left_avg < 50 and right_avg < 50:
            return True, 0.7
        
        return False, dark_ratio
    
    def _suggest_action(self, state: ScreenState, has_popup: bool) -> str:
        """Map screen state to suggested action string"""
        action_map = {
            ScreenState.LOST:                 "back_to_tiktok",
            ScreenState.POPUP_ACCOUNT_SWITCH: "select_account",
            ScreenState.POPUP_GENERIC:        "close_popup",
            ScreenState.NO_INTERNET:          "wait_reconnect",
            ScreenState.ERROR_SCREEN:         "restart_app",
            ScreenState.FOLLOWING_TAB:        "switch_to_for_you",
        }
        return action_map.get(state, "continue")

    # ─────────────────────────────────────────
    # Stats
    # ─────────────────────────────────────────

    def get_stats(self) -> Dict:
        avg_time       = self.total_time_ms / self.total_detections if self.total_detections else 0
        cache_hit_rate = self.cache_hits / self.total_detections * 100 if self.total_detections else 0
        return {
            "total_detections":     self.total_detections,
            "avg_detection_time_ms": avg_time,
            "cache_hits":           self.cache_hits,
            "cache_hit_rate":       f"{cache_hit_rate:.1f}%",
            "total_time_seconds":   self.total_time_ms / 1000,
        }

    def reset_stats(self):
        """Reset performance stats"""
        self.total_detections = 0
        self.total_time_ms = 0
        self.cache_hits = 0

# Initialize Divine Eye globally (if available)
if DIVINE_EYE_AVAILABLE:
    divine_eye = DivineEye()
    print("✅ Divine Eye initialized - AI Vision Active")
else:
    divine_eye = None
    print("⚠️  Divine Eye disabled - Install opencv-python numpy for AI Vision")


# ═══════════════════════════════════════════════════════════════
# 🎨 ULTIMATE COLOR SCHEME v1.4.3
# ═══════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════
# v1.4.3: CONSTANTS - Extracted Magic Numbers
# ═══════════════════════════════════════════════════════════════

class AppConstants:
    """
    v1.4.3: Centralized constants to replace magic numbers
    
    Extracted from scattered hardcoded values throughout the codebase.
    Makes tuning and maintenance much easier.
    """
    
    # Divine Eye Detection
    DIVINE_EYE_MIN_CONFIDENCE = 0.7
    DIVINE_EYE_LOW_CONFIDENCE = 0.0
    DIVINE_EYE_CHECK_INTERVAL = 3  # v1.4.3: Check every N loops (reduces blocking)
    
    # UI Position Ratios
    SHOP_ICON_X_RATIO = 0.92
    SHOP_ICON_Y_TOP_RATIO = 0.25
    SHOP_ICON_Y_BOTTOM_RATIO = 0.75
    LIKE_BUTTON_X_MIN_RATIO = 0.20
    LIKE_BUTTON_X_MAX_RATIO = 0.70
    AVATAR_CLICK_X_RATIO = 0.90
    AVATAR_CLICK_Y_RATIO = 0.50
    
    # Area Thresholds (pixels²)
    SHOP_ICON_MIN_AREA = 900
    SHOP_ICON_MAX_AREA = 6400
    CONTOUR_MIN_AREA = 3000
    
    # Retry Counts
    MAX_SHOP_RETRY = 3
    MAX_BACK_ATTEMPTS = 3
    MAX_FOLLOW_VERIFICATION_RETRY = 4
    MAX_SCROLL_ATTEMPTS = 7
    
    # Timing (seconds)
    CLICK_DELAY = 0.05
    SHORT_DELAY = 0.3
    MEDIUM_DELAY = 1.0
    LONG_DELAY = 2.0
    NETWORK_DELAY = 5.0
    
    # Screen Dimensions (default fallback)
    DEFAULT_SCREEN_WIDTH = 1080
    DEFAULT_SCREEN_HEIGHT = 2400
    
    # Notification Interval
    MILESTONE_INTERVAL = 10  # Send notification every N accounts


class ColorScheme:
    """Ultimate professional color palette with gradients & effects"""
    
    # Primary colors
    PRIMARY = "bright_blue"
    SECONDARY = "cyan"
    SUCCESS = "bright_green"
    WARNING = "bright_yellow"
    ERROR = "bright_red"
    INFO = "bright_cyan"
    
    # Accents & Gradients
    ACCENT = "bright_magenta"
    HIGHLIGHT = "bright_white"
    GRADIENT_START = "blue"
    GRADIENT_MIDDLE = "cyan"
    GRADIENT_END = "magenta"
    
    # Text
    TEXT_PRIMARY = "white"
    TEXT_SECONDARY = "bright_white"
    TEXT_DIM = "dim"
    TEXT_BOLD = "bold white"
    TEXT_ITALIC = "italic"
    
    # Status colors
    STATUS_ACTIVE = "bright_green"
    STATUS_IDLE = "bright_yellow"
    STATUS_ERROR = "bright_red"
    STATUS_PENDING = "bright_cyan"
    STATUS_SUCCESS = "green"
    STATUS_WARNING = "yellow"
    STATUS_RUNNING = "blue"
    
    # Special effects
    NOTIFICATION = "yellow"
    ALERT = "red"
    CRITICAL = "bold red"
    TROPHY = "gold1"
    STAR = "yellow"
    FIRE = "red"
    
    # Backgrounds
    BG_SUCCESS = "on green"
    BG_WARNING = "on yellow"
    BG_ERROR = "on red"
    BG_INFO = "on blue"
    
