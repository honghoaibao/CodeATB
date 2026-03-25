"""
╔══════════════════════════════════════════════════════╗
║           ui/constants.py - v1.4.5                   ║
║   AppConstants (magic numbers) + ColorScheme         ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → AppConstants + ColorScheme (line ~2329)
"""


class AppConstants:
    """
    Centralized constants - loại bỏ magic numbers rải rác.
    Dễ tune và maintain.
    """

    # Divine Eye Detection
    DIVINE_EYE_MIN_CONFIDENCE = 0.7
    DIVINE_EYE_LOW_CONFIDENCE = 0.0
    DIVINE_EYE_CHECK_INTERVAL = 3  # Check every N loops

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

    # ─────────────────────────────────────
    # Gradient helpers
    # ─────────────────────────────────────

    @staticmethod
    def gradient_text(text: str, colors: list = None) -> str:
        """Create multi-color gradient text effect"""
        if colors is None:
            colors = ["blue", "cyan", "magenta"]

        if not text:
            return ""

        text_len = len(text)
        colors_len = len(colors)
        parts = []

        for i, char in enumerate(text):
            color_idx = int((i / text_len) * (colors_len - 1))
            color = colors[min(color_idx, colors_len - 1)]
            parts.append(f"[{color}]{char}[/{color}]")

        return "".join(parts)

    @staticmethod
    def rainbow_text(text: str) -> str:
        """Create rainbow effect"""
        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]
        return ColorScheme.gradient_text(text, colors)

    @staticmethod
    def fire_text(text: str) -> str:
        """Create fire effect"""
        colors = ["yellow", "bright_yellow", "red", "bright_red"]
        return ColorScheme.gradient_text(text, colors)


# ═══════════════════════════════════════════════════════════════
# SMART LOGGER v1.4.3
# ═══════════════════════════════════════════════════════════════
    
