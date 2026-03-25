"""
╔══════════════════════════════════════════════════════╗
║         ui/notifications.py - v1.4.5                 ║
║   NotificationManager - Telegram / Discord / Webhook ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → NotificationManager (line ~3002)

Cung cấp:
  - Gửi thông báo Telegram Bot API (với ảnh/screenshot)
  - Gửi thông báo Discord Webhook (rich embeds)
  - Gửi Custom Webhook (POST/GET với retry & backoff)
  - Chụp và gửi screenshot qua Telegram / Discord
  - Rate limiting, duplicate filtering, lịch sử thông báo
  - Async non-blocking (background thread + Queue)
  - Báo cáo lỗi / checkpoint / session / daily report
"""

import time
import threading
from datetime import datetime, date
from io import BytesIO
from queue import Queue
from typing import Dict, List, Optional, Tuple, Type

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from ui.logger import smart_logger
from ui.ultimate_ui import UltimateUI as _UltimateUI
_ultimate_ui_instance = _UltimateUI()
ultimate_ui = _ultimate_ui_instance
class NotificationManager:
    """
    Quản lý thông báo qua Telegram & Discord
    
    ✨ Tính năng:
    - Gửi thông báo Telegram (Bot API)
    - Gửi thông báo Discord (Webhook)
    - Báo cáo chi tiết từng account
    - Tự động format đẹp
    """
    
    def __init__(self):
        """
        🔔 Ultimate Notification Manager v1.4.3
        
        ✨ NEW in v1.4.3:
        - Non-blocking async notifications (threading + queue)
        - No tool freeze when sending notifications
        - Better performance and responsiveness
        
        ✨ FEATURES from v1.4.3:
        - Multi-channel: Telegram + Discord + Custom Webhook
        - Rich embeds với màu sắc đẹp mắt
        - Auto screenshot on events (errors, checkpoints, sessions)
        - Smart filtering by importance level
        - Scheduled reports (daily 20:00, weekly Monday)
        - Error tracking với full details + screenshot
        - Session notifications (start/end với full stats)
        - Checkpoint critical alerts
        - Notification history & analytics
        - Retry mechanism với exponential backoff
        - Rate limiting intelligent
        - Template system for custom messages
        """
        # Telegram config
        self.telegram_enabled = False
        self.telegram_bot_token = ""
        self.telegram_chat_id = ""
        
        # Discord config
        self.discord_enabled = False
        self.discord_webhook_url = ""
        
        # Custom Webhook config (NEW v1.4.3)
        self.webhook_enabled = False
        self.webhook_url = ""
        self.webhook_headers = {}
        self.webhook_method = "POST"
        
        # Screenshot config (NEW v1.4.3)
        self.enable_screenshots = True
        self.screenshot_on_error = True
        self.screenshot_on_checkpoint = True
        self.screenshot_on_session_end = False
        self.screenshot_quality = 85  # 1-100
        
        # Filtering config (NEW v1.4.3)
        self.min_importance = "info"  # debug, info, warning, error, critical
        self.filter_duplicates = True
        self.duplicate_window = 300  # 5 minutes
        
        # Scheduled reports (NEW v1.4.3)
        self.enable_scheduled_reports = True
        self.daily_report_time = "20:00"
        self.weekly_report_day = 0  # Monday
        self.last_daily_report = None
        self.last_weekly_report = None
        
        # History & Analytics (NEW v1.4.3)
        self.notification_history = []
        self.max_history_size = 1000
        self.session_stats = {
            'notifications_sent': 0,
            'telegram_sent': 0,
            'discord_sent': 0,
            'webhook_sent': 0,
            'screenshots_sent': 0,
            'errors': 0,
            'retries': 0
        }
        
        # Retry config (NEW v1.4.3)
        self.enable_retry = True
        self.max_retries = 3
        self.retry_delay = 2.0  # seconds
        self.use_exponential_backoff = True
        
        # Rate limiting (NEW v1.4.3)
        self.enable_rate_limit = True
        self.max_per_minute = 20
        self.rate_limit_window = []
        
        # Recent messages for duplicate detection
        self.recent_messages = []
        
        # ═══════════════════════════════════════════════════════════════
        # v1.4.3: ASYNC NOTIFICATION SYSTEM
        # ═══════════════════════════════════════════════════════════════
        import threading
        from queue import Queue
        
        self.enable_async = True  # Can be disabled for debugging
        self.notification_queue = Queue()
        self.async_worker = None
        
        if self.enable_async:
            self._start_async_worker()
    
    def _start_async_worker(self):
        """
        v1.4.3: Start async notification worker thread
        
        Benefits:
        - Tool doesn't freeze when sending notifications
        - Better performance during network delays
        - Queued notifications sent in background
        """
        import threading
        
        def worker():
            """Background worker for async notifications"""
            while True:
                try:
                    # Get task from queue (blocking)
                    task = self.notification_queue.get()
                    
                    if task is None:  # Shutdown signal
                        break
                    
                    # Unpack task
                    func, args, kwargs = task
                    
                    # Execute notification function
                    func(*args, **kwargs)
                    
                except Exception as e:
                    # Log error but don't crash worker
                    print(f"[Async Notification Error] {e}")
                
                finally:
                    # Mark task as done
                    self.notification_queue.task_done()
        
        # Create and start daemon thread
        self.async_worker = threading.Thread(target=worker, daemon=True)
        self.async_worker.start()
    
    def _queue_notification(self, func, *args, **kwargs):
        """
        v1.4.3: Queue notification for async execution
        
        Args:
            func: Notification function to call
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        if self.enable_async and self.async_worker and self.async_worker.is_alive():
            # Add to queue for async execution
            self.notification_queue.put((func, args, kwargs))
        else:
            # Fallback: Execute synchronously
            func(*args, **kwargs)
    
    def shutdown_async_worker(self):
        """
        v1.4.3: Gracefully shutdown async worker
        
        Call this before exiting the application
        """
        if self.async_worker and self.async_worker.is_alive():
            # Send shutdown signal
            self.notification_queue.put(None)
            
            # Wait for queue to be processed (max 5 seconds)
            try:
                self.notification_queue.join()
            except Exception:
                pass
    
    def configure_telegram(self, bot_token: str, chat_id: str):
        """Cấu hình Telegram Bot"""
        self.telegram_bot_token = bot_token.strip()
        self.telegram_chat_id = chat_id.strip()
        self.telegram_enabled = bool(bot_token and chat_id)
    
    def configure_discord(self, webhook_url: str):
        """Cấu hình Discord Webhook"""
        self.discord_webhook_url = webhook_url.strip()
        self.discord_enabled = bool(webhook_url)
    
    def send_telegram(self, message: str, photo_url: str = None) -> bool:
        """
        v1.4.3 ULTIMATE: Gửi thông báo qua Telegram với Rich HTML
        ==========================================================
        Args:
            message: HTML formatted message
            photo_url: Optional photo URL to send with message
        """
        if not self.telegram_enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            data = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": False  # Enable link previews
            }
            
            # If photo provided, send as photo with caption instead
            if photo_url:
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendPhoto"
                data = {
                    "chat_id": self.telegram_chat_id,
                    "photo": photo_url,
                    "caption": message,
                    "parse_mode": "HTML"
                }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                self.session_stats['telegram_sent'] += 1
                return True
            else:
                ultimate_ui.show_message(f"❌ Telegram lỗi: {response.status_code}", "error")
                return False
                
        except Exception as e:
            ultimate_ui.show_message(f"❌ Lỗi gửi Telegram: {e}", "error")
            self.session_stats['errors'] += 1
            return False
    
    def send_discord(self, message: str = None, embed: dict = None) -> bool:
        """
        v1.4.3 ULTIMATE: Gửi thông báo qua Discord với Rich Embeds
        ===========================================================
        Args:
            message: Plain text message (optional)
            embed: Rich embed dict (recommended for beautiful notifications)
        """
        if not self.discord_enabled:
            return False
        
        try:
            data = {}
            
            # Add message if provided
            if message:
                data["content"] = message
            
            # Add embed if provided (makes it beautiful!)
            if embed:
                data["embeds"] = [embed]
            
            # If neither provided, error
            if not message and not embed:
                return False
            
            response = requests.post(self.discord_webhook_url, json=data, timeout=10)
            
            if response.status_code in [200, 204]:
                self.session_stats['discord_sent'] += 1
                return True
            else:
                ultimate_ui.show_message(f"❌ Discord lỗi: {response.status_code}", "error")
                return False
                
        except Exception as e:
            ultimate_ui.show_message(f"❌ Lỗi gửi Discord: {e}", "error")
            self.session_stats['errors'] += 1
            return False
    
    def send_notification(self, discord_content = None, telegram_content: str = None):
        """
        v1.4.3: Gửi thông báo qua tất cả kênh - With Async Support
        ===========================================================
        
        v1.4.3 NEW: Non-blocking async notifications
        - Doesn't freeze tool when network is slow
        - Uses background thread for sending
        - Can be disabled by setting enable_async = False
        
        Args:
            discord_content: Can be string (plain) or dict (embed)
            telegram_content: HTML formatted string
        """
        # v1.4.3: Use async queue for non-blocking sends
        self._queue_notification(self._send_notification_sync, discord_content, telegram_content)
    
    def _send_notification_sync(self, discord_content = None, telegram_content: str = None):
        """
        v1.4.3: Internal method for actual notification sending
        (Called by async worker thread)
        """
        results = []
        
        if self.telegram_enabled and telegram_content:
            success = self.send_telegram(telegram_content)
            results.append(("Telegram", success))
        
        if self.discord_enabled and discord_content:
            # Check if discord_content is embed (dict) or plain message (str)
            if isinstance(discord_content, dict):
                # It's an embed
                success = self.send_discord(embed=discord_content)
            else:
                # It's plain text
                success = self.send_discord(message=discord_content)
            results.append(("Discord", success))
        
        return results
    
    def format_session_start(self, total_accounts: int) -> tuple:
        """
        v1.4.3 BUILD 5: Format thông báo bắt đầu session - OPTIMIZED & BEAUTIFUL!
        =========================================================================
        ✨ NEW in BUILD 5:
        - More compact layout
        - Better emojis
        - Cleaner structure
        - Faster notification sending
        
        Returns: (discord_embed, telegram_html)
        """
        now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
        
        # ═══════════════════════════════════════════════════════════════
        # DISCORD RICH EMBED - BUILD 5 Enhanced
        # ═══════════════════════════════════════════════════════════════
        discord_embed = {
            "title": "🚀 AT TOOL - SESSION STARTED",
            "description": f"""**New farming session initiated!**
