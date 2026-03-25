"""
╔══════════════════════════════════════════════════════╗
║           core/config.py - v1.4.5                    ║
║   ProxyType + ProxyConfig + Config + ConfigManager   ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py:
  - ProxyType    (line ~6031)
  - ProxyConfig  (line ~6038)
  - Config       (line ~6074)
  - ConfigManager(line ~6347)
"""

import os
import json
import random
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────
# ProxyType / ProxyConfig
# ─────────────────────────────────────────────────────────────────

class ProxyType(Enum):
    HTTP   = "http"
    HTTPS  = "https"
    SOCKS4 = "socks4"
    SOCKS5 = "socks5"


@dataclass
class ProxyConfig:
    """Cấu hình proxy đơn giản (backward compat)"""
    enabled: bool = False
    proxy_type: str = ProxyType.HTTP.value
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""

    def get_proxy_url(self) -> Optional[str]:
        if not self.enabled or not self.host or not self.port:
            return None
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type}://{self.host}:{self.port}"

    def is_valid(self) -> bool:
        if not self.enabled:
            return True
        return bool(self.host) and 1 <= self.port <= 65535


# ─────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────

class Config:
    """Config v1.4.5 - Tất cả cài đặt của AT Tool"""

    def __init__(self):
        # TikTok Package
        self.selected_package: str = "TIKTOK"   # TikTokPackage.name

        # Account Button Position
        self.use_custom_account_button_y: bool = False
        self.custom_account_button_y_px: int = 144
        self.account_button_y_positions: List[float] = [0.06, 0.08, 0.10, 0.12, 0.14, 0.16]

        # Time settings
        self.minutes_per_account: int = 5
        self.buffer_minutes: int = 10

        # ── Smart Video Interaction ──────────────────────────────
        self.enable_smart_video_interaction: bool = True
        self.not_interested_threshold: int = 100
        self.repost_threshold: int = 10000

        # ── Priority Farming ─────────────────────────────────────
        self.enable_priority_farming: bool = True
        self.priority_mode: str = "sessions"    # "sessions" | "actions"

        # ── Follow Verification ──────────────────────────────────
        self.enable_follow_verification: bool = True
        self.max_follow_retry: int = 2

        # ── Advanced Stats ───────────────────────────────────────
        self.stats_auto_export: bool = False
        self.stats_export_interval_hours: int = 24

        # ── Device Info ──────────────────────────────────────────
        self.track_device_info: bool = True
        self.log_device_info_on_start: bool = True

        # ── Telegram Notifications ───────────────────────────────
        self.telegram_enabled: bool = False
        self.telegram_bot_token: str = ""
        self.telegram_chat_id: str = ""
        self.telegram_notify_start: bool = True
        self.telegram_notify_complete: bool = True
        self.telegram_notify_error: bool = True
        self.telegram_notify_milestone: bool = True

        # ── Discord Notifications ────────────────────────────────
        self.discord_enabled: bool = False
        self.discord_webhook_url: str = ""
        self.discord_notify_start: bool = True
        self.discord_notify_complete: bool = True
        self.discord_notify_error: bool = True
        self.discord_notify_milestone: bool = True

        self.notification_cooldown_minutes: int = 5

        # ── Rest Between Accounts ────────────────────────────────
        self.enable_rest_between_accounts: bool = False
        self.rest_duration_minutes: int = 2

        # ── Video Watch ──────────────────────────────────────────
        self.video_watch_time_min: float = 3.0
        self.video_watch_time_max: float = 8.0

        # ── Action Rates ─────────────────────────────────────────
        self.like_rate: float = 0.3
        self.follow_rate: float = 0.15
        self.comment_rate: float = 0.1
        self.notification_rate: float = 0.05
        self.shop_rate: float = 0.05

        # ── Notification (inbox) ─────────────────────────────────
        self.notification_scroll_times: int = 3
        self.notification_watch_time: float = 2.0

        # ── Shop ─────────────────────────────────────────────────
        self.shop_scroll_times: int = 5
        self.shop_item_watch_time: float = 1.5

        # ── Skip ─────────────────────────────────────────────────
        self.skip_ads: bool = True
        self.skip_live: bool = True

        # ── Comments pool ────────────────────────────────────────
        self.comments: List[str] = [
            "Hay quá", "Tuyệt vời", "👍", "❤️", "Đỉnh",
            "Amazing", "Great content", "🔥", "💯", "Quá đỉnh",
        ]

        # ── Delays ───────────────────────────────────────────────
        self.delay_after_like: float = 0.5
        self.delay_after_follow: float = 1.0
        self.delay_after_comment: float = 1.5
        self.delay_after_back: float = 0.5
        self.delay_between_accounts: float = 2.0

        # ── Swipe ────────────────────────────────────────────────
        self.swipe_random_range: int = 50

        # ── Blacklist ────────────────────────────────────────────
        self.blacklist_keywords: List[str] = [
            "tiktok", "for you", "following", "live", "search",
            "discover", "inbox", "profile", "shop", "store",
        ]
        self.ads_keywords: List[str] = ["sponsored", "quảng cáo", "ad", "promoted"]
        self.ads_ui_keywords: List[str] = ["skip", "learn more", "install"]

        # ── Checkpoint keywords ──────────────────────────────────
        self.checkpoint_keywords: List[str] = [
            "suspicious activity", "hoạt động bất thường",
            "verify your account", "xác minh tài khoản",
            "unusual activity", "account suspended",
            "tài khoản bị khóa", "verify by phone",
        ]

        # ── Screen boundaries ────────────────────────────────────
        self.account_list_y_min: float = 0.15
        self.account_list_y_max: float = 0.85
        self.profile_safe_y_max: float = 0.50
        self.like_area_y_min: float = 0.40
        self.like_area_y_max: float = 0.70

        # ── Recovery ─────────────────────────────────────────────
        self.max_back_attempts: int = 5
        self.back_delay: float = 1.0
        self.check_popup_rate: float = 0.1
        self.check_lost_rate: float = 0.05

        # ── Live / Account switch ─────────────────────────────────
        self.live_watch_seconds: float = 3.0
        self.account_switch_verify_delay: float = 3.0

        # ── Verify account ───────────────────────────────────────
        self.enable_verify_account: bool = True
        self.max_verify_attempts: int = 2

        # ── 1234 Popup ───────────────────────────────────────────
        self.enable_auto_1234_popup: bool = True
        self.popup_1234_keywords: List[str] = [
            "enter 1 2 3 4", "type 1 2 3 4", "input 1 2 3 4",
            "enter 1234", "type 1234", "input 1234",
            "nhập 1 2 3 4", "nhập 1234",
            "gõ 1 2 3 4", "gõ 1234",
            "1234 để tiếp tục", "verification code", "mã xác nhận",
            "security check", "kiểm tra bảo mật",
        ]

        # ── Profile popup scan ───────────────────────────────────
        self.enable_profile_popup_scan: bool = True
        self.profile_popup_max_scans: int = 3

        # ── Checkpoint check ─────────────────────────────────────
        self.enable_checkpoint_check: bool = True

        # ── AI Popup Handling (v1.4.4) ───────────────────────────
        self.ai_popup_enabled: bool = True
        self.ai_popup_priority: bool = True
        self.ai_max_retries: int = 2
        self.ai_confidence_threshold: float = 0.7

        # ── Auto-switch Proxy (v1.4.4) ───────────────────────────
        self.auto_switch_proxy_enabled: bool = False
        self.close_app_before_proxy_switch: bool = True
        self.reopen_app_after_proxy_switch: bool = True
        self.proxy_switch_delay_seconds: int = 3

        # ── Legacy Proxy (backward compat) ───────────────────────

        # ── Keywords bị thiếu khi tách module ──────────────────────
        self.nav_keywords: List[str]        = ["home", "trang chủ", "for you", "following"]
        self.nav_home_keywords: List[str]   = ["home", "trang chủ", "for you"]
        self.nav_inbox_keywords: List[str]  = ["inbox", "hộp thư", "message", "tin nhắn"]
        self.nav_shop_keywords: List[str]   = ["shop", "cửa hàng", "mall", "store"]
        self.live_keywords: List[str]       = ["live", "trực tiếp", "đang phát trực tiếp"]
        self.close_popup_keywords: List[str]= ["not now", "để sau", "cancel", "hủy"]
        self.swipe_delay_min: float         = 1.0
        self.swipe_delay_max: float         = 3.0
        self.delay_after_switch_click: float= 3.0
        self.delay_before_reopen: float     = 2.0
        self.proxy = ProxyConfig()

    # ── Helpers ───────────────────────────────────────────────────

    def get_tiktok_package(self) -> str:
        from core.device_manager import TikTokPackage
        try:
            return TikTokPackage[self.selected_package].package_name
        except (KeyError, AttributeError):
            return TikTokPackage.TIKTOK.package_name

    def get_video_watch_time(self) -> float:
        return random.uniform(self.video_watch_time_min, self.video_watch_time_max)

    def get_all_blacklist_keywords(self) -> List[str]:
        return self.blacklist_keywords

    def get_all_account_button_positions(self, screen_height: int) -> List[int]:
        if self.use_custom_account_button_y:
            return [self.custom_account_button_y_px]
        return [int(screen_height * r) for r in self.account_button_y_positions]

    def calculate_total_time(self, num_accounts: int) -> Tuple[int, str]:
        """Tính tổng thời gian bao gồm buffer + rest"""
        farm_time   = self.minutes_per_account * 60 * num_accounts
        buffer_time = self.buffer_minutes * 60
        rest_time   = (
            self.rest_duration_minutes * 60 * (num_accounts - 1)
            if self.enable_rest_between_accounts else 0
        )
        total = farm_time + buffer_time + rest_time
        h = total // 3600
        m = (total % 3600) // 60
        formatted = f"{h}h{m:02d}m" if h else f"{m}m"
        return (total, formatted)


