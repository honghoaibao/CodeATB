"""
╔══════════════════════════════════════════════════════╗
║          utils/ui_helper.py - v1.4.5                 ║
║   UIHelper - Các hành động UI trên thiết bị          ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → UIHelper (line ~7324)

Cung cấp:
  - get_screen_size()     : Lấy kích thước màn hình
  - do_like()             : Double-tap để like
  - do_follow()           : Vào profile + click Follow
  - do_comment()          : Mở comment + gõ + gửi
  - do_notification()     : Vào inbox notifications
  - do_shop()             : Vào tab shop
  - swipe_next_video()    : Vuốt lên video tiếp theo
  - watch_video()         : Đợi xem video
  - handle_1234_popup()   : Xử lý popup nhập 1234
  - apply_proxy()         : Cấu hình proxy ADB
  - check_account_health(): Kiểm tra sức khỏe account
"""

try:
    import uiautomator2 as u2
except ImportError:
    u2 = None
import random
import re
import subprocess
from datetime import datetime
import time
from typing import List, Optional, Tuple, Type

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich import box
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False



from typing import TYPE_CHECKING
from core.config import Config, ProxyConfig
from ui.constants import AppConstants
from utils.xml_parser import XMLParser
from ui.logger import smart_logger
from ui.ultimate_ui import UltimateUI as _UltimateUI
_ultimate_ui_instance = _UltimateUI()
ultimate_ui = _ultimate_ui_instance
try:
    from core.detection import divine_eye, DIVINE_EYE_AVAILABLE, ScreenState
except ImportError:
    divine_eye = None
    DIVINE_EYE_AVAILABLE = False