⏰ {now.strftime('%H:%M:%S')} | {now.strftime('%d/%m/%Y')}

🎯 Target: **{total_accounts} accounts**
🤖 Mode: Fully automated farming
📊 Status: 🟢 **RUNNING**""",
            "color": 0x00D9FF,  # Bright cyan
            "fields": [
                {
                    "name": "📱 Accounts",
                    "value": f"```{total_accounts}```",
                    "inline": True
                },
                {
                    "name": "⚡ Features",
                    "value": "```Auto-Farm```",
                    "inline": True
                },
                {
                    "name": "🎯 Actions",
                    "value": "```Like•Follow•Comment```",
                    "inline": True
                }
            ],
            "footer": {
                "text": "AT Tool v1.4.3 Build 5 | TikTok Auto Farming"
            },
            "timestamp": datetime.now(pytz.timezone('UTC')).isoformat()
        }
        
        # ═══════════════════════════════════════════════════════════════
        # TELEGRAM RICH HTML - BUILD 5 Compact & Beautiful
        # ═══════════════════════════════════════════════════════════════
        telegram_html = f"""<b>{'━' * 28}</b>
<b>🚀 AT TOOL SESSION</b>
<b>{'━' * 28}</b>

<b>📊 INFO</b>
  🎯 Accounts: <b>{total_accounts}</b>
  ⏰ Time: <code>{now.strftime('%H:%M:%S')}</code>
  📅 Date: <code>{now.strftime('%d/%m/%Y')}</code>
  🔥 Status: <b>RUNNING</b>