# ─────────────────────────────────────────────────────────────────
# ConfigManager
# ─────────────────────────────────────────────────────────────────

class ConfigManager:
    """Load / Save Config từ JSON file"""

    def __init__(self, config_file: str = "at_tool_config.json"):
        self.config_file = config_file
        self.config = Config()
        self.load()

    def load(self):
        try:
            if not os.path.exists(self.config_file):
                return
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, value in data.items():
                if key == "proxy":
                    pd = value
                    self.config.proxy = ProxyConfig(
                        enabled=pd.get("enabled", False),
                        proxy_type=pd.get("proxy_type", ProxyType.HTTP.value),
                        host=pd.get("host", ""),
                        port=pd.get("port", 0),
                        username=pd.get("username", ""),
                        password=pd.get("password", ""),
                    )
                elif hasattr(self.config, key):
                    setattr(self.config, key, value)
        except Exception as e:
            print(f"Lỗi load config: {e}")

    def save(self, config: Config = None):
        if config is None:
            config = self.config
        try:
            data: dict = {}
            for key in dir(config):
                if key.startswith("_") or callable(getattr(config, key)):
                    continue
                value = getattr(config, key)
                if key == "proxy":
                    data["proxy"] = {
                        "enabled":    value.enabled,
                        "proxy_type": value.proxy_type,
                        "host":       value.host,
                        "port":       value.port,
                        "username":   value.username,
                        "password":   value.password,
                    }
                else:
                    try:
                        json.dumps(value)   # only serialisable values
                        data[key] = value
                    except (TypeError, ValueError):
                        pass
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi save config: {e}")
