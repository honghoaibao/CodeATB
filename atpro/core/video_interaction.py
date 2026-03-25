"""
╔══════════════════════════════════════════════════════╗
║       core/video_interaction.py - v1.4.5             ║
║   SmartVideoInteraction - Tương tác thông minh       ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → SmartVideoInteraction (line ~4801)

Logic:
  - Video < 100 likes  → Không quan tâm
  - Video > 10K likes  → Đăng lại (Repost)
  - Còn lại            → Không làm gì
"""

import re
import time
from typing import Dict, Optional
from ui.logger import smart_logger


class SmartVideoInteraction:
    """
    Tương tác video thông minh v1.4.5

    Dựa vào số likes để quyết định hành động:
      - < not_interested_threshold (default 100)  → Không quan tâm
      - > repost_threshold (default 10,000)        → Đăng lại
    """

    # ─────────────────────────────────────────────────────────────
    # Parse likes
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def parse_likes_count(likes_text: str) -> int:
        """Parse "10.5K", "1.2M", "129K", "100" → int"""
        if not likes_text:
            return 0
        text = likes_text.strip().upper()
        for suffix, mult in [("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)]:
            if suffix in text:
                try:
                    return int(float(text.replace(suffix, "").replace(",", "").strip()) * mult)
                except (ValueError, AttributeError):
                    return 0
        try:
            return int(text.replace(",", "").replace(".", ""))
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    def get_video_likes(device, xml: str) -> Optional[int]:
        """
        TikTok 2026 — Lấy số likes của video hiện tại.

        Thuật toán RecyclerView 2026:
        ─────────────────────────────────────────────────────────────
        Side-action buttons (like, comment, share, follow) nằm ở
        cột phải màn hình. Like button là TextView với:
          • resource-id kết thúc bằng "id/asv" / "id/atv"  (TikTok 2026)
          • resource-id chứa "digg" hoặc "like_count"       (legacy)
          • bounds x1 > 74% screen_width  (cột phải)
          • text chứa số (K, M, B)
        ─────────────────────────────────────────────────────────────
        """
        try:
            # ── Tầng 1: resource-id asv / atv — TikTok 2026 ─────────
            # Like count là TextView đầu tiên bên phải (x > 74% width)
            # có text là số (có thể có K/M/B)
            pattern_asvatv = (
                r'class="android\.widget\.TextView"[^>]*'
                r'resource-id="[^"]*:id/a[st]v"[^>]*'
                r'text="([0-9]+(?:\.[0-9]+)?[KMBkmb]?)"[^>]*'
                r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            )
            for m in re.finditer(pattern_asvatv, xml):
                likes_text = m.group(1)
                x1 = int(m.group(2))
                # Phải nằm ở cột phải (side action area)
                if x1 > 600:
                    likes_count = SmartVideoInteraction.parse_likes_count(likes_text)
                    if likes_count >= 0:
                        smart_logger.log(f"📊 Video có {likes_count:,} likes (asv/atv)")
                        return likes_count

            # ── Tầng 2: resource-id digg / like_count (legacy) ───────
            digg_patterns = [
                r'resource-id="[^"]*(?:digg|like_count|like_icon)[^"]*"[^>]*text="([0-9.,]+[KMBkmb]?)"',
            ]
            for pattern in digg_patterns:
                for m in re.finditer(pattern, xml, re.IGNORECASE):
                    likes_text = m.group(1)
                    likes_count = SmartVideoInteraction.parse_likes_count(likes_text)
                    if likes_count > 0:
                        smart_logger.log(f"📊 Video có {likes_count:,} likes (digg/like_count)")
                        return likes_count

            # ── Tầng 3: text/content-desc có "likes" / "thích" ───────
            text_patterns = [
                r'text="([0-9.,]+[KMBkmb]?)\s+(?:likes?|thích)"',
                r'content-desc="([0-9.,]+[KMBkmb]?)\s+(?:likes?|thích)"',
            ]
            for pattern in text_patterns:
                for m in re.finditer(pattern, xml, re.IGNORECASE):
                    likes_text = m.group(1)
                    likes_count = SmartVideoInteraction.parse_likes_count(likes_text)
                    if likes_count > 0:
                        smart_logger.log(f"📊 Video có {likes_count:,} likes (text)")
                        return likes_count

            return None
        except Exception:
            return None

    @staticmethod
    def perform_not_interested(device, screen_width: int, screen_height: int) -> bool:
        """
        Thực hiện "Không quan tâm"
        
        Steps:
        1. Long-press video center (1s)
        2. Tìm "Không quan tâm" trong XML
        3. Click vào đó
        
        Returns:
            True nếu thành công
        """
        try:
            smart_logger.log("🚫 Thực hiện 'Không quan tâm'...", force=True)
            
            # 1. Long-press video center
            center_x = screen_width // 2
            center_y = screen_height // 2
            
            smart_logger.log(f"📍 Long-press tại ({center_x}, {center_y})", force=True)
            device.long_click(center_x, center_y, duration=1.0)
            time.sleep(1.5)
            
            # 2. Get XML
            xml = device.dump_hierarchy()
            
            # 3. Tìm "Không quan tâm"
            not_interested_keywords = [
                "Không quan tâm", "Not interested",
                "không quan tâm", "not interested"
            ]
            
            pattern = r'(?:text|content-desc)="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'
            
            for match in re.finditer(pattern, xml):
                text = match.group(1)
                
                # Check if matches keyword
                if any(kw in text for kw in not_interested_keywords):
                    x1, y1, x2, y2 = map(int, match.groups()[1:])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    
                    smart_logger.log(f"✅ Tìm thấy '{text}' tại ({cx}, {cy})", force=True)
                    device.click(cx, cy)
                    time.sleep(1)
                    
                    smart_logger.log("✅ Đã click 'Không quan tâm'", force=True)
                    return True
            
            smart_logger.log("⚠️  Không tìm thấy 'Không quan tâm'", force=True)
            # Press back to close menu
            device.press("back")
            return False
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi not_interested: {e}", force=True)
            device.press("back")  # Ensure menu closed
            return False
    
    @staticmethod
    def perform_repost(device, screen_width: int, screen_height: int) -> bool:
        """Long-press → tìm 'Đăng lại' → click"""
        try:
            cx = screen_width // 2
            cy = screen_height // 2
            device.long_click(cx, cy, duration=1.0)
            time.sleep(1.5)

            xml = device.dump_hierarchy()
            keywords = ["Đăng lại", "Repost", "đăng lại", "repost"]
            pattern = r'(?:text|content-desc)="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"'

            for m in re.finditer(pattern, xml):
                text = m.group(1)
                if any(kw in text for kw in keywords):
                    x1, y1, x2, y2 = map(int, m.groups()[1:])
                    device.click((x1 + x2) // 2, (y1 + y2) // 2)
                    time.sleep(1)
                    return True

            device.press("back")
            return False
        except Exception:
            try:
                device.press("back")
            except Exception:
                pass
            return False

    # ─────────────────────────────────────────────────────────────
    # Smart decision
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def smart_interact_with_video(device, screen_width: int, screen_height: int,
                                   config) -> Dict[str, bool]:
        """
        Tương tác thông minh dựa trên số likes

        Returns:
            {"not_interested": bool, "reposted": bool}
        """
        result = {"not_interested": False, "reposted": False}

        if not getattr(config, "enable_smart_video_interaction", True):
            return result

        try:
            xml   = device.dump_hierarchy()
            likes = SmartVideoInteraction.get_video_likes(device, xml)
            if likes is None:
                return result

            not_threshold  = getattr(config, "not_interested_threshold", 100)
            repo_threshold = getattr(config, "repost_threshold", 10000)

            if likes < not_threshold:
                result["not_interested"] = SmartVideoInteraction.perform_not_interested(
                    device, screen_width, screen_height
                )
            elif likes > repo_threshold:
                result["reposted"] = SmartVideoInteraction.perform_repost(
                    device, screen_width, screen_height
                )
        except Exception:
            pass

        return result
