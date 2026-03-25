"""
╔══════════════════════════════════════════════════════╗
║       core/device_manager.py - v1.4.5                ║
║   TikTokPackage + DeviceManager + DeviceHardwareInfo ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py:
  - TikTokPackage      (line ~5968)
  - DeviceManager      (line ~5982)
  - DeviceHardwareInfo (line ~5324)
"""

import re
import subprocess
from enum import Enum
from typing import Dict, List, Optional

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None


from ui.logger import smart_logger
from ui.ultimate_ui import UltimateUI as _UltimateUI
_ultimate_ui_instance = _UltimateUI()
ultimate_ui = _ultimate_ui_instance
# ─────────────────────────────────────────────────────────────────
# TikTokPackage
# ─────────────────────────────────────────────────────────────────

class TikTokPackage(Enum):
    TIKTOK       = ("com.zhiliaoapp.musically",      "TikTok")
    TIKTOK_LITE  = ("com.zhiliaoapp.musically.go",   "TikTok Lite")
    TIKTOK_VN    = ("com.ss.android.ugc.trill",      "TikTok VN")
    TIKTOK_ASIA  = ("com.zhiliaoapp.musically.asia", "TikTok Asia")
    TIKTOK_CHINA = ("com.ss.android.ugc.aweme",      "抖音 (Douyin)")

    def __init__(self, package_name: str, display_name: str):
        self.package_name = package_name
        self.display_name = display_name


# ─────────────────────────────────────────────────────────────────
# DeviceManager
# ─────────────────────────────────────────────────────────────────

class DeviceManager:
    """Quản lý kết nối thiết bị ADB / uiautomator2"""

    @staticmethod
    def list_devices() -> List[str]:
        """Liệt kê tất cả thiết bị đang kết nối qua ADB"""
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
            devices = []
            for line in result.stdout.split("\n"):
                if "\tdevice" in line:
                    devices.append(line.split("\t")[0])
            return devices
        except Exception as e:
            print(f"Lỗi list devices: {e}")
            return []

    @staticmethod
    def connect_u2(device_id: str) -> "Optional[u2.Device]":
        """Connect uiautomator2"""
        try:
            device = u2.connect(device_id)
            ultimate_ui.show_message(f"✅ Đã kết nối: {device_id}", "success")
            return device
        except Exception as e:
            ultimate_ui.show_message(f"❌ Lỗi kết nối: {e}", "error")
            return None

# ══════════════════════════════════════════════════════════════════
# END OF PART 1/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║                    PART 2/8 - CONFIG                           ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# PROXY TYPE ENUM v1.4.3
# ═══════════════════════════════════════════════════════════════