<b>⚡ FEATURES</b>
  ✅ Auto Like & Follow
  ✅ Smart Comments
  ✅ Shop Browsing
  ✅ Error Recovery

<i>━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v1.4.3 B5 | Started {now.strftime('%H:%M')}</i>"""
        
        return (discord_embed, telegram_html)
    
    def create_progress_bar(self, current: int, total: int, length: int = 20, filled: str = '█', empty: str = '░') -> str:
        """
        v1.4.3: Create visual progress bar
        
        Args:
            current: Current value
            total: Total value
            length: Bar length in characters
            filled: Character for filled portion
            empty: Character for empty portion
            
        Returns:
            Progress bar string like: ████████████░░░░░░░░ 60%
        """
        if total == 0:
            percentage = 0
        else:
            percentage = int((current / total) * 100)
        
        filled_length = int((current / total) * length) if total > 0 else 0
        bar = filled * filled_length + empty * (length - filled_length)
        
        return f"{bar} {percentage}%"
    
    def format_session_complete(self, session_stats: Dict, account_details: List[Dict]) -> tuple:
        """
        v1.4.3 BUILD 5: Format thông báo hoàn thành session - OPTIMIZED & BEAUTIFUL!
        ==============================================================================
        ✨ NEW in BUILD 5:
        - Cleaner, more compact layout
        - Better visual hierarchy
        - Faster rendering
        - More informative but less verbose
        
        Returns: (discord_embed, telegram_html)
        """
        now = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh'))
        
        total = session_stats.get('total_accounts', 0)
        success = session_stats.get('successful_accounts', 0)
        failed = session_stats.get('failed_accounts', 0)
        total_actions = session_stats.get('total_actions', {})
        success_rate = (success / total * 100) if total > 0 else 0
        
        # Color & status based on success rate
        if success_rate >= 80:
            color = 0x00FF00  # Green
            status_emoji = "✅"
            status_text = "EXCELLENT"
        elif success_rate >= 50:
            color = 0xFFFF00  # Yellow  
            status_emoji = "⚠️"
            status_text = "GOOD"
        else:
            color = 0xFF0000  # Red
            status_emoji = "❌"
            status_text = "NEEDS ATTENTION"
        
        # v1.4.3 BUILD 5: Compact progress bar
        success_bar = self.create_progress_bar(success, total, 12, '█', '░')
        
        # ═══════════════════════════════════════════════════════════════
        # DISCORD RICH EMBED - BUILD 5 Enhanced
        # ═══════════════════════════════════════════════════════════════
        description = f"""{status_emoji} **{status_text}** - Session Complete
⏰ {now.strftime('%H:%M:%S')} | {now.strftime('%d/%m/%Y')}

