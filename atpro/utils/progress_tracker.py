"""
╔══════════════════════════════════════════════════════╗
║       utils/progress_tracker.py - v1.4.5             ║
║   ProgressTracker - Theo dõi tiến trình farm         ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → ProgressTracker (line ~8483)
"""

from typing import Dict


class ProgressTracker:
    """Theo dõi tiến trình chi tiết"""
    
    def __init__(self):
        self.total_actions = {
            'like': 0,
            'follow': 0,
            'comment': 0,
            'notification': 0,
            'shop': 0,
            'not_interested': 0,  # v1.4.3
            'repost': 0           # v1.4.3
        }
        self.current_account_actions = {
            'like': 0,
            'follow': 0,
            'comment': 0,
            'notification': 0,
            'shop': 0,
            'not_interested': 0,  # v1.4.3
            'repost': 0           # v1.4.3
        }
    
    def reset_current(self):
        """Reset counter cho account mới"""
        self.current_account_actions = {
            'like': 0,
            'follow': 0,
            'comment': 0,
            'notification': 0,
            'shop': 0,
            'not_interested': 0,  # v1.4.3
            'repost': 0           # v1.4.3
        }
    
    def add_action(self, action_type: str):
        """Thêm action"""
        if action_type in self.total_actions:
            self.total_actions[action_type] += 1
            self.current_account_actions[action_type] += 1
    
    def get_current_actions(self) -> Dict[str, int]:
        """Lấy actions hiện tại"""
        return self.current_account_actions.copy()
    
    def get_current_summary(self) -> str:
        """Lấy tóm tắt actions hiện tại - v1.4.3"""
        like = self.current_account_actions.get('like', 0)
        follow = self.current_account_actions.get('follow', 0)
        comment = self.current_account_actions.get('comment', 0)
        notif = self.current_account_actions.get('notification', 0)
        shop = self.current_account_actions.get('shop', 0)
        not_int = self.current_account_actions.get('not_interested', 0)
        repost = self.current_account_actions.get('repost', 0)
        
        base = f"❤️ {like} | 👥 {follow} | 💬 {comment} | 📬 {notif} | 🛍️ {shop}"
        
        # Add v1.4.3 if > 0
        if not_int > 0:
            base += f" | [yellow]🚫 {not_int}[/yellow]"
        if repost > 0:
            base += f" | [yellow]🔄 {repost}[/yellow]"
        
        return base
    
    def get_total_summary(self) -> str:
        """Lấy tổng actions - v1.4.3"""
        like = self.total_actions.get('like', 0)
        follow = self.total_actions.get('follow', 0)
        comment = self.total_actions.get('comment', 0)
        notif = self.total_actions.get('notification', 0)
        shop = self.total_actions.get('shop', 0)
        not_int = self.total_actions.get('not_interested', 0)
        repost = self.total_actions.get('repost', 0)
        
        return f"❤️ {like} | 👥 {follow} | 💬 {comment} | 📬 {notif} | 🛍️ {shop}"
