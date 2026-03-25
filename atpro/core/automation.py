"""
╔══════════════════════════════════════════════════════╗
║         core/automation.py - v1.4.5                  ║
║   TikTokAutomation - Điều khiển TikTok trên device  ║
╚══════════════════════════════════════════════════════╝
"""

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None
import random
import time
from typing import List, Optional, Tuple

from typing import TYPE_CHECKING
from core.config import Config
from utils.ui_helper import UIHelper
from utils.xml_parser import XMLParser
try:
    from rich.console import Console as _Console
    if "console" not in dir():
        console = _Console()
except ImportError:
    pass

def _log(msg, force=False):
    """Helper để log qua smart_logger nếu có"""
    try:
        from ui.logger import smart_logger
        smart_logger.log(msg, force=force)
    except Exception:
        if force:
            print(f"  {msg}")

from ui.logger import smart_logger  # noqa: E402

class TikTokAutomation:
    """TikTok Automation v1.4.3 - Rest mode + Smart popup scan"""
    
    def __init__(self, device: "u2.Device", config: Config):
        self.device = device
        self.config = config
        self.screen_width, self.screen_height = UIHelper.get_screen_size(device)
        self.in_profile_mode = False
    
    def detect_live(self, xml: str) -> bool:
        """Detect live"""
        xml_lower = xml.lower()
        for keyword in self.config.live_keywords:
            if keyword.lower() in xml_lower:
                return True
        return False
    
    def check_lost(self) -> bool:
        """Check lost"""
        try:
            xml = XMLParser.extract(self.device)
            
            if XMLParser.has_nav_bar(xml, self.config):
                return False
            
            return True
        except Exception:
            return False
    
    def handle_popup_x(self) -> bool:
        """Đóng popup có nút X"""
        try:
            xml = XMLParser.extract(self.device)
            
            if not XMLParser.is_real_popup(xml, self.screen_width, self.screen_height):
                return False
            
            x_button = XMLParser.find_close_x_button(xml, self.screen_width, self.screen_height)
            
            if x_button:
                x, y = x_button
                self.device.click(x, y)
                smart_logger.log(f"✅ Đóng popup", force=True)
                time.sleep(0.8)
                
                xml_after = XMLParser.extract(self.device)
                x_button_after = XMLParser.find_close_x_button(xml_after, self.screen_width, self.screen_height)
                
                if not x_button_after:
                    return True
                else:
                    self.device.click(x, y)
                    time.sleep(0.5)
                    return True
            
        except Exception as e:
            pass
        
        return False
    
    def handle_popup(self, force: bool = False) -> bool:
        """Handle popups"""
        try:
            if self.in_profile_mode and not force:
                return False
            
            # v1.3.5: Check 1234 popup trước
            if UIHelper.handle_1234_popup(self.device, self.config):
                return True
            
            xml = XMLParser.extract(self.device)
            
            if not XMLParser.is_real_popup(xml, self.screen_width, self.screen_height):
                return False
            
            if self.handle_popup_x():
                return True
            
            xml_lower = xml.lower()
            
            for keyword in self.config.close_popup_keywords:
                if keyword.lower() in xml_lower:
                    w, h = UIHelper.get_screen_size(self.device)
                    
                    self.device.click(w // 2, int(h * 0.6))
                    smart_logger.log(f"✅ Đóng popup", force=True)
                    time.sleep(0.5)
                    return True
        except Exception as e:
            pass
        
        return False
    
    def handle_profile_popup(self) -> bool:
        """
        v1.4.3: QUÉT POPUP KHI VÀO PROFILE - SMART
        
        Quét nhiều lần, đảm bảo không nhầm video thành popup
        """
        try:
            if not self.config.enable_profile_popup_scan:
                return False
            
            # Quét nhiều lần
            for scan_idx in range(self.config.profile_popup_max_scans):
                # v1.3.5: Check 1234 popup
                if UIHelper.handle_1234_popup(self.device, self.config):
                    return True
                
                xml = XMLParser.extract(self.device)
                
                # Nếu đã có nav bar -> Không còn popup
                if XMLParser.has_nav_bar(xml, self.config):
                    return False
                
                # Kiểm tra THẬT có popup không (không nhầm video)
                if not XMLParser.is_real_popup(xml, self.screen_width, self.screen_height):
                    # Không phải popup -> Dừng quét
                    return False
                
                # Thử đóng popup
                if self.handle_popup_x():
                    smart_logger.log(f"✅ Đã đóng popup profile (lần {scan_idx+1})", force=True)
                    time.sleep(0.5)
                    continue
                
                # Thử các keyword khác
                xml_lower = xml.lower()
                
                for keyword in self.config.close_popup_keywords:
                    if keyword.lower() in xml_lower:
                        w, h = UIHelper.get_screen_size(self.device)
                        
                        self.device.click(w // 2, int(h * 0.6))
                        smart_logger.log(f"✅ Đóng popup profile (lần {scan_idx+1})", force=True)
                        time.sleep(0.5)
                        break
                else:
                    # Không tìm thấy cách đóng -> Dừng
                    break
            
            return False
            
        except Exception as e:
            return False
    
    def handle_comprehensive_popup(self) -> bool:
        """
        v1.4.3 ENHANCED: Universal popup handler
        
        Handles ALL TikTok popups automatically:
        - App updates
        - Permissions
        - Surveys
        - Tutorials
        - Recommendations
        - Generic popups
        
        Returns:
            True if popup was detected and dismissed
        """
        try:
            xml = XMLParser.extract(self.device)
            popup_info = XMLParser.detect_any_popup(xml)
            
            if not popup_info['detected']:
                return False
            
            popup_type = popup_info['type']
            smart_logger.log(f"🔔 Detected {popup_type} popup", force=True)
            
            # If we have a dismiss button, click it
            if popup_info['dismiss_button']:
                x, y = popup_info['dismiss_button']
                self.device.click(x, y)
                smart_logger.log(f"✅ Dismissed {popup_type} popup", force=True)
                time.sleep(1.0)
                return True
            
            # Fallback strategies based on popup type
            if popup_type in ['app_update', 'permission', 'survey']:
                # Try pressing back
                self.device.press("back")
                smart_logger.log(f"✅ Dismissed {popup_type} popup (back)", force=True)
                time.sleep(0.5)
                return True
            
            # Generic fallback: click outside popup (bottom area)
            w, h = UIHelper.get_screen_size(self.device)
            self.device.click(w // 2, int(h * 0.05))  # Top area
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            return False
    
    def recover_to_feed(self) -> bool:
        """Chống lạc"""
        try:
            smart_logger.log("🔧 Khôi phục về feed...", force=True)
            
            self.in_profile_mode = False
            
            for i in range(self.config.max_back_attempts):
                self.device.press("back")
                time.sleep(self.config.back_delay)
                
                xml_check = XMLParser.extract(self.device)
                
                if XMLParser.has_nav_bar(xml_check, self.config):
                    smart_logger.log(f"✅ Đã về feed", force=True)
                    return True
            
            smart_logger.log("⚠️  Reset TikTok...", force=True)
            
            self.close_tiktok()
            time.sleep(2.0)
            
            if self.open_tiktok():
                time.sleep(5.0)
                self.wait_feed_load()
                smart_logger.log("✅ Đã reset TikTok", force=True)
                return True
            
            smart_logger.log("❌ Reset thất bại!", force=True)
            return False
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi khôi phục: {e}", force=True)
            return False
    
    def click_profile_button(self) -> bool:
        """Click profile VÀ quét popup"""
        try:
            self.handle_popup()
            
            if self.check_lost():
                if not self.recover_to_feed():
                    return False
            
            x = int(self.screen_width * 0.95)
            y = int(self.screen_height * 0.97)
            self.device.click(x, y)
            time.sleep(1.5)
            
            # v1.4.3: Quét popup thông minh
            popup_closed = self.handle_profile_popup()
            
            if popup_closed:
                time.sleep(1.0)
            
            xml = XMLParser.extract(self.device)
            if XMLParser.verify_profile_page(xml):
                self.in_profile_mode = True
                smart_logger.log("✅ Đã vào profile", force=True)
                return True
            
            return False
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi click profile: {e}", force=True)
            return False
    
    def open_account_switch_popup(self) -> bool:
        """Mở popup switch account"""
        try:
            all_y_positions = self.config.get_all_account_button_positions(self.screen_height)
            
            x = int(self.screen_width * 0.50)
            
            for idx, y_position in enumerate(all_y_positions, 1):
                self.device.click(x, y_position)
                time.sleep(random.uniform(1.5, 2.0))
                
                xml_check = XMLParser.extract(self.device)
                if XMLParser.verify_popup_open(xml_check):
                    smart_logger.log(f"✅ Popup đã mở (vị trí {idx})", force=True)
                    return True
            
            smart_logger.log("❌ Không mở được popup", force=True)
            return False
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi mở popup: {e}", force=True)
            return False
    
    def get_account_list(self) -> List[str]:
        """Lấy danh sách tài khoản"""
        try:
            xml = XMLParser.extract(self.device)
            accounts = XMLParser.parse_all_usernames(xml, self.screen_height, self.config)
            
            if not accounts:
                w, h = UIHelper.get_screen_size(self.device)
                self.device.swipe(w // 2, int(h * 0.4), w // 2, int(h * 0.2), duration=0.3)
                time.sleep(1.0)
                
                xml = XMLParser.extract(self.device)
                accounts = XMLParser.parse_all_usernames(xml, self.screen_height, self.config)
            
            return accounts
        except Exception as e:
            smart_logger.log(f"❌ Lỗi lấy list acc: {e}", force=True)
            return []
    
    def verify_current_account(self, expected_account: str) -> Tuple[bool, str]:
        """
        v1.3.5: XÁC MINH TÀI KHOẢN SAU KHI CHUYỂN
        
        Returns:
            (success, checkpoint_status)
        """
        try:
            if not self.config.enable_verify_account:
                return (True, "unknown")
            
            if not self.click_profile_button():
                smart_logger.log("⚠️  Không vào được profile để verify")
                return (False, "unknown")
            
            time.sleep(1.5)
            
            xml = XMLParser.extract(self.device)
            
            # v1.4.3: Check checkpoint
            checkpoint_status = "unknown"
            if self.config.enable_checkpoint_check:
                if XMLParser.detect_checkpoint(xml, self.config):
                    checkpoint_status = "checkpoint"
                    smart_logger.log(f"⚠️  ACCOUNT BỊ CHECKPOINT!", force=True)
                else:
                    checkpoint_status = "healthy"
            
            current_id = XMLParser.get_current_account_id(xml, self.screen_width, self.screen_height, self.config)
            
            # Thoát profile + về feed sau khi verify
            self.in_profile_mode = False
            from utils.ui_helper import UIHelper
            UIHelper.safe_back_to_feed(self.device, max_attempts=2, delay=1.0)
            
            if not current_id:
                smart_logger.log("⚠️  Không đọc được @id hiện tại")
                return (False, checkpoint_status)
            
            expected_clean = expected_account.lower().strip()
            if expected_clean.startswith('@'):
                expected_clean = expected_clean[1:]
            
            current_clean = current_id.lower().strip()
            
            if current_clean == expected_clean:
                smart_logger.log(f"✅ Verify OK: @{current_id}", force=True)
                return (True, checkpoint_status)
            else:
                smart_logger.log(f"❌ Verify FAIL: Mong muốn @{expected_clean}, thực tế @{current_id}", force=True)
                return (False, checkpoint_status)
            
        except Exception as e:
            smart_logger.log(f"Lỗi verify account: {e}")
            return (False, "unknown")
    
    def switch_to_account(self, account_name: str) -> Tuple[bool, str]:
        """
        v1.4.3: SWITCH ACCOUNT VỚI VERIFY + CHECKPOINT
        
        Returns:
            (success, checkpoint_status)
        """
        try:
            smart_logger.log(f"🔄 Chuyển sang: {account_name}", force=True)
            
            xml = XMLParser.extract(self.device)
            
            account_pos = XMLParser.find_account_by_name(
                xml, account_name,
                self.screen_width, self.screen_height,
                self.config
            )
            
            if not account_pos:
                smart_logger.log(f"❌ Không tìm thấy: {account_name}", force=True)
                
                w, h = UIHelper.get_screen_size(self.device)
                self.device.click(w // 2, h // 2)
                time.sleep(self.config.account_switch_verify_delay)
                return (False, "unknown")
            
            x, y = account_pos
            self.device.click(x, y)
            
            time.sleep(self.config.delay_after_switch_click)
            
            self.handle_popup(force=True)
            
            time.sleep(self.config.delay_before_reopen)
            
            package = self.config.get_tiktok_package()
            self.device.app_start(package)
            
            time.sleep(5.0)
            
            self.wait_feed_load()
            
            # v1.4.3: Verify account + check checkpoint
            if self.config.enable_verify_account:
                verify_ok, checkpoint_status = self.verify_current_account(account_name)
                
                if verify_ok:
                    smart_logger.log(f"✅ Đã chuyển và verify: {account_name}", force=True)
                    return (True, checkpoint_status)
                else:
                    smart_logger.log(f"❌ Chuyển thành công nhưng verify FAIL: {account_name}", force=True)
                    return (False, checkpoint_status)
            else:
                smart_logger.log(f"✅ Đã chuyển: {account_name}", force=True)
                return (True, "unknown")
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi switch account: {e}", force=True)
            return (False, "unknown")
    
    def exit_profile_mode(self):
        """Thoát profile mode"""
        self.in_profile_mode = False
    
    def open_tiktok(self) -> bool:
        """Open TikTok"""
        package = self.config.get_tiktok_package()
        try:
            self.device.app_start(package)
            time.sleep(2)
            return True
        except Exception:
            return False
    
    def wait_feed_load(self) -> bool:
        """Wait feed"""
        self.in_profile_mode = False
        
        for i in range(4):
            time.sleep(3.0)
            xml = XMLParser.extract(self.device)
            if XMLParser.has_nav_bar(xml, self.config):
                smart_logger.log("✅ Feed đã load", force=True)
                return True
        
        return False
    
    def close_tiktok(self):
        """Close TikTok"""
        package = self.config.get_tiktok_package()
        try:
            self.device.app_stop(package)
        except Exception:
            pass
        
        self.in_profile_mode = False
    
    def rest_between_accounts(self, rest_minutes: int):
        """
        v1.4.3: NGHỈ GIỮA CÁC ACCOUNT
        
        Tắt app TikTok và chờ
        """
        try:
            smart_logger.log(f"😴 Nghỉ {rest_minutes} phút...", force=True)
            
            self.close_tiktok()
            
            rest_seconds = rest_minutes * 60
            
            # Hiển thị countdown
            for remaining in range(rest_seconds, 0, -1):
                mins = remaining // 60
                secs = remaining % 60
                
                if remaining % 10 == 0:  # Log mỗi 10 giây
                    console.print(f"[dim]💤 Còn {mins}m{secs:02d}s...[/dim]")
                
                time.sleep(1)
            
            smart_logger.log("✅ Đã nghỉ xong", force=True)
            
            # Mở lại TikTok
            if self.open_tiktok():
                time.sleep(5.0)
                self.wait_feed_load()
                return True
            
            return False
            
        except Exception as e:
            smart_logger.log(f"Lỗi rest: {e}")
            return False
# ══════════════════════════════════════════════════════════════════
# END OF PART 6/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║               PART 7/8 - STATISTICS UI                         ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# STATISTICS UI v1.4.3 - KHÔNG TRÙNG LẶP, ĐẸP MẮT HƠN
# ═══════════════════════════════════════════════════════════════