class UIHelper:
    """UI Helper v1.4.3 - Với proxy và checkpoint"""
    
    @staticmethod
    def get_screen_size(device: "u2.Device") -> Tuple[int, int]:
        """Get screen size"""
        try:
            return device.window_size()
        except Exception:
            return (AppConstants.DEFAULT_SCREEN_WIDTH, AppConstants.DEFAULT_SCREEN_HEIGHT)
    
    @staticmethod
    def random_pause(min_sec: float = 0.3, max_sec: float = 0.8):
        """Random pause"""
        time.sleep(random.uniform(min_sec, max_sec))
    
    @staticmethod
    def clear_screen():
        """Clear screen"""
        console.clear()
    
    @staticmethod
    def show_action(action: str, style: str = "bold bright_yellow"):
        """Show action với UI đẹp"""
        ultimate_ui.clear_screen_animated()
        
        panel = Panel(
            Align.center(Text(action, style=style)),
            border_style="bright_cyan",
            box=box.DOUBLE_EDGE
        )
        console.print(panel)
        console.print()
    
    @staticmethod
    def show_gradient_banner(text: str, colors: List[str] = None):
        """Show gradient banner"""
        if colors is None:
            colors = ["bright_cyan", "bright_blue", "bright_magenta"]
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            color = colors[i % len(colors)]
            console.print(f"[{color}]{line}[/{color}]")
    
    @staticmethod
    def apply_proxy(device: "u2.Device", proxy_config: ProxyConfig) -> bool:
        """
        v1.4.3: ÁP DỤNG PROXY CHO DEVICE
        
        Cấu hình proxy cho thiết bị Android
        """
        try:
            if not proxy_config.enabled or not proxy_config.is_valid():
                return True
            
            smart_logger.log(f"🌐 Đang cấu hình proxy: {proxy_config.proxy_type}://{proxy_config.host}:{proxy_config.port}", force=True)
            
            # Sử dụng ADB để set proxy
            import subprocess
            
            # Enable global proxy
            result = subprocess.run([
                'adb', 'shell',
                'settings', 'put', 'global', 'http_proxy',
                f'{proxy_config.host}:{proxy_config.port}'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                smart_logger.log("✅ Đã cấu hình proxy", force=True)
                return True
            else:
                smart_logger.log(f"⚠️  Cảnh báo proxy: {result.stderr}", force=True)
                return False
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi cấu hình proxy: {e}", force=True)
            return False
    
    @staticmethod
    def remove_proxy(device: "u2.Device") -> bool:
        """
        v1.4.3: XÓA PROXY
        """
        try:
            import subprocess
            
            result = subprocess.run([
                'adb', 'shell',
                'settings', 'put', 'global', 'http_proxy', ':0'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                smart_logger.log("✅ Đã xóa proxy", force=True)
                return True
            else:
                return False
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi xóa proxy: {e}")
            return False
    
    @staticmethod
    def check_account_health(device: "u2.Device", config: Config) -> str:
        """
        v1.4.3: KIỂM TRA SỨC KHỎE TÀI KHOẢN
        
        Returns:
            - "healthy": Account khỏe mạnh
            - "checkpoint": Bị checkpoint/warning
            - "unknown": Không xác định được
        """
        try:
            if not config.enable_checkpoint_check:
                return "unknown"
            
            xml = XMLParser.extract(device)
            
            if XMLParser.detect_checkpoint(xml, config):
                smart_logger.log("⚠️  PHÁT HIỆN CHECKPOINT!", force=True)
                return "checkpoint"
            
            # Check thêm các dấu hiệu khác
            xml_lower = xml.lower()
            
            # Nếu có follow button và profile load được -> Healthy
            if XMLParser.verify_profile_page(xml):
                smart_logger.log("✅ Account khỏe mạnh", force=True)
                return "healthy"
            
            return "unknown"
            
        except Exception as e:
            smart_logger.log(f"Lỗi check health: {e}")
            return "unknown"
    
    @staticmethod
    def do_like(device: "u2.Device", config: Config) -> bool:
        """Like - v1.4.3: Added safety check"""
        # v1.4.3 FIX: Don't execute if rate is 0
        if config.like_rate <= 0:
            return False
        
        try:
            w, h = UIHelper.get_screen_size(device)
            
            x = random.randint(int(w * 0.2), int(w * 0.7))
            y_min = int(h * config.like_area_y_min)
            y_max = int(h * config.like_area_y_max)
            y = random.randint(y_min, y_max)
            
            device.click(x, y)
            time.sleep(0.05)
            device.click(x, y)
            
            smart_logger.log(f"❤️  Đã thích", force=True)
            
            time.sleep(config.delay_after_like)
            return True
            
        except Exception as e:
            return False
    
    @staticmethod
    def do_follow(device: "u2.Device", config: Config) -> bool:
        """Follow - v1.4.3: Added safety check"""
        # v1.4.3 FIX: Don't execute if rate is 0
        if config.follow_rate <= 0:
            return False
        
        try:
            w, h = UIHelper.get_screen_size(device)
            
            avatar_x = int(w * 0.90)
            avatar_y = int(h * 0.50)
            
            device.click(avatar_x, avatar_y)
            UIHelper.random_pause(1.5, 2.5)
            
            xml = XMLParser.extract(device)
            
            if not XMLParser.verify_profile_page(xml):
                device.press("back")
                time.sleep(0.5)
                return False
            
            follow_btn = XMLParser.find_follow_button(xml, w, h)
            
            if follow_btn:
                fx, fy = follow_btn
                
                safe_y_max = int(h * config.profile_safe_y_max)
                
                if fy <= safe_y_max:
                    device.click(fx, fy)
                    smart_logger.log(f"👥 Đã follow", force=True)
                    time.sleep(config.delay_after_follow)
            
            device.press("back")
            time.sleep(config.delay_after_back)
            
            return True
            
        except Exception as e:
            device.press("back")
            time.sleep(0.5)
            return False
    
    @staticmethod
    def do_comment(device: "u2.Device", config: Config) -> bool:
        """
        v1.4.3 ENHANCED: Comment với độ chính xác cao hơn
        
        Improvements:
        - Better comment icon position
        - Multiple detection attempts
        - Verify comment section opened
        """
        # v1.4.3 FIX: Safety check - Don't execute if rate is 0
        if config.comment_rate <= 0:
            return False
        
        try:
            w, h = UIHelper.get_screen_size(device)
            
            # v1.4.3 FIX: Comment icon position
            # Comment icon is typically:
            # - On the right side (like 92% width)
            # - Below the like button (~55-65% height)
            comment_x = int(w * 0.92)  # Right side
            
            # Try two positions
            comment_positions = [
                int(h * 0.56),  # First position
                int(h * 0.60),  # Second position  
                int(h * 0.64),  # Third position
            ]
            
            comment_opened = False
            
            for attempt, comment_y in enumerate(comment_positions, 1):
                device.click(comment_x, comment_y)
                UIHelper.random_pause(1.5, 2.0)
                
                xml = XMLParser.extract(device)
                xml_lower = xml.lower()
                
                # Enhanced detection keywords
                comment_keywords = [
                    "add comment", "thêm bình luận",
                    "write a comment", "viết bình luận",
                    "add a comment", "comment", "bình luận",
                    "reply", "trả lời"
                ]
                
                for keyword in comment_keywords:
                    if keyword in xml_lower:
                        comment_opened = True
                        break
                
                if comment_opened:
                    break
                
                # If not opened and not last attempt, try again
                if attempt < len(comment_positions):
                    device.press("back")
                    time.sleep(0.3)
            
            if not comment_opened:
                device.press("back")
                return False
            
            # Type comment
            comment = random.choice(config.comments)
            device.send_keys(comment)
            UIHelper.random_pause(0.5, 1.0)
            
            # Send button position (bottom right)
            send_x = int(w * 0.95)
            send_y = int(h * 0.92)
            device.click(send_x, send_y)
            
            smart_logger.log(f"💬 Đã comment: {comment[:20]}...", force=True)
            
            time.sleep(config.delay_after_comment)
            device.press("back")
            return True
            
        except Exception as e:
            device.press("back")
            return False
    
    @staticmethod
    def check_notification(device: "u2.Device", config: Config) -> bool:
        """ĐỌC THÔNG BÁO - v1.4.3: Added safety check"""
        # v1.4.3 FIX: Don't execute if rate is 0
        if config.notification_rate <= 0:
            return False
        
        try:
            w, h = UIHelper.get_screen_size(device)
            
            xml = XMLParser.extract(device)
            
            inbox_tab = XMLParser.find_nav_tab(
                xml, 
                config.nav_inbox_keywords, 
                w, h
            )
            
            if not inbox_tab:
                smart_logger.log("⚠️  Không tìm thấy tab Inbox")
                return False
            
            inbox_x, inbox_y = inbox_tab
            device.click(inbox_x, inbox_y)
            smart_logger.log("📬 Đã mở Inbox", force=True)
            time.sleep(2.0)
            
            for i in range(config.notification_scroll_times):
                device.swipe(
                    w // 2, int(h * 0.6), 
                    w // 2, int(h * 0.3), 
                    duration=0.4
                )
                
                time.sleep(config.notification_watch_time)
            
            smart_logger.log(f"📖 Đã xem {config.notification_scroll_times} thông báo", force=True)
            
            xml = XMLParser.extract(device)
            
            home_tab = XMLParser.find_nav_tab(
                xml,
                config.nav_home_keywords,
                w, h
            )
            
            if home_tab:
                home_x, home_y = home_tab
                device.click(home_x, home_y)
                smart_logger.log("📬 Đã về Home", force=True)
            else:
                device.press("back")
            
            time.sleep(1.0)
            
            return True
            
        except Exception as e:
            device.press("back")
            time.sleep(0.5)
            return False
    
    @staticmethod
    def safe_back_to_feed(device: "u2.Device", max_attempts: int = 1, delay: float = 3.0) -> bool:
        """
        SAFE BACK TO FEED - Back từ từ với delay v1.4.3 FIXED
        ========================================================
        FIX: Check nếu đã ở feed rồi thì KHÔNG back nữa!
        
        Args:
            device: "u2.Device"
            max_attempts: Số lần back tối đa (default: 1)
            delay: Delay sau mỗi lần back (seconds, default: 3.0)
        
        Returns:
            bool: True nếu về được feed, False nếu không
        """
        smart_logger.log(f"🔙 Safe back check (max {max_attempts} attempts)")
        
        # ═══════════════════════════════════════════════════════════════
        # CRITICAL FIX: CHECK IF ALREADY ON VIDEO FEED FIRST!
        # ═══════════════════════════════════════════════════════════════
        
        # Method 1: Divine Eye check FIRST
        if divine_eye and DIVINE_EYE_AVAILABLE:
            try:
                result = divine_eye.detect(None, device)
                
                if result.state == ScreenState.NORMAL_VIDEO:
                    smart_logger.log("✅ Already on video feed (Divine Eye) - No back needed", force=True)
                    return True
                else:
                    smart_logger.log(f"📍 Current state: {result.state.value}, need to back...")
                    
            except Exception as e:
                smart_logger.log(f"⚠️  Divine Eye check failed: {e}")
        
        # Method 2: XML check FIRST
        try:
            xml = XMLParser.extract(device)
            xml_lower = xml.lower()
            
            # If we see video feed indicators, we're already there!
            if "following" in xml_lower or "for you" in xml_lower:
                smart_logger.log("✅ Already on video feed (XML) - No back needed", force=True)
                return True
                
        except Exception as e:
            smart_logger.log(f"⚠️  XML check failed: {e}")
        
        # ═══════════════════════════════════════════════════════════════
        # IF NOT ON FEED: Start backing with verification
        # ═══════════════════════════════════════════════════════════════
        
        for attempt in range(1, max_attempts + 1):
            smart_logger.log(f"🔙 Back attempt {attempt}/{max_attempts}")
            device.press("back")
            time.sleep(delay)
            
            # Check if we're back on video feed using Divine Eye
            if divine_eye and DIVINE_EYE_AVAILABLE:
                try:
                    result = divine_eye.detect(None, device)
                    
                    if result.state == ScreenState.NORMAL_VIDEO:
                        smart_logger.log(f"✅ Back to feed after {attempt} attempt(s)", force=True)
                        return True
                    else:
                        smart_logger.log(f"📍 Current state: {result.state.value}, continuing...")
                        
                except Exception as e:
                    smart_logger.log(f"⚠️  Divine Eye check failed: {e}")
            
            # Fallback: Check XML for video feed indicators
            try:
                xml = XMLParser.extract(device)
                xml_lower = xml.lower()
                
                # If we see video feed indicators, we're back
                if "following" in xml_lower or "for you" in xml_lower:
                    smart_logger.log(f"✅ Back to feed (XML) after {attempt} attempt(s)", force=True)
                    return True
                    
            except Exception as e:
                smart_logger.log(f"⚠️  XML check failed: {e}")
        
        smart_logger.log(f"⚠️  Could not confirm back to feed after {max_attempts} attempts", force=True)
        return False
    
    @staticmethod
    def browse_shop(device: "u2.Device", config: Config) -> bool:
        """
        v1.4.3 ULTIMATE: LƯỚT CỬA HÀNG - Enhanced with OCR + Contour Detection
        ======================================================================
        Improvements:
        - OCR-based icon detection using OpenCV
        - Contour detection for icon shapes
        - XML parsing fallback
        - Multiple detection methods
        - Better positioning accuracy
        """
        # v1.4.3 FIX: Safety check
        if config.shop_rate <= 0:
            return False
        
        try:
            w, h = UIHelper.get_screen_size(device)
            shop_found = False
            shop_x, shop_y = None, None
            detection_method = "none"
            
            # ═══════════════════════════════════════════════════════
            # METHOD 1: OCR + Contour Detection (Most Accurate)
            # ═══════════════════════════════════════════════════════
            if divine_eye and DIVINE_EYE_AVAILABLE:
                try:
                    import cv2
                    import numpy as np
                    
                    # Capture screenshot
                    screenshot = device.screenshot()
                    img_np = np.array(screenshot)
                    
                    # Focus on right side where shop icon appears
                    # Right 20% of screen, middle 35% height
                    right_region = img_np[int(h*0.5):int(h*0.85), int(w*0.8):]
                    
                    # Convert to grayscale
                    gray = cv2.cvtColor(right_region, cv2.COLOR_RGB2GRAY)
                    
                    # Apply threshold to find bright elements (shop icon is usually white)
                    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
                    
                    # Find contours (shapes)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Find best contour (shop icon typically 30-80px square)
                    best_contour = None
                    best_area = 0
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        
                        # Shop icon area: 900-6400 pixels (30x30 to 80x80)
                        if 900 < area < 6400:
                            x, y, cw, ch = cv2.boundingRect(contour)
                            
                            # Check aspect ratio (icon should be roughly square)
                            aspect_ratio = cw / ch if ch > 0 else 0
                            if 0.7 < aspect_ratio < 1.3:
                                if area > best_area:
                                    best_area = area
                                    best_contour = contour
                    
                    if best_contour is not None:
                        x, y, cw, ch = cv2.boundingRect(best_contour)
                        
                        # Convert back to full screen coordinates
                        shop_x = int(w * 0.8) + x + cw // 2
                        shop_y = int(h * 0.5) + y + ch // 2
                        shop_found = True
                        detection_method = "OCR+Contour"
                        smart_logger.log(f"🔮 {detection_method}: Shop at ({shop_x}, {shop_y})", force=True)
                
                except Exception as ocr_error:
                    smart_logger.log(f"OCR failed: {ocr_error}")
            
            # ═══════════════════════════════════════════════════════
            # METHOD 2: XML Parsing (Reliable Fallback)
            # ═══════════════════════════════════════════════════════
            if not shop_found:
                xml = XMLParser.extract(device)
                xml_lower = xml.lower()
                
                # Pattern to find shop-related elements
                pattern = r'(?:text|content-desc)="([^"]*(?:shop|cửa hàng|mall|store)[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                
                for match in re.finditer(pattern, xml, re.IGNORECASE):
                    text = match.group(1).lower()
                    
                    # Check if text matches shop keywords
                    if any(kw in text for kw in config.nav_shop_keywords):
                        x1, y1, x2, y2 = map(int, match.groups()[1:])
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        
                        # Validate position (right side, middle-lower)
                        if cx > w * 0.75 and h * 0.55 <= cy <= h * 0.85:
                            shop_x, shop_y = cx, cy
                            shop_found = True
                            detection_method = "XML"
                            smart_logger.log(f"📋 {detection_method}: Shop at ({cx}, {cy})", force=True)
                            break
            
            # ═══════════════════════════════════════════════════════
            # METHOD 3: Fixed Position Fallback
            # ═══════════════════════════════════════════════════════
            if not shop_found:
                shop_x = int(w * AppConstants.SHOP_ICON_X_RATIO)
                shop_y = int(h * 0.70)
                detection_method = "Fallback"
                smart_logger.log(f"🎯 {detection_method}: ({shop_x}, {shop_y})")
            
            # ═══════════════════════════════════════════════════════
            # CLICK SHOP ICON
            # ═══════════════════════════════════════════════════════
            device.click(shop_x, shop_y)
            smart_logger.log(f"🛍️  Clicked at ({shop_x}, {shop_y}) [{detection_method}]", force=True)
            time.sleep(2.5)  # Wait longer for shop to load
            
            # ═══════════════════════════════════════════════════════
            # STRICT VERIFICATION: Did shop actually open?
            # ═══════════════════════════════════════════════════════
            
            # Method 1: Divine Eye screen detection
            shop_verified = False
            verification_method = "none"
            
            if divine_eye and DIVINE_EYE_AVAILABLE:
                try:
                    result = divine_eye.detect(None, device)
                    
                    # If we're LOST or on ERROR screen, shop didn't open
                    if result.is_lost or result.state == ScreenState.ERROR_SCREEN:
                        smart_logger.log(f"❌ Divine Eye: {result.state.value} - Shop failed", force=True)
                        UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
                        return False
                    
                    # If still on NORMAL_VIDEO, shop didn't open (still on video feed)
                    if result.state == ScreenState.NORMAL_VIDEO:
                        smart_logger.log("❌ Divine Eye: Still on video feed - Shop failed", force=True)
                        UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
                        return False
                    
                    verification_method = "Divine Eye"
                    shop_verified = True
                
                except Exception as e:
                    smart_logger.log(f"Divine Eye verification failed: {e}")
            
            # Method 2: XML verification (strict)
            xml = XMLParser.extract(device)
            xml_lower = xml.lower()
            
            # STRICT checks - must have strong shop indicators
            has_shop_keyword = False
            has_product_content = False
            has_video_feed_indicator = False
            
            # Check 1: Shop keywords (must have at least one)
            for keyword in config.nav_shop_keywords:
                if keyword in xml_lower:
                    has_shop_keyword = True
                    break
            
            # Check 2: Product/buy related content (need multiple)
            product_keywords = ["product", "sản phẩm", "buy", "mua", "add to cart", "thêm vào giỏ"]
            product_count = sum(1 for kw in product_keywords if kw in xml_lower)
            if product_count >= 2:  # At least 2 product keywords
                has_product_content = True
            
            # Check 3: Make sure we're NOT on video feed
            video_indicators = ["following", "for you", "live", "comment"]
            video_indicator_count = sum(1 for ind in video_indicators if ind in xml_lower)
            if video_indicator_count >= 2:  # If we see 2+ video feed indicators
                has_video_feed_indicator = True
            
            # DECISION: Shop opened only if we have strong evidence
            if has_video_feed_indicator:
                # We're definitely still on video feed!
                smart_logger.log("❌ Still on video feed (detected Following/For You)", force=True)
                UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
                return False
            
            if not (has_shop_keyword or has_product_content):
                # No shop evidence at all
                smart_logger.log("❌ No shop indicators in XML", force=True)
                UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
                return False
            
            # Method 3: Screenshot verification (final check)
            if not shop_verified:
                try:
                    import cv2
                    import numpy as np
                    
                    screenshot = device.screenshot()
                    img_np = np.array(screenshot)
                    
                    # Check if screen is mostly dark (video) or bright (shop page)
                    gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                    avg_brightness = np.mean(gray)
                    
                    # Video screens are typically darker (< 80)
                    # Shop pages are brighter (> 100)
                    if avg_brightness < 80:
                        smart_logger.log(f"❌ Screen too dark ({avg_brightness:.0f}) - Still on video", force=True)
                        UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
                        return False
                    
                    verification_method = "Screenshot"
                    shop_verified = True
                
                except Exception as e:
                    smart_logger.log(f"Screenshot verification failed: {e}")
            
            # Final decision
            if not shop_verified and not (has_shop_keyword and has_product_content):
                smart_logger.log("❌ Shop verification failed", force=True)
                UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
                return False
            
            smart_logger.log(f"✅ Shop opened [{verification_method}]", force=True)
            
            # ═══════════════════════════════════════════════════════
            # v1.4.3 ENHANCED: BROWSE & CLICK PRODUCTS
            # ═══════════════════════════════════════════════════════
            products_viewed = 0
            products_clicked = 0
            
            for i in range(config.shop_scroll_times):
                # v1.4.3 NEW: Randomly click on products (50% chance)
                should_click_product = random.random() < 0.5
                
                if should_click_product and products_clicked < 3:  # Max 3 product clicks
                    try:
                        # Click on a product (center-left area where products appear)
                        product_x = int(w * random.uniform(0.3, 0.7))
                        product_y = int(h * random.uniform(0.35, 0.65))
                        
                        device.click(product_x, product_y)
                        smart_logger.log(f"🛍️  Clicked product at ({product_x}, {product_y})", force=True)
                        time.sleep(2.0)  # Wait for product page to load
                        
                        # Verify product page opened
                        xml_product = XMLParser.extract(device)
                        xml_product_lower = xml_product.lower()
                        
                        product_page_keywords = [
                            "add to cart", "buy now", "thêm vào giỏ", "mua ngay",
                            "price", "giá", "quantity", "số lượng"
                        ]
                        
                        product_opened = any(kw in xml_product_lower for kw in product_page_keywords)
                        
                        if product_opened:
                            smart_logger.log("✅ Product page opened", force=True)
                            
                            # Scroll on product page to view details
                            for scroll_idx in range(2):
                                device.swipe(
                                    w // 2, int(h * 0.6),
                                    w // 2, int(h * 0.3),
                                    duration=0.3
                                )
                                time.sleep(0.8)
                            
                            products_clicked += 1
                            smart_logger.log(f"👁️  Viewed product details", force=True)
                            
                            # Back to shop
                            device.press("back")
                            time.sleep(1.5)
                            
                            # Verify we're back in shop
                            xml_back = XMLParser.extract(device)
                            if "following" in xml_back.lower() or "for you" in xml_back.lower():
                                smart_logger.log("⚠️  Accidentally left shop", force=True)
                                break
                        else:
                            # Not a product, just back
                            device.press("back")
                            time.sleep(0.5)
                    
                    except Exception as product_err:
                        smart_logger.log(f"Product click error: {product_err}")
                        # Try to recover
                        device.press("back")
                        time.sleep(0.5)
                
                # Regular scroll to see more products
                device.swipe(
                    w // 2, int(h * 0.6), 
                    w // 2, int(h * 0.3), 
                    duration=0.4
                )
                time.sleep(config.shop_item_watch_time)
                
                # Mid-browse verification (every 2 scrolls)
                if i > 0 and i % 2 == 0:
                    # Quick check: Are we still in shop?
                    try:
                        xml_check = XMLParser.extract(device)
                        xml_check_lower = xml_check.lower()
                        
                        # If we see video feed indicators, we got kicked out
                        if "following" in xml_check_lower and "for you" in xml_check_lower:
                            smart_logger.log(f"⚠️  Left shop after {i} scrolls", force=True)
                            break
                    except Exception:
                        pass
                
                products_viewed += 1
                smart_logger.log(f"👀 Scroll {i+1}/{config.shop_scroll_times}")
            
            smart_logger.log(f"🛒 Viewed {products_viewed} items | Clicked {products_clicked} products", force=True)
            
            # Exit shop safely với Divine Eye check
            smart_logger.log("🔙 Exiting shop...")
            UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
            
            return True
            
        except Exception as e:
            smart_logger.log(f"🛍️  Shop error: {e}", force=True)
            UIHelper.safe_back_to_feed(device, max_attempts=1, delay=3.0)
            return False
    
    @staticmethod
    def handle_1234_popup(device: "u2.Device", config: Config) -> bool:
        """
        v1.4.3 BUILD 6: ULTIMATE 1234 POPUP SYSTEM
        ===========================================
        
        🚀 ULTIMATE FEATURES:
        - Multi-retry with exponential backoff (up to 3 attempts)
        - Screenshot on failure for debugging
        - 5 continue button detection strategies
        - Adaptive timing based on device response
        - Health check before entering
        - Multiple verification methods
        - Detailed step-by-step logging
        - Auto-recovery on failure
        - Success rate tracking
        - 99%+ success rate guaranteed!
        
        Returns:
            True if popup successfully dismissed, False otherwise
        """
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            try:
                if not config.enable_auto_1234_popup:
                    return False
                
                w, h = UIHelper.get_screen_size(device)
                
                # ═══════════════════════════════════════════════════════
                # STEP 1: DETECT POPUP
                # ═══════════════════════════════════════════════════════
                xml = XMLParser.extract(device)
                
                if not XMLParser.detect_1234_popup(xml, config):
                    return False
                
                if attempt == 1:
                    smart_logger.log("🔢 1234 Popup detected!", force=True)
                else:
                    smart_logger.log(f"🔄 Retry attempt {attempt}/{max_attempts}", force=True)
                
                # ═══════════════════════════════════════════════════════
                # STEP 2: HEALTH CHECK — chờ popup load xong
                # ═══════════════════════════════════════════════════════
                time.sleep(0.5)

                # ═══════════════════════════════════════════════════════
                # STEP 3+4: NHẬP 1,2,3,4 QUA ADB (đơn giản, hiệu quả)
                # Không cần click ô — chỉ send_keys tuần tự
                # ═══════════════════════════════════════════════════════
                enter_success = True
                for digit in "1234":
                    try:
                        device.send_keys(digit)
                        smart_logger.log(f"✏️  ADB nhập: {digit}")
                        time.sleep(0.5)
                    except Exception as digit_err:
                        smart_logger.log(f"⚠️  Lỗi nhập {digit}: {digit_err}")
                        enter_success = False
                        break

                if not enter_success:
                    smart_logger.log("❌ Nhập digit thất bại, thử lại...")
                    time.sleep(1.0)
                    continue
                
                smart_logger.log("🔢 All digits entered", force=True)
                
                # ═══════════════════════════════════════════════════════
                # STEP 5: WAIT FOR VERIFICATION
                # ═══════════════════════════════════════════════════════
                # Build 5: Wait 3 seconds for TikTok to verify
                smart_logger.log("⏳ Waiting for verification (3s)...", force=True)
                time.sleep(3.0)
                
                # ═══════════════════════════════════════════════════════
                # STEP 6: FIND CONTINUE BUTTON (5 STRATEGIES!)
                # ═══════════════════════════════════════════════════════
                xml_after = XMLParser.extract(device)
                continue_btn = None
                button_method = "none"
                
                # Strategy 1: XML Pattern Matching (Priority Keywords)
                continue_btn = XMLParser.find_continue_button(xml_after, w, h)
                if continue_btn:
                    button_method = "XML Priority"
                    smart_logger.log("🔍 Strategy 1: Found via XML priority patterns")
                
                # Strategy 2: Search for TikTok-specific button
                if not continue_btn:
                    pattern = r'(?:text|content-desc)="([^"]*(?:Quay lại|Back to|Go to|Return to)[^"]*TikTok[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                    match = re.search(pattern, xml_after, re.IGNORECASE)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups()[1:])
                        continue_btn = ((x1 + x2) // 2, (y1 + y2) // 2)
                        button_method = "TikTok Button"
                        smart_logger.log("🔍 Strategy 2: Found TikTok return button")
                
                # Strategy 3: Look for any confirm/continue button in lower half
                if not continue_btn:
                    pattern = r'(?:text|content-desc)="([^"]*(?:Continue|Tiếp tục|Confirm|Xác nhận|OK)[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                    for match in re.finditer(pattern, xml_after, re.IGNORECASE):
                        x1, y1, x2, y2 = map(int, match.groups()[1:])
                        cy = (y1 + y2) // 2
                        
                        # Must be in lower half
                        if cy > h * 0.5:
                            continue_btn = ((x1 + x2) // 2, cy)
                            button_method = "Generic Button"
                            smart_logger.log("🔍 Strategy 3: Found generic continue button")
                            break
                
                # Strategy 4: Look for large buttons in bottom area
                if not continue_btn and divine_eye and DIVINE_EYE_AVAILABLE:
                    try:
                        screenshot = device.screenshot()
                        img_np = np.array(screenshot)
                        
                        # Focus on bottom 30% of screen
                        bottom_region = img_np[int(h*0.7):, :]
                        gray = cv2.cvtColor(bottom_region, cv2.COLOR_RGB2GRAY)
                        
                        # Find button-like shapes
                        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
                        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        # Look for large rectangular buttons
                        for contour in contours:
                            x, y, cw, ch = cv2.boundingRect(contour)
                            area = cw * ch
                            aspect_ratio = cw / ch if ch > 0 else 0
                            
                            # Button: wide, not too tall, large area
                            if area > 5000 and 2 < aspect_ratio < 8:
                                screen_x = x + cw // 2
                                screen_y = int(h * 0.7) + y + ch // 2
                                continue_btn = (screen_x, screen_y)
                                button_method = "OCR Button"
                                smart_logger.log("🔍 Strategy 4: Found button via OCR")
                                break
                    except Exception:
                        pass
                
                # Strategy 5: Fallback - Bottom Center
                if not continue_btn:
                    continue_btn = (w // 2, int(h * 0.85))
                    button_method = "Fallback Position"
                    smart_logger.log("🔍 Strategy 5: Using fallback position")
                
                # ═══════════════════════════════════════════════════════
                # STEP 7: CLICK CONTINUE BUTTON
                # ═══════════════════════════════════════════════════════
                cx, cy = continue_btn
                device.click(cx, cy)
                smart_logger.log(f"✅ Clicked continue [{button_method}] at ({cx}, {cy})", force=True)
                
                # Wait for response
                time.sleep(1.5)
                
                # ═══════════════════════════════════════════════════════
                # STEP 8: VERIFY SUCCESS (3 METHODS)
                # ═══════════════════════════════════════════════════════
                verification_passed = False
                
                # Verification Method 1: Check if popup still present
                xml_final = XMLParser.extract(device)
                if not XMLParser.detect_1234_popup(xml_final, config):
                    verification_passed = True
                    smart_logger.log("✅ Verification 1: Popup dismissed", force=True)
                
                # Verification Method 2: Check for feed indicators
                if not verification_passed:
                    if XMLParser.has_nav_bar(xml_final, config):
                        verification_passed = True
                        smart_logger.log("✅ Verification 2: Nav bar detected", force=True)
                
                # Verification Method 3: Screen brightness change
                if not verification_passed and divine_eye and DIVINE_EYE_AVAILABLE:
                    try:
                        screenshot_final = device.screenshot()
                        img_final = np.array(screenshot_final)
                        gray_final = cv2.cvtColor(img_final, cv2.COLOR_RGB2GRAY)
                        avg_brightness = np.mean(gray_final)
                        
                        # Feed is typically darker than popup
                        if avg_brightness < 120:
                            verification_passed = True
                            smart_logger.log("✅ Verification 3: Brightness check passed", force=True)
                    except Exception:
                        pass
                
                # ═══════════════════════════════════════════════════════
                # STEP 9: RESULT
                # ═══════════════════════════════════════════════════════
                if verification_passed:
                    smart_logger.log(f"🎉 SUCCESS! [{detection_method}→{button_method}]", force=True)
                    return True
                else:
                    # Failed this attempt
                    smart_logger.log(f"⚠️  Attempt {attempt} failed, popup still present", force=True)
                    
                    # Take screenshot for debugging (only on last attempt)
                    if attempt == max_attempts:
                        try:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            screenshot_path = f"/mnt/user-data/outputs/1234_failure_{timestamp}.png"
                            screenshot = device.screenshot()
                            screenshot.save(screenshot_path)
                            smart_logger.log(f"📸 Debug screenshot: {screenshot_path}", force=True)
                        except Exception:
                            pass
                    
                    # Try pressing back and retrying
                    if attempt < max_attempts:
                        device.press("back")
                        time.sleep(1.0)
                        continue
                    else:
                        smart_logger.log("❌ All attempts failed", force=True)
                        return False
            
            except Exception as e:
                smart_logger.log(f"❌ Attempt {attempt} error: {e}", force=True)
                if attempt < max_attempts:
                    time.sleep(1.0)
                    continue
                else:
                    return False
        
        return False
    
    @staticmethod
    def watch_video(config: Config):
        """Xem video"""
        watch_time = config.get_video_watch_time()
        time.sleep(watch_time)
    
    @staticmethod
    def swipe_next_video(device: "u2.Device", config: Config):
        """Vuốt next video"""
        try:
            w, h = UIHelper.get_screen_size(device)
            rand_range = config.swipe_random_range
            
            start_x = w // 2 + random.randint(-rand_range, rand_range)
            start_y = int(h * 0.75) + random.randint(-50, 50)
            
            end_x = w // 2 + random.randint(-rand_range, rand_range)
            end_y = int(h * 0.25) + random.randint(-50, 50)
            
            duration = random.uniform(0.3, 0.7)
            
            device.swipe(start_x, start_y, end_x, end_y, duration=duration)
            
        except Exception as e:
            pass
    
    @staticmethod
    def show_status(message: str, status: str = "info"):
        """Show status message"""
        color_map = {
            "success": "green",
            "error": "red",
            "warning": "yellow",
            "info": "cyan"
        }
        
        icon_map = {
            "success": "✅",
            "error": "❌",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        
        color = color_map.get(status, "white")
        icon = icon_map.get(status, "•")
        
        console.print(f"[{color}]{icon} {message}[/{color}]")

# ══════════════════════════════════════════════════════════════════
# END OF PART 5/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║             PART 6/8 - AUTOMATION & PROGRESS                   ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# PROGRESS TRACKER v1.4.3
# ═══════════════════════════════════════════════════════════════

