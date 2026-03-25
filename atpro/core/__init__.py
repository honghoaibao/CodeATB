"""core package - Core automation logic"""
from core.config import ProxyType, ProxyConfig, Config, ConfigManager
from core.device_manager import TikTokPackage, DeviceManager, DeviceHardwareInfo
from core.detection import ScreenState, DetectionResult, DivineEye
from core.stats import FarmSession, AccountDayStats, DayStats, StatsManager, AdvancedStatistics, TimingCalculator, stats_manager
from core.video_interaction import SmartVideoInteraction
from core.priority_account import PriorityAccountManager, FollowVerifier
from core.enhanced_detection import EnhancedDetection
from core.automation import TikTokAutomation

__all__ = [
    "ScreenState", "DetectionResult", "DivineEye",
    "ProxyType", "ProxyConfig", "Config", "ConfigManager",
    "TikTokPackage", "DeviceManager", "DeviceHardwareInfo",
    "FarmSession", "AccountDayStats", "DayStats", "StatsManager",
    "AdvancedStatistics", "TimingCalculator", "stats_manager",
    "SmartVideoInteraction",
    "PriorityAccountManager", "FollowVerifier",
    "EnhancedDetection",
    "TikTokAutomation",
]