**📊 Results**
```
{success}/{total} accounts ({success_rate:.0f}%)
{success_bar}
```"""
        
        discord_fields = []
        
        # Actions summary - BUILD 5: More compact
        if total_actions:
            action_icons = {'like': '❤️', 'follow': '👥', 'comment': '💬', 'share': '📤', 'shop': '🛒'}
            action_texts = []
            for action, count in total_actions.items():
                if count > 0:
                    icon = action_icons.get(action, '•')
                    action_texts.append(f"{icon} {count}")
            
            if action_texts:
                discord_fields.append({
                    "name": "🎯 Total Actions",
                    "value": "```" + " • ".join(action_texts) + "```",
                    "inline": False
                })
        
        # Account status - BUILD 5: Top 10 only, more compact
        if account_details:
            status_lines = []
            for i, acc in enumerate(account_details[:10], 1):
                name = acc.get('account_name', f'Acc{i}')
                status = acc.get('follow_status', 'unknown')
                actions = acc.get('actions', {})
                
                # Status icon
                if status == "success":
                    icon = "✅"
                elif status == "checkpoint":
                    icon = "⚠️"
                elif status == "failed":
                    icon = "❌"
                else:
                    icon = "❓"
                
                # Action summary (compact)
                action_icons = {'like': '❤', 'follow': '👥', 'comment': '💬', 'shop': '🛒'}
                action_summary = []
                for action, count in actions.items():
                    if count > 0:
                        a_icon = action_icons.get(action, '•')
                        action_summary.append(f"{a_icon}{count}")
                
                if action_summary:
                    status_lines.append(f"{icon} **{name}**: {' '.join(action_summary)}")
                else:
                    status_lines.append(f"{icon} **{name}**")
            
            if len(account_details) > 10:
                status_lines.append(f"*... +{len(account_details) - 10} more*")
            
            discord_fields.append({
                "name": "📱 Account Details",
                "value": "\n".join(status_lines),
                "inline": False
            })
        
        discord_embed = {
            "title": f"{status_emoji} SESSION COMPLETE - {status_text}",
            "description": description,
            "color": color,
            "fields": discord_fields,
            "footer": {
                "text": f"AT Tool v1.4.3 B5 | {total} accounts | {success_rate:.0f}% success"
            },
            "timestamp": datetime.now(pytz.timezone('UTC')).isoformat()
        }
        
        # ═══════════════════════════════════════════════════════════════
        # TELEGRAM RICH HTML - BUILD 5 Compact
        # ═══════════════════════════════════════════════════════════════
        telegram_lines = [
            f"<b>{'━' * 28}</b>",
            f"<b>{status_emoji} SESSION COMPLETE</b>",
            f"<b>{'━' * 28}</b>",
            "",
            f"<b>📊 RESULTS</b>",
            f"  ✅ Success: <b>{success}/{total}</b> ({success_rate:.0f}%)",
            f"  📈 Rate: <code>{success_bar}</code>",
            ""
        ]
        
        # Actions - BUILD 5: Single line
        if total_actions:
            action_icons = {'like': '❤️', 'follow': '👥', 'comment': '💬', 'share': '📤', 'shop': '🛒'}
            action_parts = []
            for action, count in total_actions.items():
                if count > 0:
                    icon = action_icons.get(action, '•')
                    action_parts.append(f"{icon}{count}")
            
            if action_parts:
                telegram_lines.append(f"<b>🎯 ACTIONS</b>")
                telegram_lines.append(f"  {' • '.join(action_parts)}")
                telegram_lines.append("")
        
        # Top accounts - BUILD 5: Top 8 only
        if account_details:
            telegram_lines.append(f"<b>📱 TOP ACCOUNTS</b>")
            for i, acc in enumerate(account_details[:8], 1):
                name = acc.get('account_name', f'Acc{i}')
                status = acc.get('follow_status', 'unknown')
                
                if status == "success":
                    telegram_lines.append(f"  ✅ <b>{name}</b>")
                elif status == "checkpoint":
                    telegram_lines.append(f"  ⚠️ <b>{name}</b> (CP)")
                elif status == "failed":
                    telegram_lines.append(f"  ❌ <b>{name}</b>")
            
            if len(account_details) > 8:
                telegram_lines.append(f"  <i>... +{len(account_details) - 8} more</i>")
            telegram_lines.append("")
        
        telegram_lines.extend([
            f"<i>━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"v1.4.3 B5 | {now.strftime('%H:%M')}</i>"
        ])
        
        telegram_html = "\n".join(telegram_lines)
        
        return (discord_embed, telegram_html)
        
        # Follow details section
        if account_details:
            telegram_lines.append("<b>🔹 👥 CHI TIẾT FOLLOW</b>")
            
            for acc in account_details:
                name = acc.get('account_name', 'Unknown')
                status = acc.get('follow_status', 'unknown')
                
                if status == "success":
                    telegram_lines.append(f"  ✅ <b>{name}</b> | Follow OK")
                elif status == "checkpoint":
                    telegram_lines.append(f"  ⚠️ <b>{name}</b> | Checkpoint")
                elif status == "failed":
                    telegram_lines.append(f"  ❌ <b>{name}</b> | Thất bại")
                else:
                    telegram_lines.append(f"  ❓ <b>{name}</b> | Chưa rõ")
            
            telegram_lines.append("")
        
        # Action details section
        if account_details:
            telegram_lines.append("<b>🔹 📱 CHI TIẾT HÀNH ĐỘNG</b>")
            action_icons = {'like': '❤️', 'follow': '👥', 'comment': '💬', 'share': '📤', 'shop': '🛒'}
            
            for idx, acc in enumerate(account_details, 1):
                name = acc.get('account_name', f'Account {idx}')
                actions = acc.get('actions', {})
                
                action_strs = []
                for action, count in actions.items():
                    if count > 0:
                        icon = action_icons.get(action, '•')
                        action_strs.append(f"{icon}{count}")
                
                if action_strs:
                    telegram_lines.append(f"  <b>{name}</b>: {' | '.join(action_strs)}")
            
            telegram_lines.append("")
        
        # Footer
        telegram_lines.extend([
            f"<b>{'─' * 30}</b>",
            f"<i>⏰ Hoàn thành: {now.strftime('%H:%M:%S')} | Success: {success_rate:.1f}% | AT Tool v1.4.3</i>"
        ])
        
        telegram_html = "\n".join(telegram_lines)
        
        return (discord_embed, telegram_html)
        """
        Format thông báo hoàn thành session với chi tiết từng account
        
        Args:
            session_stats: Thống kê tổng quan
            account_details: List các dict chứa thông tin từng account:
                - account_name: Tên account (vd: @username)
                - status: "success" hoặc "failed"
                - follow_status: "success", "failed", hoặc "checkpoint"
                - actions: Dict {action_type: count}
                - errors: List lỗi (nếu có)
                - duration: Thời gian chạy
        """
        
        # Discord format
        discord_lines = [
            "✅ **AT TOOL - HOÀN THÀNH SESSION**",
            "",
            "📊 **TỔNG QUAN:**"
        ]
        
        # Telegram format
        telegram_lines = [
            "✅ <b>AT TOOL - HOÀN THÀNH SESSION</b>",
            "",
            "📊 <b>TỔNG QUAN:</b>"
        ]
        
        # Stats chung
        total = session_stats.get('total_accounts', 0)
        success = session_stats.get('successful_accounts', 0)
        failed = session_stats.get('failed_accounts', 0)
        
        stats_discord = [
            f"• Tổng accounts: **{total}**",
            f"• Thành công: **{success}** ✅",
            f"• Thất bại: **{failed}** ❌",
            f"• Tỷ lệ: **{(success/total*100) if total > 0 else 0:.1f}%**",
            ""
        ]
        
        stats_telegram = [
            f"• Tổng accounts: <b>{total}</b>",
            f"• Thành công: <b>{success}</b> ✅",
            f"• Thất bại: <b>{failed}</b> ❌",
            f"• Tỷ lệ: <b>{(success/total*100) if total > 0 else 0:.1f}%</b>",
            ""
        ]
        
        discord_lines.extend(stats_discord)
        telegram_lines.extend(stats_telegram)
        
        # Thống kê actions tổng
        total_actions = session_stats.get('total_actions', {})
        if total_actions:
            discord_lines.append("🎯 **HÀNH ĐỘNG TỔNG:**")
            telegram_lines.append("🎯 <b>HÀNH ĐỘNG TỔNG:</b>")
            
            action_icons = {
                'like': '❤️',
                'follow': '👥',
                'comment': '💬',
                'share': '📤',
                'shop': '🛒'
            }
            
            for action, count in total_actions.items():
                icon = action_icons.get(action, '•')
                discord_lines.append(f"• {icon} {action.title()}: **{count}**")
                telegram_lines.append(f"• {icon} {action.title()}: <b>{count}</b>")
            
            discord_lines.append("")
            telegram_lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # PHẦN FOLLOW - RIÊNG BIỆT VÀ RÕ RÀNG
        # ═══════════════════════════════════════════════════════════════
        discord_lines.append("👥 **CHI TIẾT FOLLOW:**")
        telegram_lines.append("👥 <b>CHI TIẾT FOLLOW:</b>")
        discord_lines.append("─" * 40)
        telegram_lines.append("─" * 40)
        
        for acc in account_details:
            acc_name = acc.get('account_name', 'Unknown')
            follow_status = acc.get('follow_status', 'unknown')
            
            # Format theo yêu cầu: @username | Status
            if follow_status == "success":
                status_text = "Follow thành công | Có thể làm nhiệm vụ ✅"
                icon = "✅"
            elif follow_status == "checkpoint":
                status_text = "Checkpoint | Không thể hoạt động ⚠️"
                icon = "⚠️"
            elif follow_status == "failed":
                status_text = "Thất bại | Cần kiểm tra ❌"
                icon = "❌"
            else:
                status_text = "Chưa kiểm tra"
                icon = "❓"
            
            # Discord
            discord_lines.append(f"{icon} **{acc_name}** | {status_text}")
            
            # Telegram
            telegram_lines.append(f"{icon} <b>{acc_name}</b> | {status_text}")
        
        discord_lines.append("")
        telegram_lines.append("")
        
        # ═══════════════════════════════════════════════════════════════
        # CHI TIẾT HÀNH ĐỘNG TỪNG ACCOUNT
        # ═══════════════════════════════════════════════════════════════
        discord_lines.append("📱 **CHI TIẾT HÀNH ĐỘNG:**")
        telegram_lines.append("📱 <b>CHI TIẾT HÀNH ĐỘNG:</b>")
        discord_lines.append("─" * 40)
        telegram_lines.append("─" * 40)
        
        action_icons = {
            'like': '❤️',
            'follow': '👥',
            'comment': '💬',
            'share': '📤',
            'shop': '🛒'
        }
        
        for idx, acc in enumerate(account_details, 1):
            acc_name = acc.get('account_name', f'Account {idx}')
            status = acc.get('status', 'unknown')
            actions = acc.get('actions', {})
            errors = acc.get('errors', [])
            duration = acc.get('duration', 0)
            
            # Status icon
            status_icon = "✅" if status == "success" else "❌"
            
            # Discord
            discord_lines.append(f"{status_icon} **{acc_name}**")
            if actions:
                action_strs = []
                for action, count in actions.items():
                    if count > 0:  # Chỉ show actions có count > 0
                        icon = action_icons.get(action, '•')
                        action_strs.append(f"{icon}{count}")
                if action_strs:
                    discord_lines.append(f"  └─ {' | '.join(action_strs)}")
            
            if errors:
                discord_lines.append(f"  └─ ⚠️ Lỗi: {', '.join(errors[:2])}")
            
            if duration > 0:
                discord_lines.append(f"  └─ ⏱️ {duration//60}m {duration%60}s")
            
            # Telegram  
            telegram_lines.append(f"{status_icon} <b>{acc_name}</b>")
            if actions:
                action_strs = []
                for action, count in actions.items():
                    if count > 0:  # Chỉ show actions có count > 0
                        icon = action_icons.get(action, '•')
                        action_strs.append(f"{icon}{count}")
                if action_strs:
                    telegram_lines.append(f"  └─ {' | '.join(action_strs)}")
            
            if errors:
                telegram_lines.append(f"  └─ ⚠️ Lỗi: {', '.join(errors[:2])}")
            
            if duration > 0:
                telegram_lines.append(f"  └─ ⏱️ {duration//60}m {duration%60}s")
            
            # Spacer giữa các account
            if idx < len(account_details):
                discord_lines.append("")
                telegram_lines.append("")
        
        # Footer
        discord_lines.append("─" * 40)
        discord_lines.append(f"⏰ Hoàn thành: {datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')}")
        
        telegram_lines.append("─" * 40)
        telegram_lines.append(f"⏰ Hoàn thành: {datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')}")
        
        return ("\n".join(discord_lines), "\n".join(telegram_lines))
    
    def format_error_alert(self, account_name: str, error_type: str, error_msg: str):
        """Format thông báo lỗi quan trọng"""
        discord_msg = f"""⚠️ **CẢNH BÁO LỖI**