class DeviceHardwareInfo:
    """
    Lấy thông tin phần cứng thiết bị v1.4.3
    """
    
    @staticmethod
    def get_device_info(device_id: str = None) -> Dict[str, str]:
        """
        Lấy thông tin thiết bị
        
        Returns:
            {
                'brand': str,
                'model': str,
                'android_version': str,
                'cpu': str,
                'total_ram_mb': int,
                'available_ram_mb': int,
                'total_storage_mb': int,
                'available_storage_mb': int
            }
        """
        try:
            device_arg = ['-s', device_id] if device_id else []
            
            info = {}
            
            # Get brand
            result = subprocess.run(
                ['adb'] + device_arg + ['shell', 'getprop', 'ro.product.brand'],
                capture_output=True, text=True, timeout=5
            )
            info['brand'] = result.stdout.strip() if result.returncode == 0 else 'Unknown'
            
            # Get model
            result = subprocess.run(
                ['adb'] + device_arg + ['shell', 'getprop', 'ro.product.model'],
                capture_output=True, text=True, timeout=5
            )
            info['model'] = result.stdout.strip() if result.returncode == 0 else 'Unknown'
            
            # Get Android version
            result = subprocess.run(
                ['adb'] + device_arg + ['shell', 'getprop', 'ro.build.version.release'],
                capture_output=True, text=True, timeout=5
            )
            info['android_version'] = result.stdout.strip() if result.returncode == 0 else 'Unknown'
            
            # Get CPU info
            result = subprocess.run(
                ['adb'] + device_arg + ['shell', 'getprop', 'ro.product.cpu.abi'],
                capture_output=True, text=True, timeout=5
            )
            info['cpu'] = result.stdout.strip() if result.returncode == 0 else 'Unknown'
            
            # Get RAM info from /proc/meminfo
            result = subprocess.run(
                ['adb'] + device_arg + ['shell', 'cat', '/proc/meminfo'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                meminfo = result.stdout
                
                # Parse MemTotal
                match = re.search(r'MemTotal:\s+(\d+)\s+kB', meminfo)
                if match:
                    info['total_ram_mb'] = int(match.group(1)) // 1024
                else:
                    info['total_ram_mb'] = 0
                
                # Parse MemAvailable
                match = re.search(r'MemAvailable:\s+(\d+)\s+kB', meminfo)
                if match:
                    info['available_ram_mb'] = int(match.group(1)) // 1024
                else:
                    info['available_ram_mb'] = 0
            else:
                info['total_ram_mb'] = 0
                info['available_ram_mb'] = 0
            
            # Get Storage info
            result = subprocess.run(
                ['adb'] + device_arg + ['shell', 'df', '/data'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        # parts[1] = total, parts[3] = available (in KB typically)
                        try:
                            total_kb = int(parts[1])
                            avail_kb = int(parts[3])
                            info['total_storage_mb'] = total_kb // 1024
                            info['available_storage_mb'] = avail_kb // 1024
                        except (ValueError, IndexError, KeyError):
                            info['total_storage_mb'] = 0
                            info['available_storage_mb'] = 0
                    else:
                        info['total_storage_mb'] = 0
                        info['available_storage_mb'] = 0
                else:
                    info['total_storage_mb'] = 0
                    info['available_storage_mb'] = 0
            else:
                info['total_storage_mb'] = 0
                info['available_storage_mb'] = 0
            
            return info
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi get_device_info: {e}", force=True)
            return {
                'brand': 'Unknown',
                'model': 'Unknown',
                'android_version': 'Unknown',
                'cpu': 'Unknown',
                'total_ram_mb': 0,
                'available_ram_mb': 0,
                'total_storage_mb': 0,
                'available_storage_mb': 0
            }
    
    @staticmethod
    def format_device_info(info: Dict) -> str:
        """
        Format device info v1.4.3 ULTIMATE - Beautiful colors
        """
        # Calculate RAM percentage
        ram_used_pct = ((info['total_ram_mb'] - info['available_ram_mb']) / info['total_ram_mb'] * 100) if info['total_ram_mb'] > 0 else 0
        
        # Calculate Storage percentage  
        storage_used_pct = ((info['total_storage_mb'] - info['available_storage_mb']) / info['total_storage_mb'] * 100) if info['total_storage_mb'] > 0 else 0
        
        # Color coding for percentages
        ram_color = "bright_green" if ram_used_pct < 70 else ("bright_yellow" if ram_used_pct < 85 else "bright_red")
        storage_color = "bright_green" if storage_used_pct < 70 else ("bright_yellow" if storage_used_pct < 85 else "bright_red")
        
        lines = [
            f"[bold bright_cyan]📱 Brand:[/bold bright_cyan] [bright_white]{info['brand']}[/bright_white]",
            f"[bold bright_cyan]📱 Model:[/bold bright_cyan] [bright_white]{info['model']}[/bright_white]",
            f"[bold bright_cyan]🤖 Android:[/bold bright_cyan] [bright_white]{info['android_version']}[/bright_white]",
            f"[bold bright_cyan]💻 CPU:[/bold bright_cyan] [bright_white]{info['cpu']}[/bright_white]",
            f"[bold bright_cyan]🎯 RAM:[/bold bright_cyan] [{ram_color}]{info['available_ram_mb']:,} MB[/{ram_color}] [dim]/[/dim] [bright_white]{info['total_ram_mb']:,} MB[/bright_white] [dim]({100-ram_used_pct:.0f}% free)[/dim]",
            f"[bold bright_cyan]💾 Storage:[/bold bright_cyan] [{storage_color}]{info['available_storage_mb']:,} MB[/{storage_color}] [dim]/[/dim] [bright_white]{info['total_storage_mb']:,} MB[/bright_white] [dim]({100-storage_used_pct:.0f}% free)[/dim]"
        ]
        return "\n".join(lines)
