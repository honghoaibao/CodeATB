"""
╔══════════════════════════════════════════════════════╗
║       core/priority_account.py - v1.4.5              ║
║   PriorityAccountManager + FollowVerifier            ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py:
  - PriorityAccountManager (line ~5095) - Ưu tiên account ít sessions
  - FollowVerifier         (line ~5208) - Double-check follow thành công
"""

import time
from typing import Dict, List, Optional
from ui.logger import smart_logger


class PriorityAccountManager:
    """
    Quản lý ưu tiên accounts v1.4.5

    Logic: Farm accounts có ít sessions / actions nhất trước
    """

    @staticmethod
    def sort_accounts_by_priority(accounts: List[str], stats_manager) -> List[str]:
        """
        Sắp xếp accounts theo thứ tự ưu tiên
        
        Priority: Accounts có ít sessions nhất lên đầu
        
        Args:
            accounts: Danh sách account names
            stats_manager: StatsManager instance
            
        Returns:
            Danh sách accounts đã sắp xếp
        """
        try:
            # Get today stats
            today_stats = stats_manager.get_today_stats()
            
            if not today_stats:
                # No stats yet, return original order
                smart_logger.log("ℹ️  Chưa có stats, dùng thứ tự gốc", force=True)
                return accounts
            
            # Create priority list: (account, sessions_count, total_actions)
            account_priorities = []
            
            for account in accounts:
                if account in today_stats.accounts:
                    acc_stats = today_stats.accounts[account]
                    sessions = acc_stats.sessions_count
                    total_actions = sum(acc_stats.total_actions.values())
                else:
                    # Account chưa farm hôm nay
                    sessions = 0
                    total_actions = 0
                
                account_priorities.append((account, sessions, total_actions))
            
            # Sort by sessions (ascending), then by total_actions (ascending)
            account_priorities.sort(key=lambda x: (x[1], x[2]))
            
            # Extract sorted accounts
            sorted_accounts = [acc for acc, _, _ in account_priorities]
            
            # Log priority order
            smart_logger.log("🏆 Thứ tự ưu tiên accounts:", force=True)
            for i, (acc, sessions, actions) in enumerate(account_priorities, 1):
                smart_logger.log(
                    f"  {i}. {acc} - {sessions} sessions, {actions} actions",
                    force=True
                )
            
            return sorted_accounts
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi sort_accounts: {e}", force=True)
            return accounts
    
    @staticmethod
    def get_account_priority_info(account: str, stats_manager) -> Dict:
        """
        Thông tin ưu tiên của 1 account

        Returns:
            {
                "sessions_today": int,
                "total_actions_today": int,
                "last_farm_time": datetime | None,
                "priority_score": int  # thấp hơn = ưu tiên cao hơn
            }
        """
        try:
            today_stats = stats_manager.get_today_stats()
            if not today_stats or account not in today_stats.accounts:
                return {
                    "sessions_today": 0,
                    "total_actions_today": 0,
                    "last_farm_time": None,
                    "priority_score": 0,
                }
            s = today_stats.accounts[account]
            return {
                "sessions_today": s.sessions_count,
                "total_actions_today": sum(s.total_actions.values()),
                "last_farm_time": s.last_session_time,
                "priority_score": s.sessions_count * 100 + sum(s.total_actions.values()),
            }
        except Exception:
            return {
                "sessions_today": 0,
                "total_actions_today": 0,
                "last_farm_time": None,
                "priority_score": 0,
            }


class FollowVerifier:
    """
    Xác minh follow thành công v1.4.5

    Quy trình:
    1. Click nút Follow
    2. Swipe down để reload profile
    3. Kiểm tra trạng thái "Following" / "Đang theo dõi"
    4. Trả về True/False
    """

    @staticmethod
    def perform_follow_with_verification(device, username: str,
                                          screen_width: int, screen_height: int) -> bool:
        """
        Follow + xác minh kết quả

        Returns:
            True nếu follow thành công
        """
        try:
            xml = device.dump_hierarchy()

            follow_xpaths = [
                '//android.widget.Button[@content-desc="Follow"]',
                '//android.widget.Button[@text="Follow"]',
                '//android.widget.Button[contains(@text, "Theo dõi")]',
                '//*[contains(@content-desc, "follow")][@clickable="true"]',
            ]

            follow_clicked = False
            for xpath in follow_xpaths:
                try:
                    if not device.xpath(xpath).exists:
                        continue
                    info = device.xpath(xpath).info
                    text = info.get("text", "").lower()
                    desc = info.get("contentDescription", "").lower()

                    # Đã follow rồi → bỏ qua
                    if "following" in text or "following" in desc or "đang theo dõi" in text:
                        return False

                    device.xpath(xpath).click()
                    follow_clicked = True
                    time.sleep(1.5)
                    break
                except Exception:
                    continue

            if not follow_clicked:
                return False

            # Reload profile
            sy = int(screen_height * 0.2)
            ey = int(screen_height * 0.6)
            cx = screen_width // 2
            device.swipe(cx, sy, cx, ey, duration=0.3)
            time.sleep(2)

            # Check trạng thái
            xml_after = device.dump_hierarchy().lower()
            success_indicators = [
                "following", "đang theo dõi",
                "message", "tin nhắn",
                "unfollow", "bỏ theo dõi",
            ]
            is_following = any(ind in xml_after for ind in success_indicators)

            # Check nút Follow còn không
            still_follow = False
            for xpath in follow_xpaths:
                try:
                    if device.xpath(xpath).exists:
                        info = device.xpath(xpath).info
                        t = info.get("text", "").lower()
                        if "follow" in t and "following" not in t:
                            still_follow = True
                            break
                except Exception:
                    continue

            return is_following and not still_follow

        except Exception:
            return False