📱 Account: **{account_name}**
❌ Loại lỗi: **{error_type}**
📝 Chi tiết: {error_msg}

⏰ {datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')}"""
        
        telegram_msg = f"""⚠️ <b>CẢNH BÁO LỖI</b>

📱 Account: <b>{account_name}</b>
❌ Loại lỗi: <b>{error_type}</b>
📝 Chi tiết: {error_msg}

⏰ {datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')}"""
        return (discord_msg, telegram_msg)
    
    def test_connection(self) -> Dict[str, bool]:
        """Test kết nối tới các platform"""
        results = {}
        
        if self.telegram_enabled:
            test_msg = f"🧪 <b>Test connection from AT Tool</b>\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            results['telegram'] = self.send_telegram(test_msg)
        
        if self.discord_enabled:
            test_msg = f"🧪 **Test connection from AT Tool**\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            results['discord'] = self.send_discord(test_msg)
        
        return results
    
    # ═══════════════════════════════════════════════════════════════
    # 🆕 ULTIMATE NOTIFICATION METHODS v1.4.3
    # ═══════════════════════════════════════════════════════════════
    
    def configure_webhook(self, url: str, headers: Dict[str, str] = None, method: str = "POST"):
        """Configure custom webhook (NEW v1.4.3)"""
        self.webhook_url = url.strip()
        self.webhook_headers = headers or {}
        self.webhook_method = method.upper()
        self.webhook_enabled = bool(url)
        smart_logger.log(f"✅ Webhook configured: {url[:50]}...", force=True)
    
    def send_webhook(self, payload: Dict, retry: bool = True) -> bool:
        """
        Send notification to custom webhook (NEW v1.4.3)
        
        Args:
            payload: Dictionary data to send
            retry: Enable retry on failure
        """
        if not self.webhook_enabled:
            return False
        
        if not self._check_rate_limit():
            smart_logger.log("⚠️  Rate limit reached, skipping webhook", force=True)
            return False
        
        attempts = 0
        max_attempts = self.max_retries if retry and self.enable_retry else 1
        
        while attempts < max_attempts:
            try:
                headers = self.webhook_headers.copy()
                headers['Content-Type'] = 'application/json'
                
                if self.webhook_method == "POST":
                    response = requests.post(
                        self.webhook_url,
                        json=payload,
                        headers=headers,
                        timeout=10
                    )
                else:
                    response = requests.get(
                        self.webhook_url,
                        params=payload,
                        headers=headers,
                        timeout=10
                    )
                
                if response.status_code in [200, 201, 204]:
                    self.session_stats['webhook_sent'] += 1
                    self.session_stats['notifications_sent'] += 1
                    return True
                
                attempts += 1
                if attempts < max_attempts:
                    delay = self.retry_delay * (2 ** attempts) if self.use_exponential_backoff else self.retry_delay
                    time.sleep(delay)
                    self.session_stats['retries'] += 1
            
            except Exception as e:
                attempts += 1
                if attempts < max_attempts:
                    delay = self.retry_delay * (2 ** attempts) if self.use_exponential_backoff else self.retry_delay
                    time.sleep(delay)
                    self.session_stats['retries'] += 1
                else:
                    smart_logger.log(f"❌ Webhook error after {attempts} attempts: {e}", force=True)
                    self.session_stats['errors'] += 1
        
        return False
    
    def capture_and_send_screenshot(self, device, caption: str = "Screenshot", 
                                    channels: list = None) -> bool:
        """
        Capture and send screenshot (NEW v1.4.3)
        
        Args:
            device: uiautomator2 device object
            caption: Screenshot caption
            channels: List of channels ['telegram', 'discord'] or None for all
        """
        if not self.enable_screenshots:
            return False
        
        if channels is None:
            channels = []
            if self.telegram_enabled:
                channels.append('telegram')
            if self.discord_enabled:
                channels.append('discord')
        
        if not channels:
            return False
        
        try:
            # Capture screenshot
            screenshot = device.screenshot()
            
            # Convert to bytes
            from io import BytesIO
            buffer = BytesIO()
            screenshot.save(buffer, format='PNG', quality=self.screenshot_quality)
            screenshot_bytes = buffer.getvalue()
            
            success = False
            
            # Send to Telegram
            if 'telegram' in channels and self.telegram_enabled:
                try:
                    url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendPhoto"
                    files = {'photo': ('screenshot.png', screenshot_bytes, 'image/png')}
                    data = {
                        'chat_id': self.telegram_chat_id,
                        'caption': f"📸 {caption}"
                    }
                    response = requests.post(url, data=data, files=files, timeout=15)
                    if response.status_code == 200:
                        success = True
                        self.session_stats['screenshots_sent'] += 1
                except Exception as e:
                    smart_logger.log(f"⚠️  Telegram screenshot lỗi: {e}", force=True)
            
            # Send to Discord
            if 'discord' in channels and self.discord_enabled:
                try:
                    files = {'file': ('screenshot.png', screenshot_bytes, 'image/png')}
                    data = {'content': f"📸 {caption}"}
                    response = requests.post(self.discord_webhook_url, data=data, files=files, timeout=15)
                    if response.status_code in [200, 204]:
                        success = True
                        self.session_stats['screenshots_sent'] += 1
                except Exception as e:
                    smart_logger.log(f"⚠️  Discord screenshot lỗi: {e}", force=True)
            
            return success
        
        except Exception as e:
            smart_logger.log(f"❌ Screenshot capture lỗi: {e}", force=True)
            return False
    
    def send_error_notification(self, account: str, error_msg: str, device = None):
        """
        Send error notification with screenshot (NEW v1.4.3)
        
        Args:
            account: Account name
            error_msg: Error message
            device: Device object for screenshot
        """
        if self._is_filtered("error"):
            return
        
        # Format messages
        timestamp = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')
        
        telegram_msg = f"""🚨 <b>LỖI NGHIÊM TRỌNG</b>

📱 Account: <b>{account}</b>
❌ Lỗi: <code>{error_msg}</code>

⏰ {timestamp}
🔔 AT Tool v1.4.3"""
        
        discord_msg = f"""🚨 **LỖI NGHIÊM TRỌNG**

📱 Account: **{account}**
❌ Lỗi: ```{error_msg}```

⏰ {timestamp}
🔔 AT Tool v1.4.3"""
        
        # Send notifications
        if self.telegram_enabled:
            self.send_telegram(telegram_msg)
        
        if self.discord_enabled:
            self.send_discord(discord_msg)
        
        # Send to webhook
        if self.webhook_enabled:
            self.send_webhook({
                'type': 'error',
                'account': account,
                'error': error_msg,
                'timestamp': timestamp
            })
        
        # Send screenshot if enabled and device available
        if device and self.screenshot_on_error:
            self.capture_and_send_screenshot(device, f'Lỗi: {account}')
        
        # Log to history
        self._add_to_history('error', account, error_msg)
    
    def send_checkpoint_notification(self, account: str, device = None):
        """
        Send checkpoint critical alert (NEW v1.4.3)
        
        Args:
            account: Account name
            device: Device object
        """
        timestamp = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')
        
        telegram_msg = f"""🚨 <b>CHECKPOINT - CRITICAL</b>

📱 Account: <b>{account}</b>
⚠️  Status: <b>BỊ CHECKPOINT</b>
❌ Không thể hoạt động

📸 Screenshot đã được gửi
⏰ {timestamp}
🔔 AT Tool v1.4.3"""
        
        discord_msg = f"""🚨 **CHECKPOINT - CRITICAL**

📱 Account: **{account}**
⚠️  Status: **BỊ CHECKPOINT**
❌ Không thể hoạt động

📸 Screenshot đã được gửi
⏰ {timestamp}
🔔 AT Tool v1.4.3"""
        
        # Send with high priority
        if self.telegram_enabled:
            self.send_telegram(telegram_msg)
        
        if self.discord_enabled:
            self.send_discord(discord_msg)
        
        if self.webhook_enabled:
            self.send_webhook({
                'type': 'checkpoint',
                'severity': 'critical',
                'account': account,
                'timestamp': timestamp
            })
        
        # ALWAYS send screenshot for checkpoint
        if device and self.screenshot_on_checkpoint:
            self.capture_and_send_screenshot(device, f"🚨 CHECKPOINT: {account}")
        
        # Log
        self._add_to_history('checkpoint', account, 'Account checkpoint detected')
    
    def send_daily_report(self, stats: Dict):
        """
        Send daily summary report (NEW v1.4.3)
        
        Args:
            stats: Daily statistics dictionary
        """
        if not self.enable_scheduled_reports:
            return
        
        # Check if already sent today
        today = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).date()
        if self.last_daily_report == today:
            return
        
        self.last_daily_report = today
        
        timestamp = datetime.now(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%d/%m/%Y %H:%M:%S')
        
        telegram_msg = f"""📊 <b>BÁO CÁO HÀNG NGÀY</b>

📅 Ngày: <b>{today.strftime('%d/%m/%Y')}</b>

📈 <b>THỐNG KÊ:</b>
• Total Accounts: <b>{stats.get('total_accounts', 0)}</b>
• Sessions: <b>{stats.get('total_sessions', 0)}</b>
• Total Actions: <b>{stats.get('total_actions', 0)}</b>
• Likes: <b>{stats.get('likes', 0)}</b>
• Follows: <b>{stats.get('follows', 0)}</b>
• Comments: <b>{stats.get('comments', 0)}</b>

✅ Success Rate: <b>{stats.get('success_rate', 0):.1f}%</b>
❌ Errors: <b>{stats.get('errors', 0)}</b>

⏰ {timestamp}
🔔 AT Tool v1.4.3"""
        
        discord_msg = f"""📊 **BÁO CÁO HÀNG NGÀY**

📅 Ngày: **{today.strftime('%d/%m/%Y')}**

📈 **THỐNG KÊ:**
• Total Accounts: **{stats.get('total_accounts', 0)}**
• Sessions: **{stats.get('total_sessions', 0)}**
• Total Actions: **{stats.get('total_actions', 0)}**
• Likes: **{stats.get('likes', 0)}**
• Follows: **{stats.get('follows', 0)}**
• Comments: **{stats.get('comments', 0)}**

✅ Success Rate: **{stats.get('success_rate', 0):.1f}%**
❌ Errors: **{stats.get('errors', 0)}**

⏰ {timestamp}
🔔 AT Tool v1.4.3"""
        
        if self.telegram_enabled:
            self.send_telegram(telegram_msg)
        
        if self.discord_enabled:
            self.send_discord(discord_msg)
        
        if self.webhook_enabled:
            self.send_webhook({
                'type': 'daily_report',
                'date': today.isoformat(),
                'stats': stats,
                'timestamp': timestamp
            })
    
    def get_notification_stats(self) -> Dict:
        """Get notification statistics (NEW v1.4.3)"""
        return {
            'total_sent': self.session_stats['notifications_sent'],
            'telegram': self.session_stats['telegram_sent'],
            'discord': self.session_stats['discord_sent'],
            'webhook': self.session_stats['webhook_sent'],
            'screenshots': self.session_stats['screenshots_sent'],
            'errors': self.session_stats['errors'],
            'retries': self.session_stats['retries'],
            'history_size': len(self.notification_history),
            'last_daily_report': self.last_daily_report.isoformat() if self.last_daily_report else None
        }
    
    def _is_filtered(self, level: str) -> bool:
        """Check if notification should be filtered"""
        level_priority = {
            'debug': 0,
            'info': 1,
            'warning': 2,
            'error': 3,
            'critical': 4
        }
        
        min_priority = level_priority.get(self.min_importance, 1)
        current_priority = level_priority.get(level, 1)
        
        return current_priority < min_priority
    
    def _check_rate_limit(self) -> bool:
        """Check rate limiting"""
        if not self.enable_rate_limit:
            return True
        
        now = time.time()
        # Remove old entries
        self.rate_limit_window = [t for t in self.rate_limit_window if now - t < 60]
        
        if len(self.rate_limit_window) >= self.max_per_minute:
            return False
        
        self.rate_limit_window.append(now)
        return True
    
    def _add_to_history(self, notif_type: str, account: str, message: str):
        """Add notification to history"""
        self.notification_history.append({
            'type': notif_type,
            'account': account,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Trim history if too large
        if len(self.notification_history) > self.max_history_size:
            self.notification_history = self.notification_history[-self.max_history_size:]
# ═══════════════════════════════════════════════════════════════
    # 🆕 ULTIMATE NOTIFICATION METHODS v1.4.3
    # ═══════════════════════════════════════════════════════════════
    
# ENHANCED TIMING CALCULATOR v1.4.3
# ✨ Độ chính xác tuyệt đối - Bao gồm wait + rest time
# ═══════════════════════════════════════════════════════════════
    