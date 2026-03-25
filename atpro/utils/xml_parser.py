"""
╔══════════════════════════════════════════════════════╗
║          utils/xml_parser.py - v1.4.5                ║
║   XMLParser (Part1 + Part2 merged)                   ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py:
  - XMLParser          (line ~6421) - Part 1
  - XMLParserContinued (line ~6920) - Part 2

Part 2 đã được merge vào XMLParser theo pattern gốc:
  for method_name in dir(XMLParserContinued): setattr(XMLParser, ...)
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from ui.logger import smart_logger


class XMLParser:
    """
    XML Parser v1.4.5 - Full feature

    Tất cả phương thức parse XML của TikTok:
    - extract()              : Lấy hierarchy XML
    - is_valid_tiktok_id()   : Validate TikTok username
    - parse_all_usernames()  : Lấy danh sách accounts từ XML
    - detect_checkpoint()    : Phát hiện checkpoint/ban
    - is_real_popup()        : Phân biệt popup thật vs video feed
    - find_close_x_button()  : Tìm nút X đóng popup
    - find_follow_button()   : Tìm nút Follow
    - detect_ads()           : Phát hiện quảng cáo
    - detect_1234_popup()    : Phát hiện popup nhập 1234
    - detect_any_popup()     : Phát hiện tất cả loại popup
    - find_account_by_name() : Tìm account trong popup list
    - find_nav_tab()         : Tìm tab navigation bar
    - get_current_account_id(): Lấy @username hiện tại
    """

    # ─────────────────────────────────────────────────────────────
    # Extract XML
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def extract(device) -> str:
        try:
            return device.dump_hierarchy()
        except Exception:
            try:
                return device.dump()
            except Exception:
                return ""

    # ─────────────────────────────────────────────────────────────
    # TikTok ID validation
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def has_accented_chars(text: str) -> bool:
        clean = text.replace("@", "").strip()
        for char in clean:
            if char in "._ " or char.isdigit():
                continue
            if char.isalpha():
                if unicodedata.category(char) in ("Mn", "Mc", "Me"):
                    return True
                if len(unicodedata.normalize("NFD", char)) > 1:
                    return True
                if not ("a" <= char <= "z" or "A" <= char <= "Z"):
                    return True
            else:
                return True
        return False

    @staticmethod
    def is_valid_tiktok_id(text: str, config) -> bool:
        if not text:
            return False
        clean = text[1:] if text.startswith("@") else text.strip()
        if len(clean) < 2 or len(clean) > 30:
            return False
        if XMLParser.has_accented_chars(clean):
            return False
        cl = clean.lower()
        for kw in config.get_all_blacklist_keywords():
            if kw in cl:
                return False
        if re.match(r"^\d+[\.,]?\d*[KMB\+]?$", clean, re.IGNORECASE):
            return False
        if re.match(r"^\d+:\d+", clean):
            return False
        if " " in clean:
            return False
        if not any(c.isalpha() or c.isdigit() for c in clean):
            return False
        if not re.match(r"^[a-zA-Z0-9._]+$", clean):
            return False
        return True

    @staticmethod
    def clean_tiktok_id(text: str) -> str:
        return text[1:] if text.startswith("@") else text.strip()

    # ─────────────────────────────────────────────────────────────
    # Popup state
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def verify_popup_open(xml: str) -> bool:
        xml_lower = xml.lower()
        signs = [
            "chuyển đổi tài khoản", "switch account",
            "thêm tài khoản", "add account",
            "quản lý tài khoản", "manage account",
        ]
        return any(s in xml_lower for s in signs)

    @staticmethod
    def parse_all_usernames(xml: str, screen_height: int, config) -> List[str]:
        """Parse tất cả usernames hợp lệ, bỏ qua status bar"""
        candidates: List[str] = []
        seen: set = set()
        try:
            popup_opened = XMLParser.verify_popup_open(xml)
            pattern = r'(?:text|content-desc)="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            status_bar_max_y = int(screen_height * 0.10)
            raw_items = []

            for m in re.finditer(pattern, xml, re.IGNORECASE):
                text = m.group(1).strip()
                if not text:
                    continue
                y1, y2 = int(m.group(3)), int(m.group(5))
                cy = (y1 + y2) // 2
                if cy < status_bar_max_y:
                    continue
                if not popup_opened:
                    y_min = int(screen_height * config.account_list_y_min)
                    y_max = int(screen_height * config.account_list_y_max)
                    if not (y_min <= cy <= y_max):
                        continue
                if XMLParser.is_valid_tiktok_id(text, config):
                    clean = XMLParser.clean_tiktok_id(text)
                    raw_items.append((cy, clean))

            raw_items.sort(key=lambda x: x[0])
            for _, acc in raw_items:
                if acc.lower() not in seen:
                    candidates.append(acc)
                    seen.add(acc.lower())
        except Exception:
            pass
        return candidates

    @staticmethod
    def detect_checkpoint(xml: str, config) -> bool:
        """
        v1.4.3: PHÁT HIỆN CHECKPOINT
        
        Kiểm tra xem account có bị checkpoint/warning/banned không
        """
        xml_lower = xml.lower()
        
        for keyword in config.checkpoint_keywords:
            if keyword.lower() in xml_lower:
                return True
        
        return False
    
    @staticmethod
    def is_real_popup(xml: str, screen_width: int, screen_height: int) -> bool:
        """
        v1.4.3: KIỂM TRA POPUP THẬT - NÂNG CẤP ĐỂ KHÔNG NHẦM VIDEO
        
        Cải tiến: Không nhầm video thành popup
        """
        try:
            xml_lower = xml.lower()
            
            # 1. Kiểm tra nút close
            has_close_button = False
            
            if re.search(r'text="[✕×X]"', xml):
                has_close_button = True
            
            if re.search(r'content-desc="[^"]*(?:close|dismiss|cancel)[^"]*"', xml, re.IGNORECASE):
                has_close_button = True
            
            if re.search(r'resource-id="[^"]*(?:close|dismiss|cancel)[^"]*"', xml, re.IGNORECASE):
                has_close_button = True
            
            # 2. Kiểm tra dialog container
            has_dialog_container = False
            
            dialog_indicators = [
                'class="android.widget.FrameLayout"[^>]*resource-id="[^"]*dialog',
                'class="android.widget.FrameLayout"[^>]*resource-id="[^"]*popup',
                'class="android.app.Dialog"',
                'class="androidx.appcompat.app.AlertDialog"',
            ]
            
            for pattern in dialog_indicators:
                if re.search(pattern, xml, re.IGNORECASE):
                    has_dialog_container = True
                    break
            
            # 3. Kiểm tra popup keywords
            popup_specific_keywords = [
                "allow access", "cho phép truy cập",
                "grant permission", "cấp quyền",
                "update available", "cập nhật mới",
                "new version", "phiên bản mới",
                "download", "tải xuống",
                "create account", "tạo tài khoản",
                "sign up now", "đăng ký ngay",
                "enable notifications", "bật thông báo",
                "turn on notifications", "mở thông báo",
                "get started", "bắt đầu",
                "skip tutorial", "bỏ qua hướng dẫn",
                "terms of service", "điều khoản dịch vụ",
                "privacy policy", "chính sách bảo mật",
                "agree and continue", "đồng ý và tiếp tục",
            ]
            
            has_popup_keyword = False
            for keyword in popup_specific_keywords:
                if keyword in xml_lower:
                    has_popup_keyword = True
                    break
            
            # 4. v1.4.3: KIỂM TRA KHÔNG PHẢI VIDEO FEED
            is_video_feed = False
            video_indicators = [
                "for you", "trang chủ", "foryou",
                "following", "đang theo dõi",
                # Thêm các dấu hiệu video
                "class=\"android.view.TextureView\"",
                "class=\"android.view.SurfaceView\"",
            ]
            
            video_count = 0
            for indicator in video_indicators:
                if indicator in xml_lower:
                    video_count += 1
            
            # Nếu có nhiều dấu hiệu video -> Không phải popup
            if video_count >= 2:
                is_video_feed = True
            
            # 5. Kiểm tra profile page
            is_profile_page = False
            profile_indicators = [
                "follower", "following", "đang theo dõi",
                "edit profile", "sửa hồ sơ",
            ]
            
            profile_count = 0
            for indicator in profile_indicators:
                if indicator in xml_lower:
                    profile_count += 1
            
            if profile_count >= 2:
                is_profile_page = True
            
            # 6. Logic quyết định
            # Nếu là video feed -> KHÔNG PHẢI POPUP
            if is_video_feed:
                return False
            
            # Nếu là profile hoặc feed khác
            if is_profile_page:
                # Phải có cả dialog container VÀ close button
                if has_dialog_container and has_close_button:
                    return True
                else:
                    return False
            
            # Trường hợp còn lại: Tính điểm
            signals = sum([
                has_close_button,
                has_dialog_container,
                has_popup_keyword
            ])
            
            # Cần ít nhất 2/3 signals
            is_popup = signals >= 2
            
            return is_popup
            
        except Exception as e:
            return False
    
    @staticmethod
    def find_close_x_button(xml: str, screen_width: int, screen_height: int) -> Optional[Tuple[int, int]]:
        """Tìm nút X đóng popup - chỉ khi có popup thật"""
        if not XMLParser.is_real_popup(xml, screen_width, screen_height):
            return None
        try:
            candidates = []
            for p, base_score in [
                (r'text="[✕×X]"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', 100),
                (r'content-desc="[^"]*(?:close|dismiss|cancel|exit)[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', 80),
                (r'resource-id="[^"]*(?:close|dismiss|cancel)[^"]*"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', 70),
            ]:
                for m in re.finditer(p, xml, re.IGNORECASE):
                    x1, y1, x2, y2 = map(int, m.groups()[-4:])
                    w, h = x2 - x1, y2 - y1
                    if 20 <= w <= 100 and 20 <= h <= 100:
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        score = base_score
                        if cx > screen_width * 0.7 and cy < screen_height * 0.3:
                            score += 50
                        elif cx < screen_width * 0.3 and cy < screen_height * 0.3:
                            score += 30
                        candidates.append((score, cx, cy))
            if not candidates:
                return None
            candidates.sort(key=lambda x: -x[0])
            return (candidates[0][1], candidates[0][2])
        except Exception:
            return None

    @staticmethod
    def detect_ads(xml: str, config) -> bool:
        xml_lower = xml.lower()
        ads_count = sum(1 for kw in config.ads_keywords if kw.lower() in xml_lower)
        ui_match  = any(kw.lower() in xml_lower for kw in config.ads_ui_keywords)
        return (ads_count >= 1 and ui_match) or ads_count >= 2

    @staticmethod
    def verify_profile_page(xml: str) -> bool:
        xml_lower = xml.lower()
        signs = ["follower", "following", "đang theo dõi", "edit profile", "sửa hồ sơ", "thích", "liked"]
        return sum(1 for s in signs if s in xml_lower) >= 2

    @staticmethod
    def find_follow_button(xml: str, screen_width: int, screen_height: int) -> Optional[Tuple[int, int]]:
        """
        TikTok 2026 — Tìm nút Follow trên video feed (RecyclerView layout).

        Thuật toán 3 tầng (ưu tiên cao → thấp):
        ─────────────────────────────────────────
        Tầng 1 — resource-id asv / atv (TikTok 2026 signature)
            TikTok dùng RecyclerView để hiển thị video. Side-action
            buttons (like, follow, comment, share) là TextView với
            resource-id kết thúc bằng:
              • "id/asv"  — bản quốc tế (com.zhiliaoapp.musically)
              • "id/atv"  — bản nội địa VN (com.ss.android.ugc.trill)
            Cây phân cấp rất sâu (20-30 cấp) nhưng resource-id không
            bị obfuscate → đây là phương pháp chính xác nhất.

        Tầng 2 — text / content-desc "Follow" (fallback text)
            Khi resource-id bị đổi tên, text vẫn ổn định.

        Tầng 3 — RecyclerView + bounds x > 74% width (fallback vị trí)
            Nút side-action luôn nằm ở cột phải (x1 > 800px Full HD).
            Chọn nút nằm ở ~40-60% chiều cao (vị trí nút Follow điển hình).
        ─────────────────────────────────────────
        """
        try:
            right_threshold = int(screen_width * 0.74)  # ~800px / Full HD

            # ── Tầng 1: resource-id asv / atv ───────────────────────
            # TikTok 2026: side-action container có id/asv hoặc id/atv
            # TextView con trong container đó là nút follow (có text)
            pattern_asvatv = (
                r'class="android\.widget\.TextView"[^>]*'
                r'resource-id="[^"]*:id/a[st]v"[^>]*'
                r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            )
            for m in re.finditer(pattern_asvatv, xml):
                x1, y1, x2, y2 = map(int, m.groups())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                if x1 >= right_threshold and screen_height * 0.30 <= cy <= screen_height * 0.70:
                    return (cx, cy)

            # ── Tầng 2: text / content-desc ─────────────────────────
            text_patterns = [
                r'text="(Follow|Theo dõi|\+\s*Follow|Follow back)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                r'content-desc="(Follow|Theo dõi|\+\s*Follow|Follow back)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            ]
            candidates = []
            for pattern in text_patterns:
                for m in re.finditer(pattern, xml, re.IGNORECASE):
                    x1, y1, x2, y2 = map(int, m.groups()[1:])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    if cy < screen_height * 0.08 or cy > screen_height * 0.70:
                        continue
                    candidates.append((abs(cx - screen_width // 2) + abs(cy - screen_height * 0.35), (cx, cy)))
            if candidates:
                return min(candidates)[1]

            # ── Tầng 3: RecyclerView + side bounds fallback ──────────
            if "androidx.recyclerview.widget.RecyclerView" in xml:
                pattern_side = (
                    r'class="android\.widget\.(?:TextView|ImageView)"[^>]*'
                    r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                )
                mid_y_lo, mid_y_hi = screen_height * 0.35, screen_height * 0.60
                for m in re.finditer(pattern_side, xml):
                    x1, y1, x2, y2 = map(int, m.groups())
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    if x1 >= right_threshold and mid_y_lo <= cy <= mid_y_hi:
                        return (cx, cy)

            return None
        except Exception:
            return None
    
    @staticmethod
    def detect_1234_popup(xml: str, config) -> bool:
        xml_lower = xml.lower()
        return any(kw in xml_lower for kw in config.popup_1234_keywords)

    @staticmethod
    def find_1234_input_field(xml: str, screen_width: int, screen_height: int) -> Optional[Tuple[int, int]]:
        """Tìm ô nhập liệu cho popup 1234"""
        pattern = r'class="android.widget.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
        center_x, center_y = screen_width // 2, screen_height // 2
        best = None
        min_dist = float("inf")
        for m in re.finditer(pattern, xml):
            x1, y1, x2, y2 = map(int, m.groups())
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            dist = abs(cx - center_x) + abs(cy - center_y)
            if dist < min_dist:
                min_dist = dist
                best = (cx, cy)
        return best

    @staticmethod
    def find_continue_button(xml: str, screen_width: int, screen_height: int) -> Optional[Tuple[int, int]]:
        """Tìm nút Continue / Quay lại TikTok (cho popup 1234)"""
        pattern = (
            r'(?:text|content-desc)="'
            r'(Tiếp tục|Continue|OK|Xác nhận|Confirm|Quay lại TikTok|Back to TikTok|Go to TikTok|Return to TikTok)'
            r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
        )
        candidates = []
        for m in re.finditer(pattern, xml, re.IGNORECASE):
            btn_text = m.group(1)
            x1, y1, x2, y2 = map(int, m.groups()[1:])
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            if cy <= screen_height * 0.5:
                continue
            priority = 10 if "tiktok" in btn_text.lower() or "quay lại" in btn_text.lower() else (
                5 if "continue" in btn_text.lower() or "tiếp tục" in btn_text.lower() else 1
            )
            candidates.append({"pos": (cx, cy), "priority": priority, "y": cy})
        if candidates:
            candidates.sort(key=lambda x: (-x["priority"], -x["y"]))
            return candidates[0]["pos"]
        return None

    @staticmethod
    def detect_any_popup(xml: str) -> Dict:
        """Phát hiện toàn diện các loại popup TikTok"""
        xml_lower = xml.lower()
        result: Dict = {"detected": False, "type": None, "dismiss_button": None}

        if not any(ind in xml_lower for ind in ["dialog", "popup", "modal", "alert", "bottom sheet", "overlay"]):
            return result

        def _find_dismiss(patterns_str: str) -> Optional[Tuple[int, int]]:
            m = re.search(patterns_str, xml, re.IGNORECASE)
            if m:
                x1, y1, x2, y2 = map(int, m.groups()[1:])
                return ((x1 + x2) // 2, (y1 + y2) // 2)
            return None

        # App Update
        if any(kw in xml_lower for kw in ["update available", "new version", "cập nhật", "phiên bản mới"]):
            result.update({"detected": True, "type": "app_update",
                "dismiss_button": _find_dismiss(
                    r'(?:text|content-desc)="(Later|Not now|Để sau|Skip|Bỏ qua)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                )})
            return result

        # Permission
        if any(kw in xml_lower for kw in ["allow", "permission", "cho phép", "quyền truy cập", "camera", "microphone"]):
            result.update({"detected": True, "type": "permission",
                "dismiss_button": _find_dismiss(
                    r'(?:text|content-desc)="(Deny|Don\'t allow|Not now|Từ chối|Không cho phép|Để sau)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                )})
            return result

        # Survey / Rating
        if any(kw in xml_lower for kw in ["rate", "review", "feedback", "survey", "đánh giá", "khảo sát"]):
            result.update({"detected": True, "type": "survey",
                "dismiss_button": _find_dismiss(
                    r'(?:text|content-desc)="(Close|Dismiss|No thanks|Not now|Đóng|Không|Để sau)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                )})
            return result

        # Tutorial / Feature intro
        if any(kw in xml_lower for kw in ["new feature", "tutorial", "tính năng mới", "hướng dẫn"]):
            result.update({"detected": True, "type": "tutorial",
                "dismiss_button": _find_dismiss(
                    r'(?:text|content-desc)="(Skip|Close|Got it|OK|Bỏ qua|Đóng|Đã hiểu)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
                )})
            return result

        # Generic close button
        m = re.search(
            r'(?:text|content-desc)="(Close|Dismiss|Cancel|X|Đóng|Hủy)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            xml, re.IGNORECASE
        )
        if m:
            x1, y1, x2, y2 = map(int, m.groups()[1:])
            result.update({"detected": True, "type": "generic",
                "dismiss_button": ((x1 + x2) // 2, (y1 + y2) // 2)})

        return result

    @staticmethod
    def has_nav_bar(xml: str, config) -> bool:
        """
        TikTok 2026 — Phát hiện đang ở feed (có thanh nav bar).

        Thuật toán RecyclerView 2026:
        ─────────────────────────────────────────────────────────────
        TikTok dùng RecyclerView để render video. Mỗi item video có
        các side-action buttons (like, comment, share, follow) nằm
        bên phải màn hình. Node mục tiêu là TextView với:
          • resource-id kết thúc bằng "id/asv" (bản quốc tế)
                                 hoặc "id/atv" (bản nội địa VN)
          • bounds: cột x > 800px (Full HD) — phía phải màn hình

        Phát hiện theo 3 tầng (ưu tiên cao → thấp):
          1. resource-id asv/atv  (chính xác nhất, không bị obfuscate)
          2. keyword nav_keywords trong XML                (nhanh)
          3. RecyclerView + side-action bounds x > 74% width (fallback)
        ─────────────────────────────────────────────────────────────
        """
        if not xml:
            return False

        # ── Tầng 1: resource-id asv / atv (TikTok 2026 signature) ──
        # Ví dụ: resource-id="com.zhiliaoapp.musically:id/asv"
        #        resource-id="com.ss.android.ugc.trill:id/atv"
        if re.search(r'resource-id="[^"]*:id/a[st]v"', xml):
            return True

        # ── Tầng 2: keyword-based (nav_keywords từ config) ──────────
        xml_lower = xml.lower()
        if any(kw.lower() in xml_lower for kw in config.nav_keywords):
            return True

        # ── Tầng 3: RecyclerView + side-action bounds fallback ───────
        # RecyclerView chứa video feed luôn có class này
        if "androidx.recyclerview.widget.RecyclerView" not in xml:
            return False
        # Tìm TextView/ImageView nằm ở cột phải (x1 > ~74% width = 800px)
        # → đây là nút like/comment/share/follow trên video
        right_threshold = 800  # ~74% của 1080px Full HD
        for m in re.finditer(
            r'class="android\.widget\.(?:TextView|ImageView)"'
            r'[^>]*bounds="\[(\d+),\d+\]\[\d+,\d+\]"',
            xml,
        ):
            if int(m.group(1)) >= right_threshold:
                return True

        return False

# ══════════════════════════════════════════════════════════════════
# END OF PART 3/8
# ══════════════════════════════════════════════════════════════════
    # ═══ Alias từ XMLParserContinued (tương thích ngược) ═══════
    @staticmethod
    def find_account_by_name(xml, account_name, screen_width, screen_height, config):
        return XMLParserContinued.find_account_by_name(
            xml, account_name, screen_width, screen_height, config
        )

    @staticmethod
    def find_nav_tab(xml, tab_name, screen_width, screen_height):
        return XMLParserContinued.find_nav_tab(
            xml, tab_name, screen_width, screen_height
        )

    @staticmethod
    def get_current_account_id(xml, screen_width=None, screen_height=None, config=None):
        return XMLParserContinued.get_current_account_id(xml, screen_width, screen_height, config)

"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║               PART 4/8 - XML PARSER (2/2)                      ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# XML PARSER v1.4.3 - PART 2 (Tiếp theo)
# ═══════════════════════════════════════════════════════════════
class XMLParserContinued:
    """XML Parser v1.4.3 - Part 2"""
    
    def find_account_by_name(xml: str, account_name: str, screen_width: int, screen_height: int, config) -> Optional[Tuple[int, int]]:
        """Tìm account - BỎ QUA STATUS BAR"""
        try:
            target = account_name.lower().strip()
            if target.startswith('@'):
                target = target[1:]
            
            pattern = r'(?:text|content-desc)="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            
            popup_opened = XMLParser.verify_popup_open(xml)
            
            status_bar_max_y = int(screen_height * 0.10)
            
            candidates = []
            
            for match in re.finditer(pattern, xml, re.IGNORECASE):
                text = match.group(1).strip()
                
                clean = text.lower()
                if clean.startswith('@'):
                    clean = clean[1:]
                
                if clean == target:
                    match_type = 'exact'
                elif target in clean or clean in target:
                    match_type = 'partial'
                else:
                    continue
                
                x1, y1, x2, y2 = map(int, match.groups()[1:])
                cy = (y1 + y2) // 2
                
                if cy < status_bar_max_y:
                    continue
                
                if not popup_opened:
                    y_min = int(screen_height * config.account_list_y_min)
                    y_max = int(screen_height * config.account_list_y_max)
                    
                    if not (y_min <= cy <= y_max):
                        continue
                
                cx = (x1 + x2) // 2
                candidates.append((match_type, cx, cy, text))
            
            if not candidates:
                return None
            
            exact_matches = [c for c in candidates if c[0] == 'exact']
            if exact_matches:
                _, cx, cy, text = exact_matches[0]
                return (cx, cy)
            
            _, cx, cy, text = candidates[0]
            return (cx, cy)
            
        except Exception as e:
            smart_logger.log(f"Lỗi tìm account: {e}")
        
        return None


    def find_nav_tab(xml: str, keywords: List[str], screen_width: int, screen_height: int) -> Optional[Tuple[int, int]]:
        """TÌM TAB NAVIGATION BẰNG XML"""
        try:
            xml_lower = xml.lower()
            
            navbar_y_min = int(screen_height * 0.90)
            navbar_y_max = screen_height
            
            pattern = r'(?:text|content-desc)="([^"]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            
            candidates = []
            
            for match in re.finditer(pattern, xml, re.IGNORECASE):
                text = match.group(1).strip().lower()
                
                matched_keyword = None
                for kw in keywords:
                    if kw.lower() in text:
                        matched_keyword = kw
                        break
                
                if not matched_keyword:
                    continue
                
                x1, y1, x2, y2 = map(int, match.groups()[1:])
                cy = (y1 + y2) // 2
                
                if not (navbar_y_min <= cy <= navbar_y_max):
                    continue
                
                cx = (x1 + x2) // 2
                candidates.append((cx, cy, matched_keyword))
            
            if candidates:
                cx, cy, kw = candidates[0]
                smart_logger.log(f"✅ Tìm tab '{kw}' tại ({cx}, {cy})")
                return (cx, cy)
            
            return None
            
        except Exception as e:
            smart_logger.log(f"Lỗi tìm tab: {e}")
            return None


    def get_current_account_id(xml: str, screen_width: int, screen_height: int, config) -> Optional[str]:
        """
        v1.3.5: LẤY @ID TÀI KHOẢN HIỆN TẠI
        
        Tìm @username ở vùng profile (10-30% chiều cao màn hình)
        """
        try:
            pattern = r'(?:text|content-desc)="(@[a-zA-Z0-9._]+)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            
            profile_y_min = int(screen_height * 0.10)
            profile_y_max = int(screen_height * 0.30)
            
            candidates = []
            
            for match in re.finditer(pattern, xml):
                username = match.group(1)
                x1, y1, x2, y2 = map(int, match.groups()[1:])
                cy = (y1 + y2) // 2
                
                if profile_y_min <= cy <= profile_y_max:
                    if XMLParser.is_valid_tiktok_id(username, config):
                        clean_id = XMLParser.clean_tiktok_id(username)
                        candidates.append(clean_id)
            
            if candidates:
                return candidates[0]
            
            return None
            
        except Exception as e:
            return None
    
    
    

# ══════════════════════════════════════════════════════════════════
# END OF PART 3/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║               PART 4/8 - XML PARSER (2/2)                      ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# XML PARSER v1.4.3 - PART 2 (Tiếp theo)
# ═══════════════════════════════════════════════════════════════
    

# ══════════════════════════════════════════════════════════════════
# END OF PART 3/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║               PART 4/8 - XML PARSER (2/2)                      ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# XML PARSER v1.4.3 - PART 2 (Tiếp theo)
# ═══════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════
# END OF PART 3/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║               PART 4/8 - XML PARSER (2/2)                      ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# XML PARSER v1.4.3 - PART 2 (Tiếp theo)
# ═══════════════════════════════════════════════════════════════
    
    
    

# ══════════════════════════════════════════════════════════════════
# END OF PART 3/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║               PART 4/8 - XML PARSER (2/2)                      ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# XML PARSER v1.4.3 - PART 2 (Tiếp theo)
# ═══════════════════════════════════════════════════════════════
    

# ══════════════════════════════════════════════════════════════════
# END OF PART 3/8
# ══════════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                    🎯 AT TOOL v1.4.3 🎯                        ║
║              CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG PRO                  ║
║               PART 4/8 - XML PARSER (2/2)                      ║
║   ✨ Proxy + Rest + Checkpoint + UI Pro + Stats Fixed ✨     ║
╚═══════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════
# XML PARSER v1.4.3 - PART 2 (Tiếp theo)
# ═══════════════════════════════════════════════════════════════
