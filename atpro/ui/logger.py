"""
╔══════════════════════════════════════════════════════╗
║           ui/logger.py - v1.4.5                      ║
║   SmartLogger - Async non-blocking activity logger   ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → SmartLogger (line ~2461)

Features:
  - Async logging (non-blocking console.print)
  - Log box cố định 25 dòng
  - Export logs ra file
  - Stats tracking (success/error/warning/info)
"""

import json
from datetime import datetime
from queue import Queue
from typing import Dict, List, Optional, Set
import threading

import pytz
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich import box

from .constants import ColorScheme

console = Console()


class SmartLogger:
    """
    Logger thông minh với async background worker.

    Dùng queue để print logs trong background thread,
    giữ cho main farming loop không bị chặn bởi I/O.
    """

    def __init__(self, max_logs_display: int = 25):
        self.max_logs_display = max_logs_display
        self.logs: List[Dict] = []
        self.display_logs: List[Dict] = []
        self._tool_instance = None  # Set by TikTokFarmApp để push vào recent_logs
        self.stats = {
            "total": 0,
            "success": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
        }

        self.important_keywords = [
            "✅", "❌", "⚠️", "🔄", "💫", "🎯", "⏱️",
            "switch", "chuyển", "hoàn thành", "thất bại", "lỗi", "đã",
            "verify", "check", "popup", "proxy", "checkpoint",
            "khỏe", "bị khóa", "like", "follow", "comment",
            "shop", "notification", "delay", "wait",
            "scan", "profile", "account",
        ]

        # ── Async worker ──────────────────────────
        self.enable_async = True
        self.log_queue: Queue = Queue()
        self.async_worker: Optional[threading.Thread] = None

        if self.enable_async:
            self._start_async_worker()

    # ─────────────────────────────────────────
    # Async worker
    # ─────────────────────────────────────────

    def _start_async_worker(self):
        """
        v1.4.3 BUILD 3: Start async logging worker thread
        
        Benefits:
        - console.print() doesn't block main thread
        - Logs printed in background
        - Tool stays responsive
        """
        import threading
        
        def worker():
            """Background worker for async logging"""
            while True:
                try:
                    # Get log task from queue (blocking)
                    task = self.log_queue.get()
                    
                    if task is None:  # Shutdown signal
                        break
                    
                    # Unpack task
                    color, timestamp, message = task
                    
                    # Print to console (in background thread)
                    console.print(f"[{color}][{timestamp}] {message}[/{color}]")
                    
                except Exception as e:
                    # Log error but don't crash worker
                    print(f"[Async Log Error] {e}")
                
                finally:
                    # Mark task as done
                    self.log_queue.task_done()
        
        # Create and start daemon thread
        self.async_worker = threading.Thread(target=worker, daemon=True)
        self.async_worker.start()
    
    def _queue_log_output(self, color: str, timestamp: str, message: str):
        """Queue a log entry for async printing"""
        if self.enable_async and self.async_worker and self.async_worker.is_alive():
            self.log_queue.put((color, timestamp, message))
        else:
            console.print(f"[{color}][{timestamp}] {message}[/{color}]")

    def shutdown_async_worker(self):
        """Gracefully shutdown async worker. Call before app exit."""
        if self.async_worker and self.async_worker.is_alive():
            self.log_queue.put(None)  # Poison pill
            import time
            time.sleep(0.5)

    # ─────────────────────────────────────────
    # Logging
    # ─────────────────────────────────────────

    def _categorize_log(self, message: str) -> str:
        msg_lower = message.lower()
        if "✅" in message or "hoàn thành" in msg_lower:
            self.stats["success"] += 1
            return "success"
        elif "❌" in message or "lỗi" in msg_lower:
            self.stats["error"] += 1
            return "error"
        elif "⚠️" in message or "warning" in msg_lower:
            self.stats["warning"] += 1
            return "warning"
        else:
            self.stats["info"] += 1
            return "info"

    def log(self, message: str, force: bool = False, level: str = "auto"):
        """
        Log a message.

        Args:
            message: Message to log
            force:   Always log, skip importance filter
            level:   "auto" | "success" | "error" | "warning" | "info"
        """
        should_log = force or any(
            k.lower() in message.lower() for k in self.important_keywords
        )

        if not should_log:
            return

        tz = pytz.timezone("Asia/Ho_Chi_Minh")
        timestamp = datetime.now(tz).strftime("%H:%M:%S")
        log_type = self._categorize_log(message) if level == "auto" else level

        log_entry = {"timestamp": timestamp, "message": message, "type": log_type}
        self.logs.append(log_entry)
        self.stats["total"] += 1

        self.display_logs.append(log_entry)
        if len(self.display_logs) > self.max_logs_display:
            self.display_logs.pop(0)

        color_map = {
            "success": "bright_green",
            "error": "bright_red",
            "warning": "bright_yellow",
            "info": "dim",
        }
        color = color_map.get(log_type, "dim")
        self._queue_log_output(color, timestamp, message)

        # Push vào recent_logs của TikTokFarmApp (để hiển thị real-time)
        if self._tool_instance is not None:
            try:
                color_map2 = {
                    "success": "bright_green",
                    "error":   "bright_red",
                    "warning": "bright_yellow",
                    "info":    "dim",
                }
                c = color_map2.get(log_type, "dim")
                self._tool_instance.recent_logs.append(
                    f"[{c}][{timestamp}] {message}[/{c}]"
                )
            except Exception:
                pass

    # ─────────────────────────────────────────
    # UI component
    # ─────────────────────────────────────────

    def get_log_box(self) -> Panel:
        """Return a Rich Panel showing recent activity"""
        if not self.display_logs:
            content = Align.center(
                "[dim italic]Chưa có hoạt động nào...[/dim italic]",
                vertical="middle",
            )
        else:
            icon_map = {
                "success": "✅",
                "error": "❌",
                "warning": "⚠️",
                "info": "ℹ️",
            }
            color_map = {
                "success": ColorScheme.SUCCESS,
                "error": ColorScheme.ERROR,
                "warning": ColorScheme.WARNING,
                "info": ColorScheme.INFO,
            }
            lines = []
            for entry in self.display_logs:
                color = color_map.get(entry["type"], ColorScheme.TEXT_PRIMARY)
                icon = icon_map.get(entry["type"], "•")
                lines.append(
                    f"[{color}]{icon} [{entry['timestamp']}] {entry['message']}[/{color}]"
                )
            content = "\n".join(lines)

        footer = (
            f"[{ColorScheme.SUCCESS}]✅ {self.stats['success']}[/{ColorScheme.SUCCESS}]  "
            f"[{ColorScheme.ERROR}]❌ {self.stats['error']}[/{ColorScheme.ERROR}]  "
            f"[{ColorScheme.WARNING}]⚠️ {self.stats['warning']}[/{ColorScheme.WARNING}]  "
            f"[dim]Total: {self.stats['total']}[/dim]"
        )

        return Panel(
            content,
            title=(
                f"[bold {ColorScheme.PRIMARY}]📋 Activity Monitor "
                f"({len(self.display_logs)}/{self.max_logs_display})"
                f"[/bold {ColorScheme.PRIMARY}]"
            ),
            subtitle=footer,
            border_style=ColorScheme.PRIMARY,
            box=box.ROUNDED,
            padding=(1, 2),
        )

    # ─────────────────────────────────────────
    # Reset / Export
    # ─────────────────────────────────────────

    def reset(self):
        """Reset display logs and counters (keep full log history)"""
        self.display_logs = []
        self.stats = {
            "total": 0,
            "success": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
        }

    def reset_all(self):
        """Reset everything including full log history"""
        self.logs = []
        self.reset()

    def get_logs(self) -> List[Dict]:
        return self.logs.copy()

    def export_logs(self, filename: str = None) -> bool:
        """Export logs to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"at_tool_logs_{timestamp}.json"

        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "logs": self.logs,
                        "stats": self.stats,
                        "exported_at": datetime.now().isoformat(),
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            self.log(f"✅ Exported logs to {filename}", force=True)
            return True
        except Exception as e:
            self.log(f"❌ Failed to export logs: {e}", force=True)
            return False


# ─────────────────────────────────────────
# Global singleton
# ─────────────────────────────────────────
smart_logger = SmartLogger(max_logs_display=25)
