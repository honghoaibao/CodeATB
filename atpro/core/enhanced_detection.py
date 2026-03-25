"""
╔══════════════════════════════════════════════════════╗
║      core/enhanced_detection.py - v1.4.5             ║
║   EnhancedDetection - Multi-strategy element finder  ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → EnhancedDetection (line ~8842)

Multi-strategy approach:
  - Text matching (exact + fuzzy Levenshtein)
  - ResourceId matching
  - Content description matching
  - Position-based detection (±50px tolerance)
  - Track success rate per strategy
"""

import re
from typing import Any, Dict, List, Optional


class EnhancedDetection:
    """
    v1.4.5: Enhanced Element Detection

    Tìm element trên màn hình bằng nhiều strategies.
    Tự động track strategy nào hoạt động tốt nhất.
    """

    def __init__(self, device):
        self.device = device
        self.detection_history: Dict[str, Dict[str, int]] = {}

    # ─────────────────────────────────────────────────────────────
    # Main entry
    # ─────────────────────────────────────────────────────────────

    def multi_strategy_find(self, element_desc: dict, max_attempts: int = 3) -> Optional[Any]:
        """
        Tìm element với nhiều strategies

        Args:
            element_desc: {
                "text":         "Follow",
                "resource_id":  "com.zhiliaoapp.musically:id/follow_btn",
                "content_desc": "Follow button",
                "bounds":       [x1, y1, x2, y2]
            }
            max_attempts: số lần thử mỗi strategy

        Returns:
            Element nếu tìm thấy, None nếu không
        """
        strategies = [
            ("text_exact",    lambda: self._find_by_text_exact(element_desc.get("text"))),
            ("text_fuzzy",    lambda: self._find_by_text_fuzzy(element_desc.get("text"))),
            ("resource_id",   lambda: self._find_by_resource_id(element_desc.get("resource_id"))),
            ("content_desc",  lambda: self._find_by_content_desc(element_desc.get("content_desc"))),
            ("position",      lambda: self._find_by_position(element_desc.get("bounds"))),
        ]
        # Skip strategies without data
        skip_map = {
            "text_exact":   not element_desc.get("text"),
            "text_fuzzy":   not element_desc.get("text"),
            "resource_id":  not element_desc.get("resource_id"),
            "content_desc": not element_desc.get("content_desc"),
            "position":     not element_desc.get("bounds"),
        }

        for name, func in strategies:
            if skip_map.get(name):
                continue
            for _ in range(max_attempts):
                try:
                    elem = func()
                    if elem:
                        self._track(name, success=True)
                        return elem
                except Exception:
                    pass
            self._track(name, success=False)

        return None

    # ─────────────────────────────────────────────────────────────
    # Find strategies
    # ─────────────────────────────────────────────────────────────

    def _find_by_text_exact(self, text: Optional[str]) -> Optional[Any]:
        if not text:
            return None
        try:
            elem = self.device(text=text)
            return elem if elem.exists else None
        except Exception:
            return None

    def _find_by_text_fuzzy(self, text: Optional[str], threshold: float = 0.8) -> Optional[Any]:
        """Fuzzy text match dùng Levenshtein similarity"""
        if not text:
            return None
        try:
            import xml.etree.ElementTree as ET
            raw = self.device.dump_hierarchy()
            root = ET.fromstring(raw)
            best_elem = None
            best_score = 0.0
            for elem in root.iter():
                elem_text = elem.get("text", "")
                if elem_text:
                    sim = self._text_similarity(text.lower(), elem_text.lower())
                    if sim >= threshold and sim > best_score:
                        best_score = sim
                        try:
                            found = self.device(text=elem_text)
                            if found.exists:
                                best_elem = found
                        except Exception:
                            pass
            return best_elem
        except Exception:
            return None

    def _find_by_resource_id(self, resource_id: Optional[str]) -> Optional[Any]:
        if not resource_id:
            return None
        try:
            elem = self.device(resourceId=resource_id)
            return elem if elem.exists else None
        except Exception:
            return None

    def _find_by_content_desc(self, content_desc: Optional[str]) -> Optional[Any]:
        if not content_desc:
            return None
        try:
            elem = self.device(description=content_desc)
            return elem if elem.exists else None
        except Exception:
            return None

    def _find_by_position(self, bounds: Optional[List[int]]) -> Optional[Any]:
        """Tìm element gần position ±50px"""
        if not bounds or len(bounds) != 4:
            return None
        try:
            import xml.etree.ElementTree as ET
            x1, y1, x2, y2 = bounds
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            tolerance = 50
            raw = self.device.dump_hierarchy()
            root = ET.fromstring(raw)
            for elem in root.iter():
                eb = elem.get("bounds", "")
                m = re.findall(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", eb)
                if m:
                    ex1, ey1, ex2, ey2 = map(int, m[0])
                    ecx, ecy = (ex1 + ex2) // 2, (ey1 + ey2) // 2
                    if abs(ecx - cx) <= tolerance and abs(ecy - cy) <= tolerance:
                        text = elem.get("text", "")
                        rid  = elem.get("resource-id", "")
                        if text:
                            found = self.device(text=text)
                            if found.exists:
                                return found
                        elif rid:
                            found = self.device(resourceId=rid)
                            if found.exists:
                                return found
        except Exception:
            pass
        return None

    # ─────────────────────────────────────────────────────────────
    # Text similarity (Levenshtein)
    # ─────────────────────────────────────────────────────────────

    def _text_similarity(self, s1: str, s2: str) -> float:
        if not s1 or not s2:
            return 0.0
        l1, l2 = len(s1), len(s2)
        if l1 == 0:
            return 0.0 if l2 else 1.0
        if l2 == 0:
            return 0.0
        dp = [[0] * (l2 + 1) for _ in range(l1 + 1)]
        for i in range(l1 + 1):
            dp[i][0] = i
        for j in range(l2 + 1):
            dp[0][j] = j
        for i in range(1, l1 + 1):
            for j in range(1, l2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
        return 1 - dp[l1][l2] / max(l1, l2)

    # ─────────────────────────────────────────────────────────────
    # Analytics
    # ─────────────────────────────────────────────────────────────

    def _track(self, strategy: str, success: bool):
        if strategy not in self.detection_history:
            self.detection_history[strategy] = {"success": 0, "fail": 0}
        if success:
            self.detection_history[strategy]["success"] += 1
        else:
            self.detection_history[strategy]["fail"] += 1

    def get_detection_stats(self) -> Dict[str, Dict]:
        stats: Dict[str, Dict] = {}
        for strategy, counts in self.detection_history.items():
            total = counts["success"] + counts["fail"]
            if total:
                stats[strategy] = {
                    "success_rate": counts["success"] / total,
                    "total": total,
                    "successes": counts["success"],
                }
        return stats

    def get_best_strategy(self) -> Optional[str]:
        """Get strategy with highest success rate"""
        stats = self.get_detection_stats()
        if not stats:
            return None
        
        best = max(stats.items(), key=lambda x: x[1]['success_rate'])
        return best[0]


# ═══════════════════════════════════════════════════════════════
# TIKTOK AUTOMATION v1.4.3
# ═══════════════════════════════════════════════════════════════
    
