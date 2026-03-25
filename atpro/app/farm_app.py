"""
app/farm_app.py - v1.4.6  Blue Edition
"""
import os, random, time
from collections import deque
from datetime import datetime
from typing import List, Optional, Tuple, Type

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.align import Align
    from rich.columns import Columns
    from rich.prompt import Prompt, Confirm, IntPrompt, FloatPrompt
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.live import Live
    from rich.text import Text
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False; console = None

try:
    import pytz; vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
except ImportError:
    vn_tz = None

import traceback
from ui.logger import smart_logger


# ================================================================
#  BANNER  v1.4.6  -  Blue Edition
#  Unicode box-drawing + block letters
# ================================================================

_BANNER_RAW = """[bold bright_blue]    ╔═══════════════════════════════════════════════════════════╗
    ║     █████╗ ████████╗   ████████╗ ██████╗  ██████╗ ██╗   ║
    ║    ██╔══██╗╚══██╔══╝   ╚══██╔══╝██╔═══██╗██╔═══██╗██║   ║
    ║    ███████║   ██║         ██║   ██║   ██║██║   ██║██║   ║
    ║    ██╔══██║   ██║         ██║   ██║   ██║██║   ██║██║   ║
    ║    ██║  ██║   ██║         ██║   ╚██████╔╝╚██████╔╝███████╗║
    ║    ╚═╝  ╚═╝   ╚═╝         ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝║
    ║[/bold bright_blue][cyan]        🔵 Auto TikTok Tool  v1.4.6  Blue Edition 🔵       [/cyan][bold bright_blue]║
    ╚═══════════════════════════════════════════════════════════╝[/bold bright_blue]"""


def show_banner(subtitle: str = ""):
    """Banner Unicode box-drawing + block letters - giong v1.4.4."""
    if not RICH_AVAILABLE:
        print("=" * 62)
        print("   AT TOOL v1.4.6  --  Blue Edition")
        if subtitle:
            print(f"   >> {subtitle}")
        print("=" * 62)
        return
    try:
        os.system("clear" if os.name != "nt" else "cls")
    except Exception:
        pass
    now = datetime.now()
    try:
        if vn_tz: now = datetime.now(vn_tz)
    except Exception: pass
    ts = now.strftime("%H:%M:%S")
    ds = now.strftime("%d/%m/%Y")

    console.print(_BANNER_RAW)
    console.print()

    b_ver = "[bold white on blue] v1.4.6 [/bold white on blue]"
    b_ed  = "[bold white on blue] BLUE EDITION [/bold white on blue]"
    b_ai  = "[bold white on blue] AI-POWERED [/bold white on blue]"
    clock = f"[cyan]{ts}[/cyan]  [white]{ds}[/white]"
    if subtitle:
        bar = (f"  {b_ver} {b_ed} {b_ai}  {clock}\n"
               f"  [bright_blue]>[/bright_blue] [bright_white]{subtitle}[/bright_white]")
    else:
        bar = f"  {b_ver} {b_ed} {b_ai}  {clock}"
    console.print(Panel(bar, border_style="blue", box=box.HORIZONTALS, padding=(0, 1)))
    console.print()


def loading_effect(msg: str = "Dang tai...", duration: float = 1.0):
    if not RICH_AVAILABLE:
        print(f"... {msg}"); time.sleep(duration); return
    with Progress(
        SpinnerColumn("dots", style="bright_blue"),
        TextColumn(f"[cyan]{msg}"),
        BarColumn(bar_width=30, style="blue", complete_style="bright_blue"),
        TextColumn("[bright_blue]{task.percentage:>3.0f}%"),
        console=console, transient=True,
    ) as prog:
        task = prog.add_task("", total=100)
        steps = max(10, int(duration * 20))
        for _ in range(steps):
            prog.update(task, advance=100 / steps)
            time.sleep(duration / steps)


def _badge(number: str, color: str = "blue") -> str:
    return f"[bold white on {color}] {number} [/bold white on {color}]"


def _status(enabled: bool) -> str:
    return ("[bold white on blue] ON [/bold white on blue]" if enabled
            else "[white on grey23] OFF [/white on grey23]")


class TikTokFarmApp:
    """Main App v1.4.6 — Neon UI Edition"""

    def __init__(self):
        from core.config import ConfigManager
        from models import AIAPIKeyManager, ProxyManager
        from ui.notifications import NotificationManager
        from ui.ultimate_ui import ultimate_ui
        from ui.constants import ColorScheme
        from utils.progress_tracker import ProgressTracker

        self.config_manager   = ConfigManager()
        self.config           = self.config_manager.config
        self.progress_tracker = ProgressTracker()
        self.notification_manager = NotificationManager()
        self.recent_logs      = deque(maxlen=25)
        self._ultimate_ui     = ultimate_ui
        self._ColorScheme     = ColorScheme

        # v1.4.4: AI + Proxy managers
        self.ai_key_manager = AIAPIKeyManager()
        self.proxy_manager  = ProxyManager()
        self.ai_handler     = None
        self.popup_handler  = None

        if self.config.ai_popup_enabled and self.ai_key_manager.get_active_key():
            try:
                from ai import AIPopupHandler, TwoLayerPopupHandler
                self.ai_handler   = AIPopupHandler(self.ai_key_manager)
                self.popup_handler = TwoLayerPopupHandler(self.ai_handler, self.config)
            except Exception as e:
                print(f"⚠️  Khởi tạo AI thất bại: {e}")

        self._last_ui_update      = 0
        self._divine_eye_counter  = 0
        self._video_count         = 0

    # ──────────────────────────────────────────────────────────────
    # Progress display (giống hệt v1.4.4)
    # ──────────────────────────────────────────────────────────────

    def show_detailed_progress(self, account_name, account_idx, total_accounts,
                               elapsed_seconds, total_seconds, formatted_total,
                               account_elapsed, account_duration):
        if not RICH_AVAILABLE:
            return

        overall_percent = min(100, int((elapsed_seconds / max(1, total_seconds)) * 100))
        account_percent = min(100, int((account_elapsed / max(1, account_duration)) * 100))

        elapsed_h = elapsed_seconds // 3600
        elapsed_m = (elapsed_seconds % 3600) // 60
        elapsed_str = f"{elapsed_h}h{elapsed_m:02d}m" if elapsed_h else f"{elapsed_m}m"

        BAR = 35
        ov_filled  = int(BAR * overall_percent / 100)
        ac_filled  = int(BAR * account_percent / 100)
        overall_bar = "▰" * ov_filled  + "▱" * (BAR - ov_filled)
        account_bar = "▰" * ac_filled  + "▱" * (BAR - ac_filled)

        overall_content = (
            f"[bold bright_cyan]{overall_bar}[/bold bright_cyan] [bold bright_yellow]{overall_percent}%[/bold bright_yellow]\n"
            f"[dim bright_white]Đã chạy:[/dim bright_white] [bright_green]{elapsed_str}[/bright_green] / [bright_cyan]{formatted_total}[/bright_cyan]"
        )
        overall_panel = Panel(overall_content,
            title="[bold bright_cyan]╔═══ TIẾN ĐỘ TỔNG ═══╗[/bold bright_cyan]",
            border_style="bright_cyan", box=box.HEAVY_EDGE)

        account_m       = account_elapsed // 60
        account_total_m = account_duration // 60
        actions_summary = self.progress_tracker.get_current_summary()

        account_content = (
            f"[bold bright_yellow]Account:[/bold bright_yellow] [bold bright_green]{account_name}[/bold bright_green] "
            f"[dim bright_white]({account_idx}/{total_accounts})[/dim bright_white]\n\n"
            f"[bold cyan]Farm:[/bold cyan] [bold cyan]{account_bar}[/bold cyan] [bold bright_yellow]{account_percent}%[/bold bright_yellow]\n"
            f"[dim bright_white]Thời gian:[/dim bright_white] [bright_green]{account_m}m[/bright_green] / [bright_cyan]{account_total_m}m[/bright_cyan]\n\n"
            f"[bold cyan]Actions:[/bold cyan] {actions_summary}"
        )
        account_panel = Panel(account_content,
            title="[bold bright_yellow]╔═══ ACCOUNT HIỆN TẠI ═══╗[/bold bright_yellow]",
            border_style="bright_blue", box=box.HEAVY_EDGE)

        self._ultimate_ui.clear_screen_animated()
        console.print(overall_panel)
        console.print()
        console.print(account_panel)
        console.print()

        if self.recent_logs:
            log_text = "\n".join(list(self.recent_logs)[-25:])
            console.print(Panel(log_text,
                title="[bold bright_green]📋 LOGS (Real-time)[/bold bright_green]",
                border_style="bright_cyan", box=box.ROUNDED))
        console.print()

    # ──────────────────────────────────────────────────────────────
    # Setup helpers
    # ──────────────────────────────────────────────────────────────

    def _setup_notifications(self) -> Tuple[List, float]:
        """
        v1.4.3: Setup notification managers
        
        Returns:
            Tuple of (account_details list, session_start_time)
        """
        # Link SmartLogger
        smart_logger._tool_instance = self
        
        # Configure notification managers
        if self.config.telegram_enabled:
            self.notification_manager.configure_telegram(
                self.config.telegram_bot_token,
                self.config.telegram_chat_id
            )
        
        if self.config.discord_enabled:
            self.notification_manager.configure_discord(
                self.config.discord_webhook_url
            )
        
        # Initialize tracking variables
        account_details = []
        session_start_time = time.time()
        
        return account_details, session_start_time
    
    def _setup_farm_environment(self, device):
        from core.automation import TikTokAutomation
        from utils.ui_helper import UIHelper

        self._ultimate_ui.clear_screen_animated()
        show_banner()
        console.print()

        if self.config.proxy.enabled:
            if not UIHelper.apply_proxy(device, self.config.proxy):
                self._ultimate_ui.show_message("⚠️  Proxy không hoạt động, tiếp tục không proxy", "warning")
                time.sleep(2)

        automation = TikTokAutomation(device, self.config)

        if self.config.track_device_info and self.config.log_device_info_on_start:
            try:
                from core.device_manager import DeviceManager, DeviceHardwareInfo
                devices = DeviceManager.list_devices()
                if devices:
                    device_info = DeviceHardwareInfo.get_device_info(devices[0])
                    console.print(Panel(
                        DeviceHardwareInfo.format_device_info(device_info),
                        title="[bold bright_cyan]💻 DEVICE INFO[/bold bright_cyan]",
                        border_style="bright_blue", box=box.ROUNDED, padding=(1, 2)))
                    console.print()
                    time.sleep(2)
            except Exception:
                pass

        return automation

    def _initialize_tiktok(self, automation):
        """Khởi tạo TikTok và lấy danh sách acc — giống hệt v1.4.4."""
        # Bước 1: Mở TikTok
        with console.status("[cyan]🚀 Đang mở TikTok...[/cyan]", spinner="dots"):
            if not automation.open_tiktok():
                self._ultimate_ui.show_message("❌ Không thể mở TikTok!", "error")
                return []
            time.sleep(1)
        self._ultimate_ui.show_message("✅ Đã mở TikTok", "success")

        # Bước 2: Chờ feed load
        with console.status("[yellow]⏳ Đang chờ feed load...[/yellow]", spinner="dots"):
            automation.wait_feed_load()
            time.sleep(1)
        self._ultimate_ui.show_message("✅ Feed đã load", "success")

        # Bước 3: Vào hồ sơ
        with console.status("[cyan]👤 Đang vào hồ sơ...[/cyan]", spinner="dots"):
            if not automation.click_profile_button():
                self._ultimate_ui.show_message("❌ Không vào được hồ sơ!", "error")
                return []
            time.sleep(5.0)  # Chờ hồ sơ load xong
        self._ultimate_ui.show_message("✅ Đã vào hồ sơ", "success")

        # Bước 4: Mở popup danh sách tài khoản
        with console.status("[magenta]📋 Đang lấy danh sách tài khoản...[/magenta]", spinner="dots"):
            if not automation.open_account_switch_popup():
                self._ultimate_ui.show_message("❌ Không mở được popup!", "error")
                automation.exit_profile_mode()
                return []
            time.sleep(1)

        # Bước 5: Lấy danh sách
        accounts = automation.get_account_list()
        if not accounts:
            self._ultimate_ui.show_message("❌ Không tìm thấy tài khoản nào!", "error")
            automation.exit_profile_mode()
            return []

        self._ultimate_ui.show_message(f"✅ Tìm thấy {len(accounts)} tài khoản", "success")

        # Bước 6: Thoát popup + trở về feed
        from utils.ui_helper import UIHelper
        automation.exit_profile_mode()
        UIHelper.safe_back_to_feed(automation.device, max_attempts=1, delay=1.0)

        console.print()
        return accounts


    def _apply_priority_farming(self, accounts, stats_manager):
        if not self.config.enable_priority_farming:
            return accounts
        console.print("[cyan]🏆 Applying Priority Farming...[/cyan]")
        try:
            from core.priority_account import PriorityAccountManager
            sorted_accs = PriorityAccountManager.sort_accounts_by_priority(accounts, stats_manager)
            self._ultimate_ui.show_message("✅ Đã sắp xếp accounts theo ưu tiên", "success")
            console.print()
            return sorted_accs
        except Exception as e:
            self._ultimate_ui.show_message(f"⚠️  Lỗi priority: {e}", "warning")
            return accounts

    def _send_start_notification(self, accounts):
        if not ((self.config.telegram_enabled and self.config.telegram_notify_start) or
                (self.config.discord_enabled  and self.config.discord_notify_start)):
            return
        try:
            discord_msg, tg_msg = self.notification_manager.format_session_start(len(accounts))
            self.notification_manager.send_notification(discord_msg, tg_msg)
            console.print(f"[bright_green]✅ Đã gửi thông báo bắt đầu session[/bright_green]")
            time.sleep(1)
        except Exception:
            pass

    def _display_account_list(self, accounts):
        console.print(Panel("[bold bright_cyan]✨ DANH SÁCH TÀI KHOẢN ✨[/bold bright_cyan]",
                            border_style="bright_cyan", box=box.DOUBLE, padding=(0, 2)))
        console.print()

        t = Table(box=box.DOUBLE_EDGE, border_style="bright_cyan", show_header=True,
                  header_style="bold bright_cyan", show_lines=True, padding=(0, 2))
        t.add_column("STT", justify="center", style="bold bright_cyan", width=10)
        t.add_column("TÀI KHOẢN", style="bold bright_white", width=35, no_wrap=False)
        t.add_column("TRẠNG THÁI", justify="center", width=25)

        for idx, acc in enumerate(accounts, 1):
            if idx == 1:
                status = "[bold bright_green on #004400]●[/] [bright_green]ĐANG DÙNG[/bright_green]"
                row_style = "on #001a1a"
            else:
                status = "[dim bright_cyan]○[/dim bright_cyan] [dim]Chờ[/dim]"
                row_style = "dim"
            t.add_row(f"[bold]{idx}[/bold]", f"[cyan]{acc}[/cyan]", status, style=row_style)

        console.print(t)
        console.print()

    def _display_farm_configuration(self, accounts=None, formatted_time=""):
        from core.device_manager import TikTokPackage

        package_name = TikTokPackage[self.config.selected_package].display_name

        button_y_info = (f"[bright_cyan]🎯 Nút acc:[/bright_cyan] [cyan]{self.config.custom_account_button_y_px}px[/cyan]"
                         if self.config.use_custom_account_button_y else
                         "[bright_cyan]🎯 Nút acc:[/bright_cyan] [cyan]Auto[/cyan]")

        proxy_info = (f"[cyan]🌐 Proxy:[/cyan] [bright_green]{self.config.proxy.proxy_type}://{self.config.proxy.host}:{self.config.proxy.port}[/bright_green]"
                      if self.config.proxy.enabled else
                      "[cyan]🌐 Proxy:[/cyan] [dim]Tắt[/dim]")

        rest_info = (f"[cyan]😴 Nghỉ giữa acc:[/cyan] [bright_green]{self.config.rest_duration_minutes}m[/bright_green]"
                     if self.config.enable_rest_between_accounts else
                     "[cyan]😴 Nghỉ giữa acc:[/cyan] [dim]Tắt[/dim]")

        console.print(Panel("[bold bright_cyan]📈 THÔNG TIN CHẠY TOOL v1.4.6[/bold bright_cyan]",
                            border_style="bright_cyan", box=box.DOUBLE, padding=(0, 2)))
        console.print()

        col1_content = f"""[bold bright_yellow]📦 GÓI TIKTOK[/bold bright_yellow]
[bright_cyan]{package_name}[/bright_cyan]

[bold bright_yellow]📊 TỔNG TÀI KHOẢN[/bold bright_yellow]
[bold bright_green]{len(accounts)}[/bold bright_green] accounts

[bold bright_yellow]⏱️ PHÚT/TÀI KHOẢN[/bold bright_yellow]
[bright_green]{self.config.minutes_per_account}[/bright_green] phút

[bold bright_yellow]🕐 TỔNG THỜI GIAN[/bold bright_yellow]
[bold bright_cyan]~{formatted_time}[/bold bright_cyan]
[dim](+{self.config.buffer_minutes}m buffer)[/dim]"""

        col2_content = f"""[bold bright_cyan]═══ TỶ LỆ THAO TÁC ═══[/bold bright_cyan]

[cyan]❤️  Like[/cyan]
  [bold bright_green]{self.config.like_rate*100:.0f}%[/bold bright_green]

[cyan]👥 Follow[/cyan]
  [bold bright_green]{self.config.follow_rate*100:.0f}%[/bold bright_green]

[cyan]💬 Comment[/cyan]
  [bold bright_green]{self.config.comment_rate*100:.0f}%[/bold bright_green]

[cyan]📬 Thông báo[/cyan]
  [bold bright_green]{self.config.notification_rate*100:.0f}%[/bold bright_green]

[cyan]🛍️  Cửa hàng[/cyan]
  [bold bright_green]{self.config.shop_rate*100:.0f}%[/bold bright_green]"""

        verify  = "✅ Bật" if self.config.enable_verify_account else "❌ Tắt"
        a1234   = "✅ Bật" if self.config.enable_auto_1234_popup else "❌ Tắt"
        ckpt    = "✅ Bật" if self.config.enable_checkpoint_check else "❌ Tắt"
        popscan = "✅ Bật" if self.config.enable_profile_popup_scan else "❌ Tắt"
        sv      = "✅ ON"  if self.config.enable_smart_video_interaction else "❌ OFF"
        prio    = "✅ ON"  if self.config.enable_priority_farming else "❌ OFF"
        fv      = "✅ ON"  if self.config.enable_follow_verification else "❌ OFF"

        col3_content = f"""[bold bright_yellow]⚙️  TÍNH NĂNG[/bold bright_yellow]

[cyan]Verify Acc:[/cyan] {verify}
[cyan]Auto 1234:[/cyan] {a1234}
[cyan]Checkpoint:[/cyan] {ckpt}
[cyan]Popup Scan:[/cyan] {popscan}
[cyan]Smart Video:[/cyan] {sv}
[cyan]Priority Farm:[/cyan] {prio}
[cyan]Follow Verify:[/cyan] {fv}

{proxy_info}
{rest_info}
{button_y_info}"""

        # -- Bảng cấu hình 4 cột, fixed width, không lệch --
        n_acc = len(accounts) if accounts else "?"
        verify_s  = "ON " if self.config.enable_verify_account else "OFF"
        a1234_s   = "ON " if self.config.enable_auto_1234_popup else "OFF"
        popup_s   = "ON " if self.config.enable_profile_popup_scan else "OFF"
        sv_s      = "ON " if self.config.enable_smart_video_interaction else "OFF"
        prio_s    = "ON " if self.config.enable_priority_farming else "OFF"
        fv_s      = "ON " if self.config.enable_follow_verification else "OFF"

        cfg = Table(box=box.SIMPLE_HEAVY, show_header=False,
                    border_style="bright_blue", padding=(0, 2), expand=False)
        cfg.add_column("", style="cyan",        width=20, no_wrap=True)
        cfg.add_column("", style="bright_white", width=22, no_wrap=True)
        cfg.add_column("", style="cyan",        width=20, no_wrap=True)
        cfg.add_column("", style="bright_white", width=16, no_wrap=True)

        def _r(l1, v1, l2="", v2=""):
            cfg.add_row(l1, v1, l2, v2)

        _r("Goi TikTok",    package_name[:20],
           "Like rate",     f"{self.config.like_rate*100:.0f}%")
        _r("Tai khoan",     str(n_acc),
           "Follow rate",   f"{self.config.follow_rate*100:.0f}%")
        _r("Phut/account",  f"{self.config.minutes_per_account}m",
           "Comment",       f"{self.config.comment_rate*100:.0f}%")
        _r("Tong TG",       f"~{formatted_time}",
           "Thong bao",     f"{self.config.notification_rate*100:.0f}%")
        _r("Verify acc",    verify_s,
           "Cua hang",      f"{self.config.shop_rate*100:.0f}%")
        _r("Auto 1234",     a1234_s,
           "Popup scan",    popup_s)
        _r("Smart video",   sv_s,
           "Priority farm", prio_s)
        _r("Follow verify", fv_s,
           "Proxy", "ON " if self.config.proxy.enabled else "OFF")

        console.print(Panel(
            cfg, border_style="bright_blue", box=box.ROUNDED,
            padding=(0, 1),
            title="[bold bright_cyan]  CAU HINH PHIEN NUOI  [/bold bright_cyan]",
        ))
        console.print()

    def _confirm_farm_start(self, automation, device):
        from utils.ui_helper import UIHelper
        console.print(Panel(
            "[bold bright_yellow]⚡ Bắt đầu nuôi tất cả tài khoản?[/bold bright_yellow]\n\n"
            "[dim]Công cụ sẽ tự động farm theo cấu hình trên.[/dim]",
            border_style="bright_blue", box=box.DOUBLE, padding=(1, 2)))
        console.print()

        if not Confirm.ask("[bold bright_cyan]❯[/bold bright_cyan] Xác nhận", default=True):
            self._ultimate_ui.show_message("❌ Đã hủy", "warning")
            try:
                automation.exit_profile_mode()
            except Exception:
                pass
            return False

        console.print()
        with console.status("[cyan]⬅️  Đang quay về feed...[/cyan]", spinner="dots"):
            try:
                UIHelper.safe_back_to_feed(device, max_attempts=1, delay=1.0)
                automation.exit_profile_mode()
            except Exception:
                pass

        console.print()
        console.print(Panel("[bold bright_cyan]🌱 BẮT ĐẦU NUÔI TÀI KHOẢN 🌱[/bold bright_cyan]",
                            border_style="bright_cyan", box=box.DOUBLE, padding=(0, 2)))
        console.print()
        return True

    def _send_milestone_notification(self, current_idx, total_accounts):
        if current_idx % 10 != 0:
            return
        if not ((self.config.telegram_enabled and self.config.telegram_notify_milestone) or
                (self.config.discord_enabled   and self.config.discord_notify_milestone)):
            return
        try:
            now_str = (datetime.now(vn_tz) if vn_tz else datetime.now()).strftime("%H:%M:%S")
            discord_msg = f"📊 **PROGRESS UPDATE**\n\nĐã hoàn thành: **{current_idx}/{total_accounts}** accounts\n⏰ {now_str}"
            tg_msg      = f"📊 <b>PROGRESS UPDATE</b>\n\nĐã hoàn thành: <b>{current_idx}/{total_accounts}</b> accounts\n⏰ {now_str}"
            self.notification_manager.send_notification(discord_msg, tg_msg)
        except Exception:
            pass

    def _finalize_session(self, accounts, account_details, session_start_time, formatted_time, automation, device):
        from utils.ui_helper import UIHelper
        console.print()
        console.print()

        total_summary = self.progress_tracker.get_total_summary()

        # Send completion notification
        if ((self.config.telegram_enabled and self.config.telegram_notify_complete) or
            (self.config.discord_enabled   and self.config.discord_notify_complete)):
            try:
                total_actions = {"like": 0, "follow": 0, "comment": 0, "share": 0, "shop": 0}
                successful = sum(1 for a in account_details if a["status"] == "success")
                failed     = sum(1 for a in account_details if a["status"] != "success")
                for acc in account_details:
                    for k, v in acc["actions"].items():
                        if k in total_actions:
                            total_actions[k] += v

                session_stats = {
                    "total_accounts":      len(account_details),
                    "successful_accounts": successful,
                    "failed_accounts":     failed,
                    "total_actions":       total_actions,
                    "duration_seconds":    int(time.time() - session_start_time),
                }
                discord_msg, tg_msg = self.notification_manager.format_session_complete(
                    session_stats, account_details)
                self.notification_manager.send_notification(discord_msg, tg_msg)
                console.print("[bright_green]✅ Đã gửi báo cáo hoàn thành![/bright_green]")
            except Exception as e:
                console.print(f"[bright_yellow]⚠️  Không gửi được báo cáo: {str(e).replace('[','[')[:80]}[/bright_yellow]")

        # Completion panel
        console.print(Panel(
            Align.center(
                f"[bold bright_cyan]\n🎉🎉🎉 HOÀN THÀNH! 🎉🎉🎉\n\n"
                f"✅ Đã nuôi {len(accounts)} tài khoản\n"
                f"⏱️  Tổng thời gian: ~{formatted_time}\n"
                f"📊 Tổng thao tác: {total_summary}\n"
                f"💯 Dữ liệu đã lưu vào thống kê!\n[/bold bright_cyan]"
            ),
            border_style="bright_cyan", box=box.HEAVY_EDGE,
            title="[bold bright_yellow]⭐ THÀNH CÔNG ⭐[/bold bright_yellow]"
        ))

        # ── AI Quota Status ──────────────────────────────────
        if self.ai_handler is not None:
            try:
                quota_status = self.ai_handler.get_quota_status()
                if quota_status.get("exhausted_keys") or quota_status.get("partial_keys"):
                    console.print()
                    from rich.table import Table
                    aq = Table(
                        title="[bold bright_cyan]🤖 AI QUOTA STATUS[/bold bright_cyan]",
                        box=box.ROUNDED, border_style="bright_blue", show_header=True,
                        header_style="bold bright_cyan")
                    aq.add_column("Tên key",   style="bright_white",  width=20)
                    aq.add_column("Model",     style="bright_cyan",   width=28)
                    aq.add_column("Tình trạng",style="bold",          width=22)
                    all_keys = self.ai_key_manager.get_all_keys()
                    for k in all_keys:
                        if k.is_quota_exhausted:
                            st = "[bright_red]✖ Hết quota hoàn toàn[/bright_red]"
                        elif k.exhausted_models:
                            st = f"[cyan]⚡ {len(k.exhausted_models)} model đã hết[/cyan]"
                        else:
                            st = "[bright_green]✅ Còn đầy[/bright_green]"
                        aq.add_row(k.name, k.model, st)
                    console.print(aq)
                    console.print("[dim]  Dùng menu AI → Reset quota để đặt lại cho phiên sau[/dim]")
            except Exception:
                pass

        # ── Divine Eye statistics ────────────────────────────
        try:
            import core.detection as _det_mod
            _de = getattr(_det_mod, "divine_eye", None)
            if _de is not None:
                console.print()
                self._ultimate_ui.show_section_divider("DIVINE EYE STATISTICS", "🔮", style="cyan")
                stats = _de.get_stats()
                self._ultimate_ui.show_mega_stats({
                    "Tổng lần detect": f"{stats.get('total_detections', 0):,}",
                    "Cache hit rate":  stats.get("cache_hit_rate", "N/A"),
                    "Avg detect time": f"{stats.get('avg_detection_time_ms', 0):.1f}ms",
                    "Tổng thời gian":  f"{stats.get('total_time_seconds', 0):.1f}s",
                }, "AI Vision Performance", show_bars=False)
                console.print()
        except Exception:
            pass

        if self.config.proxy.enabled:
            try:
                UIHelper.remove_proxy(device)
            except Exception:
                pass
        try:
            automation.close_tiktok()
        except Exception:
            pass

    # ──────────────────────────────────────────────────────────────
    # run_farm
    # ──────────────────────────────────────────────────────────────

    def run_farm(self, device):
        """
        v1.4.3: Main farm flow - REFACTORED
        
        Orchestrates the farming process by coordinating smaller, 
        focused methods. Each step is now testable and maintainable.
        """
        # ── v1.4.6: modular imports ──────────────────────────────────────
        from core.stats import StatsManager, FarmSession
        from core.detection import divine_eye, DIVINE_EYE_AVAILABLE, ScreenState
        from core.priority_account import FollowVerifier
        from utils.xml_parser import XMLParser
        from utils.ui_helper import UIHelper
        from utils.progress_tracker import ProgressTracker
        from core.video_interaction import SmartVideoInteraction
        from ui.logger import smart_logger
        from ui.constants import AppConstants

        # ═══════════════════════════════════════════════════════════════
        # PHASE 1: SETUP & INITIALIZATION
        # ═══════════════════════════════════════════════════════════════
        
        # Setup notifications and tracking
        account_details, session_start_time = self._setup_notifications()
        
        # Setup environment (proxy, device info, banner)
        automation = self._setup_farm_environment(device)
        
        # Initialize TikTok and get accounts
        accounts = self._initialize_tiktok(automation)
        if not accounts:
            return
        
        # Initialize stats manager
        stats_manager = StatsManager()
        
        # Apply priority farming if enabled
        accounts = self._apply_priority_farming(accounts, stats_manager)
        
        # ═══════════════════════════════════════════════════════════════
        # PHASE 2: DISPLAY & CONFIRMATION ✅ REFACTORED
        # ═══════════════════════════════════════════════════════════════
        
        # Send start notification
        self._send_start_notification(accounts)
        
        # Display account list
        self._display_account_list(accounts)
        
        # ═══════════════════════════════════════════════════════════════
        # DISPLAY CONFIGURATION ✅ REFACTORED (Phase 4)
        # ═══════════════════════════════════════════════════════════════
        total_seconds, formatted_time = self.config.calculate_total_time(len(accounts))
        self._display_farm_configuration(accounts, formatted_time)
        
        # USER CONFIRMATION ✅ REFACTORED
        # ═══════════════════════════════════════════════════════════════
        # ═══════════════════════════════════════════════════════════════
        # PHASE 3: MAIN FARMING LOOP
        # ═══════════════════════════════════════════════════════════════
        
        duration = self.config.minutes_per_account * 60
        
        self.progress_tracker = ProgressTracker()
        
        start_time = time.time()
        # vn_tz từ module-level
        
        # Main farm loop
        for idx, account in enumerate(accounts, 1):
            self.progress_tracker.reset_current()
            
            account_start_time = datetime.now(vn_tz)
            account_start = time.time()
            account_end = account_start + duration
            
            # ═══════════════════════════════════════════════════════════════
            # v1.4.3: TRACKING VARIABLES FOR NOTIFICATIONS
            # ═══════════════════════════════════════════════════════════════
            account_actions = {'like': 0, 'follow': 0, 'comment': 0, 'share': 0, 'shop': 0}
            account_errors = []
            account_status = "success"
            account_follow_status = "unknown"
            
            # v1.4.3: Lưu checkpoint status
            current_checkpoint_status = "unknown"
            
            while time.time() < account_end:
                elapsed_total = int(time.time() - start_time)
                elapsed_account = int(time.time() - account_start)
                
                # ═══════════════════════════════════════════════════════
                # v1.4.3 BUILD 4: THROTTLE UI UPDATES
                # Only update UI every N seconds to prevent blocking
                # ═══════════════════════════════════════════════════════
                if not hasattr(self, 'last_ui_update'):
                    self.last_ui_update = 0
                
                current_time = time.time()
                ui_update_interval = 2.0  # Update every 2 seconds
                
                if current_time - self.last_ui_update >= ui_update_interval:
                    self.show_detailed_progress(
                        account, idx, len(accounts),
                        elapsed_total, total_seconds, formatted_time,
                        elapsed_account, duration
                    )
                    self.last_ui_update = current_time
                
                # ═══════════════════════════════════════════════════════
                # v1.4.3 OPTIMIZED: DIVINE EYE - Reduced Frequency
                # Check every N loops instead of every loop to prevent blocking
                # ═══════════════════════════════════════════════════════
                if not hasattr(self, 'divine_eye_counter'):
                    self.divine_eye_counter = 0
                
                self.divine_eye_counter += 1
                
                # Only run Divine Eye every N loops (reduces blocking)
                should_run_divine_eye = (self.divine_eye_counter % AppConstants.DIVINE_EYE_CHECK_INTERVAL == 0)
                
                if divine_eye and DIVINE_EYE_AVAILABLE and should_run_divine_eye:
                    try:
                        result = divine_eye.detect(None, device)
                        
                        # Log detection if high confidence
                        if result.confidence > AppConstants.DIVINE_EYE_MIN_CONFIDENCE:
                            smart_logger.log(f"🔮 {result.state.value} ({result.confidence*100:.0f}%)")
                        
                        # Handle lost states
                        if result.is_lost:
                            smart_logger.log(f"⚠️  {result.action_suggestion}", force=True)
                            
                            if result.state == ScreenState.LOST:
                                smart_logger.log("🔄 Recovering to TikTok...", force=True)
                                # FIX: Don't back multiple times - just reopen TikTok
                                # Multiple backs can exit the app!
                                automation.open_tiktok()
                                time.sleep(3)
                                continue
                            
                            elif result.state == ScreenState.ERROR_SCREEN:
                                smart_logger.log("❌ Error screen detected", force=True)
                                UIHelper.swipe_next_video(device, self.config)
                                time.sleep(1)
                                continue
                            
                            elif result.state == ScreenState.NO_INTERNET:
                                smart_logger.log("📡 No internet, waiting 5s...", force=True)
                                time.sleep(5)
                                continue
                        
                        # v1.4.3 ENHANCED: Handle popups comprehensively
                        if result.has_popup:
                            smart_logger.log("📋 Popup detected by Divine Eye", force=True)
                            
                            # Try comprehensive popup handler first
                            popup_dismissed = automation.handle_comprehensive_popup()
                            
                            if not popup_dismissed:
                                # Fallback: simple back
                                device.press("back")
                                time.sleep(0.5)
                            
                            continue
                        
                        # Handle wrong tab
                        if result.state == ScreenState.FOLLOWING_TAB:
                            smart_logger.log("👥 On Following tab, switching...", force=True)
                            w, h = UIHelper.get_screen_size(device)
                            device.click(int(w * 0.7), int(h * 0.05))
                            time.sleep(1)
                            continue
                    
                    except Exception as divine_error:
                        smart_logger.log(f"Divine Eye error: {divine_error}")
                
                # Check 1234 popup
                UIHelper.handle_1234_popup(device, self.config)
                
                # Check popup ngẫu nhiên
                if random.random() < self.config.check_popup_rate:
                    console.print("[dim]🔍 Quét popup...[/dim]")
                    automation.handle_popup()
                
                # Check lost
                if random.random() < self.config.check_lost_rate:
                    if automation.check_lost():
                        console.print("[red]⚠️  Khôi phục...[/red]")
                        if not automation.recover_to_feed():
                            break
                        continue
                
                xml = XMLParser.extract(device)
                
                # Skip live
                if automation.detect_live(xml):
                    console.print("[dim]📺 Live...[/dim]")
                    if not self.config.skip_live:
                        time.sleep(self.config.live_watch_seconds)
                        device.press("back")
                    else:
                        UIHelper.swipe_next_video(device, self.config)
                    continue
                
                # Skip ads
                if self.config.skip_ads and XMLParser.detect_ads(xml, self.config):
                    console.print("[dim]📺 Bỏ ads...[/dim]")
                    UIHelper.swipe_next_video(device, self.config)
                    time.sleep(1.0)
                    continue
                
                # ═══════════════════════════════════════════════════════
                # v1.4.3 FIX: Smart watch time (respect account time limit)
                # ═══════════════════════════════════════════════════════
                remaining_time = account_end - time.time()
                
                if remaining_time <= 0:
                    # Time's up! Break immediately
                    smart_logger.log("⏰ Account time finished", force=True)
                    break
                
                # Get desired watch time
                desired_watch_time = self.config.get_video_watch_time()
                
                # v1.4.3 BUILD 5: Log watch time to verify randomness
                smart_logger.log(f"⏱️  Watch: {desired_watch_time:.1f}s (range: {self.config.video_watch_time_min}-{self.config.video_watch_time_max}s)")
                
                # Adjust if we don't have enough time
                # Reserve 2 seconds for swipe and actions
                max_watch_time = max(1.0, remaining_time - 2.0)
                actual_watch_time = min(desired_watch_time, max_watch_time)
                
                # v1.4.3 BUILD 5: If actual differs from desired, log it
                if actual_watch_time < desired_watch_time:
                    smart_logger.log(f"⚠️  Adjusted to {actual_watch_time:.1f}s (remaining: {remaining_time:.1f}s)")
                
                # Only watch if we have at least 1 second
                if actual_watch_time >= 1.0:
                    time.sleep(actual_watch_time)
                else:
                    # Not enough time, swipe and exit
                    smart_logger.log("⏰ Time's up, swiping to next", force=True)
                    UIHelper.swipe_next_video(device, self.config)
                    time.sleep(0.5)
                    break
                
                # v1.4.3 FIX: Check time immediately after watching
                # If time's up, swipe FIRST then break (don't leave stuck on video)
                if time.time() >= account_end:
                    smart_logger.log("⏰ Account time reached, final swipe", force=True)
                    UIHelper.swipe_next_video(device, self.config)
                    time.sleep(0.5)
                    break
                
                # v1.4.3: SMART VIDEO INTERACTION
                if self.config.enable_smart_video_interaction:
                    try:
                        screen_width, screen_height = UIHelper.get_screen_size(device)
                        result = SmartVideoInteraction.smart_interact_with_video(
                            device, screen_width, screen_height, self.config
                        )
                        if result['not_interested']:
                            self.progress_tracker.add_action('not_interested')
                            console.print("[dim yellow]🚫 Not interested[/dim yellow]")
                        if result['reposted']:
                            self.progress_tracker.add_action('repost')
                            console.print("[dim yellow]🔄 Reposted[/dim yellow]")
                    except Exception as e:
                        error_msg = str(e).replace('[', '\\[').replace(']', '\\]')
                        console.print(f"[dim red]⚠️  Lỗi smart video: {error_msg}[/dim red]")
                
                # ═══════════════════════════════════════════════════════
                # v1.4.3 ENHANCED: Periodic comprehensive popup check
                # Check every 5 videos for any missed popups
                # ═══════════════════════════════════════════════════════
                if not hasattr(self, 'video_count'):
                    self.video_count = 0
                
                self.video_count += 1
                
                if self.video_count % 5 == 0:  # Every 5 videos
                    try:
                        popup_found = automation.handle_comprehensive_popup()
                        if popup_found:
                            smart_logger.log("✅ Periodic popup check: Dismissed popup", force=True)
                    except Exception:
                        pass
                
                # Random actions
                rand = random.random()
                cumulative = 0
                
                if rand < (cumulative := cumulative + self.config.like_rate):
                    if UIHelper.do_like(device, self.config):
                        self.progress_tracker.add_action('like')
                        account_actions['like'] += 1  # v1.4.3: Track for notification
                
                elif rand < (cumulative := cumulative + self.config.follow_rate):
                    # v1.4.3: FOLLOW WITH VERIFICATION
                    if self.config.enable_follow_verification:
                        try:
                            screen_width, screen_height = UIHelper.get_screen_size(device)
                            # Try to get username (simplified - just use "user")
                            username = "user"
                            success = FollowVerifier.perform_follow_with_verification(
                                device, username, screen_width, screen_height
                            )
                            if success:
                                self.progress_tracker.add_action('follow')
                                account_actions['follow'] += 1  # v1.4.3: Track for notification
                                console.print("[dim green]✅ Follow verified[/dim green]")
                            else:
                                console.print("[dim yellow]❌ Follow failed[/dim yellow]")
                        except Exception as e:
                            error_msg = str(e).replace('[', '\\[').replace(']', '\\]')
                            console.print(f"[dim red]⚠️  Follow verify lỗi: {error_msg}[/dim red]")
                    else:
                        # Old method without verification
                        if UIHelper.do_follow(device, self.config):
                            self.progress_tracker.add_action('follow')
                            account_actions['follow'] += 1  # v1.4.3: Track for notification
                
                elif rand < (cumulative := cumulative + self.config.comment_rate):
                    if UIHelper.do_comment(device, self.config):
                        self.progress_tracker.add_action('comment')
                        account_actions['comment'] += 1  # v1.4.3: Track for notification
                
                elif rand < (cumulative := cumulative + self.config.notification_rate):
                    if UIHelper.check_notification(device, self.config):
                        self.progress_tracker.add_action('notification')
                
                elif rand < (cumulative := cumulative + self.config.shop_rate):
                    if UIHelper.browse_shop(device, self.config):
                        self.progress_tracker.add_action('shop')
                        account_actions['shop'] += 1  # v1.4.3: Track for notification
                
                # Swipe next
                UIHelper.swipe_next_video(device, self.config)
                delay = random.uniform(self.config.swipe_delay_min, self.config.swipe_delay_max)
                time.sleep(delay)
            
            # Kết thúc account
            account_end_time = datetime.now(vn_tz)
            
            # ═══════════════════════════════════════════════════════════════
            # v1.4.3: SAVE ACCOUNT DETAILS FOR NOTIFICATION
            # ═══════════════════════════════════════════════════════════════
            account_duration = int(time.time() - account_start)
            account_details.append({
                'account_name': f'@{account}',  # Add @ prefix
                'status': account_status,
                'follow_status': account_follow_status,
                'actions': account_actions.copy(),
                'errors': account_errors.copy(),
                'duration': account_duration
            })
            
            # v1.4.3: Lưu session với checkpoint status
            session = FarmSession(
                account=account,
                start_time=account_start_time,
                end_time=account_end_time,
                duration_seconds=int(time.time() - account_start),
                actions=self.progress_tracker.get_current_actions(),
                success=True,
                proxy_used=self.config.proxy.get_proxy_url() if self.config.proxy.enabled else None,
                checkpoint_status=current_checkpoint_status
            )
            stats_manager.add_session(session)
            
            smart_logger.log(f"✅ Hoàn thành {account}", force=True)
            
            # ═══════════════════════════════════════════════════════════════
            # MILESTONE NOTIFICATION ✅ REFACTORED
            # ═══════════════════════════════════════════════════════════════
            self._send_milestone_notification(idx, len(accounts))
            
            # v1.4.3: REST MODE - Nghỉ giữa các account
            if idx < len(accounts) and self.config.enable_rest_between_accounts:
                automation.rest_between_accounts(self.config.rest_duration_minutes)
            
            # Switch to next account
            if idx < len(accounts):
                next_account = accounts[idx]
                
                console.print()
                console.print(f"[cyan]🔄 Chuẩn bị chuyển sang {next_account}...[/cyan]")
                time.sleep(1.0)
                
                console.print("[cyan]👤 Vào hồ sơ...[/cyan]")
                automation.click_profile_button()
                time.sleep(5.0)  # Chờ hồ sơ load xong
                
                console.print("[magenta]📋 Mở danh sách acc...[/magenta]")
                if not automation.open_account_switch_popup():
                    self._ultimate_ui.show_message(f"❌ Không mở popup", "error")
                    # FIX: Use safe_back_to_feed instead of manual backs
                    UIHelper.safe_back_to_feed(device, max_attempts=1, delay=1.0)
                    automation.exit_profile_mode()
                    continue
                
                time.sleep(1.5)
                
                console.print(f"[green]🔄 Chuyển sang {next_account}...[/green]")
                success, checkpoint_status = automation.switch_to_account(next_account)
                
                # ═══════════════════════════════════════════════════════════════
                # v1.4.3: TRACK FOLLOW STATUS AFTER SWITCH
                # ═══════════════════════════════════════════════════════════════
                # Lưu checkpoint status cho account tiếp theo
                current_checkpoint_status = checkpoint_status
                
                # Set follow_status based on checkpoint
                if checkpoint_status == "checkpoint":
                    account_follow_status = "checkpoint"
                    account_status = "failed"
                    account_errors.append("Checkpoint detected")
                elif checkpoint_status == "healthy":
                    account_follow_status = "success"
                elif success:
                    account_follow_status = "success"
                else:
                    account_follow_status = "failed"
                    account_status = "failed"
                    account_errors.append("Switch failed")
                
                if success:
                    self._ultimate_ui.show_message(f"✅ Đã chuyển: {next_account}", "success")
                    
                    # Hiển thị checkpoint status
                    if checkpoint_status == "checkpoint":
                        console.print(f"[red]⚠️  WARNING: {next_account} bị CHECKPOINT![/red]")
                        
                        # ═══════════════════════════════════════════════════════════════
                        # v1.4.3: SEND ERROR NOTIFICATION FOR CHECKPOINT
                        # ═══════════════════════════════════════════════════════════════
                        if (self.config.telegram_enabled and self.config.telegram_notify_error) or \
                           (self.config.discord_enabled and self.config.discord_notify_error):
                            try:
                                discord_msg, telegram_msg = self.notification_manager.format_error_alert(
                                    f"@{next_account}",
                                    "Checkpoint Detected",
                                    "Account bị checkpoint, không thể hoạt động"
                                )
                                self.notification_manager.send_notification(discord_msg, telegram_msg)
                            except Exception:
                                pass
                                
                    elif checkpoint_status == "healthy":
                        self._ultimate_ui.show_message(f"✅ {next_account} khỏe mạnh", "success")
                    
                    automation.exit_profile_mode()
                else:
                    self._ultimate_ui.show_message(f"⚠️  Switch thất bại", "warning")
                    automation.exit_profile_mode()
        
        # ═══════════════════════════════════════════════════════════════
        # FINALIZE SESSION ✅ REFACTORED
        # ═══════════════════════════════════════════════════════════════
        self._finalize_session(
            accounts,
            account_details,
            session_start_time,
            formatted_time,
            automation,
            device
        )
    

    # ──────────────────────────────────────────────────────────────
    # show_config (giống hệt v1.4.4)
    # ──────────────────────────────────────────────────────────────

    def show_config(self):
        from core.device_manager import TikTokPackage
        CS = self._ColorScheme

        package_name = TikTokPackage[self.config.selected_package].display_name

        col1_content = f"""[bold bright_cyan]📦 GÓI & THỜI GIAN[/bold bright_cyan]
━━━━━━━━━━━━━━━━━━━━━━━
[cyan]Gói TikTok:[/cyan]
  [bright_green]{package_name}[/bright_green]

[cyan]Phút/TK:[/cyan]
  [bright_green]{self.config.minutes_per_account}[/bright_green] phút

[cyan]Buffer:[/cyan]
  [bright_green]{self.config.buffer_minutes}[/bright_green] phút

[cyan]Thời gian xem:[/cyan]
  [bright_green]{self.config.video_watch_time_min}-{self.config.video_watch_time_max}[/bright_green]s

[bold bright_cyan]⚙️  PROXY & REST[/bold bright_cyan]
━━━━━━━━━━━━━━━━━━━━━━━"""

        if self.config.proxy.enabled:
            col1_content += f"\n[cyan]Proxy:[/cyan]\n  [bright_green]✅ {self.config.proxy.proxy_type}://{self.config.proxy.host}:{self.config.proxy.port}[/bright_green]"
        else:
            col1_content += "\n[cyan]Proxy:[/cyan]\n  [dim]❌ Tắt[/dim]"

        if self.config.enable_rest_between_accounts:
            col1_content += f"\n\n[cyan]Nghỉ giữa acc:[/cyan]\n  [bright_green]✅ {self.config.rest_duration_minutes}m[/bright_green]"
        else:
            col1_content += "\n\n[cyan]Nghỉ giữa acc:[/cyan]\n  [dim]❌ Tắt[/dim]"

        verify   = "✅ Bật" if self.config.enable_verify_account else "❌ Tắt"
        a1234    = "✅ Bật" if self.config.enable_auto_1234_popup else "❌ Tắt"
        ckpt     = "✅ Bật" if self.config.enable_checkpoint_check else "❌ Tắt"
        popscan  = "✅ Bật" if self.config.enable_profile_popup_scan else "❌ Tắt"

        col2_content = f"""[bold bright_cyan]📊 TỶ LỆ THAO TÁC[/bold bright_cyan]
━━━━━━━━━━━━━━━━━━━━━━━
[cyan]❤️  Like:[/cyan]
  [bold bright_green]{self.config.like_rate*100:.0f}%[/bold bright_green]

[cyan]👥 Follow:[/cyan]
  [bold bright_green]{self.config.follow_rate*100:.0f}%[/bold bright_green]

[cyan]💬 Comment:[/cyan]
  [bold bright_green]{self.config.comment_rate*100:.0f}%[/bold bright_green]

[cyan]📬 Thông báo:[/cyan]
  [bold bright_green]{self.config.notification_rate*100:.0f}%[/bold bright_green]

[cyan]🛍️  Cửa hàng:[/cyan]
  [bold bright_green]{self.config.shop_rate*100:.0f}%[/bold bright_green]

[bold bright_cyan]✓ TÍNH NĂNG CƠ BẢN[/bold bright_cyan]
━━━━━━━━━━━━━━━━━━━━━━━
[cyan]Verify Acc:[/cyan] {verify}
[cyan]Auto 1234:[/cyan] {a1234}
[cyan]Checkpoint:[/cyan] {ckpt}
[cyan]Popup Scan:[/cyan] {popscan}"""

        sv     = "✅ ON" if self.config.enable_smart_video_interaction else "❌ OFF"
        prio   = "✅ ON" if self.config.enable_priority_farming else "❌ OFF"
        fv     = "✅ ON" if self.config.enable_follow_verification else "❌ OFF"
        stats  = "✅ ON" if self.config.stats_auto_export else "❌ OFF"
        device = "✅ ON" if self.config.track_device_info else "❌ OFF"
        tg_st  = "✅ Configured" if (self.config.telegram_enabled and self.config.telegram_bot_token) else "❌ Not Setup"
        dc_st  = "✅ Configured" if (self.config.discord_enabled and self.config.discord_webhook_url) else "❌ Not Setup"

        col3_content = f"""[bold bright_yellow]✨ MỚI v1.4.6[/bold bright_yellow]
━━━━━━━━━━━━━━━━━━━━━━━
[cyan]🎯 Smart Video:[/cyan]
  {sv}
  [dim]<{self.config.not_interested_threshold}/>{self.config.repost_threshold:,}[/dim]

[cyan]🏆 Priority Farm:[/cyan]
  {prio}
  [dim]Mode: {self.config.priority_mode}[/dim]

[cyan]✅ Follow Verify:[/cyan]
  {fv}
  [dim]Retry: {self.config.max_follow_retry}[/dim]

[cyan]📊 Advanced Stats:[/cyan]
  {stats}
  [dim]Export: {self.config.stats_export_interval_hours}h[/dim]

[cyan]💻 Device Info:[/cyan]
  {device}

[bold {CS.ACCENT}]🔔 THÔNG BÁO[/bold {CS.ACCENT}]
━━━━━━━━━━━━━━━━━━━━━━━
[cyan]📱 Telegram:[/cyan]
  {tg_st}

[cyan]💬 Discord:[/cyan]
  {dc_st}"""

        console.print(Columns([
            Panel(col1_content, border_style="bright_cyan",   box=box.ROUNDED, padding=(1, 2)),
            Panel(col2_content, border_style="bright_blue", box=box.ROUNDED, padding=(1, 2)),
            Panel(col3_content, border_style="bright_cyan",  box=box.ROUNDED, padding=(1, 2)),
        ], equal=True, expand=True))


    # ──────────────────────────────────────────────────────────────
    # v1.4.6 SETTINGS MENU — cấu trúc 2 tầng
    # ──────────────────────────────────────────────────────────────

    def settings_menu(self):
        """Menu Cài đặt v1.4.6 — 2 nhóm: Chung + Nuôi acc"""
        while True:
            show_banner("⚙️  CÀI ĐẶT")

            grid = Table.grid(padding=(0, 2))
            grid.add_column(width=10)
            grid.add_column(style="bright_white")

            grid.add_row(
                _badge("1", "bright_cyan"),
                "[bold bright_white]⚙️  Cài đặt chung[/bold bright_white]\n"
                "  [dim]Gói TikTok · Proxy · AI Keys · Notifications · Device[/dim]"
            )
            grid.add_row("", "")
            grid.add_row(
                _badge("2", "blue"),
                "[bold bright_white]🌾 Cài đặt nuôi acc[/bold bright_white]\n"
                "  [dim]Thời gian · Tỷ lệ · Tính năng tự động · Popup[/dim]"
            )
            grid.add_row("", "")
            grid.add_row(
                _badge("0", "grey46"),
                "[dim]← Quay lại Menu chính[/dim]"
            )

            console.print(Panel(
                grid,
                title="[bold black on bright_blue]  ⚙️  CÀI ĐẶT  [/bold black on bright_blue]",
                border_style="bright_cyan",
                box=box.HEAVY_HEAD,
                padding=(1, 3)))
            console.print()

            c = Prompt.ask("[bold bright_cyan]❯[/bold bright_cyan] Chọn", choices=["1","2","0"], default="0")
            if c == "1":
                self.general_settings_menu()
            elif c == "2":
                self.farm_settings_menu()
            else:
                break

    def general_settings_menu(self):
        """Cài đặt chung v1.4.6"""
        from core.device_manager import TikTokPackage
        from core.config import ProxyType
        cfg = self.config

        while True:
            show_banner("⚙️  CÀI ĐẶT CHUNG")

            pkg_name = TikTokPackage[cfg.selected_package].display_name
            n_keys   = len(self.ai_key_manager.keys)
            n_proxy  = len(self.proxy_manager.proxies)

            gt = Table.grid(padding=(0, 2))
            gt.add_column(width=10)
            gt.add_column(style="bright_white", width=30)
            gt.add_column(style="dim", justify="right")

            def grow(num, col, label, val):
                gt.add_row(_badge(num, col), label, val)

            grow("1","bright_blue",    "📦 Gói TikTok",
                 f"[cyan]{pkg_name}[/cyan]")
            grow("2","bright_blue",    "🎯 Vị trí nút acc",
                 "[dim]Auto[/dim]" if not cfg.use_custom_account_button_y
                 else f"[bright_green]{cfg.custom_account_button_y_px}px[/bright_green]")
            grow("3","bright_cyan",    "🌐 Proxy",
                 _status(cfg.proxy.enabled) + (
                     f" [dim]{cfg.proxy.host}:{cfg.proxy.port}[/dim]"
                     if cfg.proxy.enabled else ""))
            grow("4","bright_cyan",    "🤖 AI API Keys",
                 f"[cyan]{n_keys}[/cyan] keys")
            grow("5","bright_cyan",    "🌐 Proxy Manager",
                 f"[cyan]{n_proxy}[/cyan] proxies")
            grow("6","cyan",           "📱 Telegram",     _status(cfg.telegram_enabled))
            grow("7","cyan",           "💬 Discord",      _status(cfg.discord_enabled))
            grow("8","cyan",           "💻 Device Info",  _status(cfg.track_device_info))
            grow("9","cyan",           "📊 Auto Export",  _status(cfg.stats_auto_export))
            gt.add_row("", "", "")
            grow("0","grey46",         "← Quay lại",      "")

            console.print(Panel(
                gt,
                title="[bold bright_white on bright_blue]  ⚙️  CÀI ĐẶT CHUNG  [/bold bright_white on bright_blue]",
                border_style="bright_cyan",
                box=box.HEAVY_HEAD,
                padding=(1, 2)))
            console.print()

            choice = Prompt.ask("[bold bright_cyan]❯[/bold bright_cyan] Chọn mục", default="0").strip()

            if choice == "1":
                show_banner("📦 CHỌN GÓI TIKTOK")
                pt = Table(box=box.ROUNDED, show_header=True,
                           header_style="bold bright_cyan", border_style="bright_cyan")
                pt.add_column("#", justify="center", style="bright_cyan bold", width=5)
                pt.add_column("Gói", style="bright_green bold", width=20)
                pt.add_column("Package", style="dim")
                for i, pkg in enumerate(TikTokPackage, 1):
                    mark = " ◀" if pkg.name == cfg.selected_package else ""
                    pt.add_row(str(i), pkg.display_name + mark, pkg.package_name)
                console.print(pt); console.print()
                v = IntPrompt.ask("[cyan]Chọn (1-5)[/cyan]", default=1)
                if 1 <= v <= len(TikTokPackage):
                    sel = list(TikTokPackage)[v-1]
                    cfg.selected_package = sel.name
                    loading_effect(f"Đã chọn {sel.display_name}", 0.5)

            elif choice == "2":
                show_banner("🎯 VỊ TRÍ NÚT ACC")
                console.print("  [bright_cyan]1.[/bright_cyan] Auto\n  [bright_cyan]2.[/bright_cyan] Custom (px)")
                m = IntPrompt.ask("Chọn", default=1)
                if m == 1:
                    cfg.use_custom_account_button_y = False
                    loading_effect("Auto mode", 0.4)
                elif m == 2:
                    cfg.use_custom_account_button_y = True
                    y = IntPrompt.ask("[cyan]Y (px)[/cyan]", default=144)
                    cfg.custom_account_button_y_px = max(50, min(500, y))
                    loading_effect(f"Y = {cfg.custom_account_button_y_px}px", 0.4)

            elif choice == "3":
                show_banner("🌐 CẤU HÌNH PROXY")
                cfg.proxy.enabled = Confirm.ask("[cyan]Bật Proxy?[/cyan]", default=cfg.proxy.enabled)
                if cfg.proxy.enabled:
                    for i, t in enumerate(["HTTP","HTTPS","SOCKS4","SOCKS5"],1):
                        console.print(f"  [bright_cyan]{i}.[/bright_cyan] {t}")
                    pc = IntPrompt.ask("[cyan]Loại (1-4)[/cyan]", default=1)
                    from core.config import ProxyType as _PT
                    pts = [_PT.HTTP, _PT.HTTPS, _PT.SOCKS4, _PT.SOCKS5]
                    if 1 <= pc <= 4: cfg.proxy.proxy_type = pts[pc-1].value
                    cfg.proxy.host = Prompt.ask("[cyan]Host[/cyan]", default=cfg.proxy.host or "127.0.0.1")
                    cfg.proxy.port = IntPrompt.ask("[cyan]Port[/cyan]", default=cfg.proxy.port or 8080)
                    if Confirm.ask("[cyan]Dùng Auth?[/cyan]", default=False):
                        cfg.proxy.username = Prompt.ask("[cyan]Username[/cyan]", default=cfg.proxy.username or "")
                        cfg.proxy.password = Prompt.ask("[cyan]Password[/cyan]", password=True, default="")
                    loading_effect(f"Proxy: {cfg.proxy.proxy_type}://{cfg.proxy.host}:{cfg.proxy.port}", 0.5)
                else:
                    loading_effect("Đã tắt proxy", 0.4)

            elif choice == "4":
                self.ai_api_keys_menu()
            elif choice == "5":
                self.proxy_management_menu()
            elif choice == "6":
                self.config_telegram()
            elif choice == "7":
                self.config_discord()

            elif choice == "8":
                show_banner("💻 DEVICE INFO")
                cfg.track_device_info = Confirm.ask("[cyan]Bật Device Tracking?[/cyan]", default=cfg.track_device_info)
                if cfg.track_device_info:
                    cfg.log_device_info_on_start = Confirm.ask("[cyan]Log khi start?[/cyan]", default=cfg.log_device_info_on_start)
                loading_effect("Đã lưu", 0.4)

            elif choice == "9":
                show_banner("📊 AUTO EXPORT STATS")
                cfg.stats_auto_export = Confirm.ask("[cyan]Bật Auto Export?[/cyan]", default=cfg.stats_auto_export)
                if cfg.stats_auto_export:
                    h = IntPrompt.ask("[cyan]Export mỗi X giờ[/cyan]", default=cfg.stats_export_interval_hours)
                    cfg.stats_export_interval_hours = max(1, min(168, h))
                loading_effect("Đã lưu", 0.4)

            elif choice == "0":
                self.config_manager.save(cfg)
                loading_effect("💾 Đã lưu cài đặt chung", 0.6)
                break

    def farm_settings_menu(self):
        """Cài đặt nuôi acc v1.4.6 — tỷ lệ + tính năng"""
        while True:
            show_banner("🌾 CÀI ĐẶT NUÔI ACC")
            cfg = self.config

            ft = Table.grid(padding=(0, 2))
            ft.add_column(width=10)
            ft.add_column(style="bright_white", width=30)
            ft.add_column(style="dim", justify="right")

            def frow(num, col, label, val):
                ft.add_row(_badge(num, col), label, val)

            # Thời gian
            frow("1","bright_blue",   "⏱️  Phút/tài khoản",    f"[cyan]{cfg.minutes_per_account}m[/cyan]")
            frow("2","bright_blue",   "🎬 Thời gian xem video", f"[cyan]{cfg.video_watch_time_min:.1f}s–{cfg.video_watch_time_max:.1f}s[/cyan]")
            frow("3","bright_blue",   "⏳ Buffer time",          f"[cyan]{cfg.buffer_minutes}m[/cyan]")
            # Tỷ lệ
            ft.add_row(_badge("─","grey23"), "[dim]── Tỷ lệ thao tác ──[/dim]", "")
            frow("4","bright_cyan",   "❤️  Like",               f"[bright_red]{cfg.like_rate*100:.0f}%[/bright_red]")
            frow("5","bright_cyan",   "👥 Follow",              f"[bright_green]{cfg.follow_rate*100:.0f}%[/bright_green]")
            frow("6","bright_cyan",   "💬 Comment",             f"[bright_blue]{cfg.comment_rate*100:.0f}%[/bright_blue]")
            frow("7","cyan",          "📬 Inbox (thông báo)",   f"[cyan]{cfg.notification_rate*100:.0f}%[/cyan]")
            frow("8","cyan",          "🛍️  Cửa hàng",          f"[cyan]{cfg.shop_rate*100:.0f}%[/cyan]")
            # Tính năng
            ft.add_row(_badge("─","grey23"), "[dim]── Tính năng tự động ──[/dim]", "")
            frow("A","bright_cyan",   "🔍 Verify Account",       _status(cfg.enable_verify_account))
            frow("B","bright_cyan",   "🔢 Auto nhập 1234",       _status(cfg.enable_auto_1234_popup))
            frow("C","bright_cyan",   "⚠️  Checkpoint check",    _status(cfg.enable_checkpoint_check))
            frow("D","bright_cyan",   "🔍 Profile popup scan",   _status(cfg.enable_profile_popup_scan))
            frow("E","cyan",          "🎯 Smart Video",          _status(cfg.enable_smart_video_interaction))
            frow("F","cyan",          "🏆 Priority Farming",     _status(cfg.enable_priority_farming))
            frow("G","cyan",          "✅ Follow Verify",         _status(cfg.enable_follow_verification))
            frow("H","cyan",          "😴 Rest giữa acc",        _status(cfg.enable_rest_between_accounts))
            ft.add_row("", "", "")
            frow("0","grey46",        "← Quay lại",              "")

            console.print(Panel(
                ft,
                title="[bold bright_white on bright_blue]  🌾  CÀI ĐẶT NUÔI ACC  [/bold bright_white on bright_blue]",
                border_style="bright_blue",
                box=box.HEAVY_HEAD,
                padding=(1, 2)))
            console.print()

            choice = Prompt.ask("[bold bright_blue]❯[/bold bright_blue] Chọn mục",
                                default="0").strip().upper()

            if choice == "1":
                v = IntPrompt.ask("[cyan]Phút mỗi TK[/cyan]", default=cfg.minutes_per_account)
                cfg.minutes_per_account = max(1, v)
                loading_effect(f"Đặt {cfg.minutes_per_account}m/TK", 0.4)
            elif choice == "2":
                mn = FloatPrompt.ask("[cyan]Min (s)[/cyan]", default=cfg.video_watch_time_min)
                mx = FloatPrompt.ask("[cyan]Max (s)[/cyan]", default=cfg.video_watch_time_max)
                cfg.video_watch_time_min = max(1.0, min(30.0, mn))
                cfg.video_watch_time_max = max(cfg.video_watch_time_min+1, min(60.0, mx))
                loading_effect(f"Video: {cfg.video_watch_time_min:.1f}s–{cfg.video_watch_time_max:.1f}s", 0.4)
            elif choice == "3":
                v = IntPrompt.ask("[cyan]Buffer (phút)[/cyan]", default=cfg.buffer_minutes)
                cfg.buffer_minutes = max(0, min(60, v))
                loading_effect(f"Buffer: {cfg.buffer_minutes}m", 0.4)
            elif choice == "4":
                v = FloatPrompt.ask("[cyan]Like rate (0.0–1.0)[/cyan]", default=cfg.like_rate)
                cfg.like_rate = max(0.0, min(1.0, v))
                loading_effect(f"Like: {cfg.like_rate*100:.0f}%", 0.4)
            elif choice == "5":
                v = FloatPrompt.ask("[cyan]Follow rate (0.0–1.0)[/cyan]", default=cfg.follow_rate)
                cfg.follow_rate = max(0.0, min(1.0, v))
                loading_effect(f"Follow: {cfg.follow_rate*100:.0f}%", 0.4)
            elif choice == "6":
                v = FloatPrompt.ask("[cyan]Comment rate (0.0–1.0)[/cyan]", default=cfg.comment_rate)
                cfg.comment_rate = max(0.0, min(1.0, v))
                loading_effect(f"Comment: {cfg.comment_rate*100:.0f}%", 0.4)
            elif choice == "7":
                show_banner("📬 INBOX THÔNG BÁO")
                r = FloatPrompt.ask("[cyan]Tỷ lệ (0.0–1.0)[/cyan]", default=cfg.notification_rate)
                s = IntPrompt.ask("[cyan]Scroll (lần)[/cyan]", default=cfg.notification_scroll_times)
                w = FloatPrompt.ask("[cyan]Xem (s)[/cyan]", default=cfg.notification_watch_time)
                cfg.notification_rate          = max(0.0, min(1.0, r))
                cfg.notification_scroll_times  = max(1, min(10, s))
                cfg.notification_watch_time    = max(0.5, min(10.0, w))
                loading_effect("Đã lưu inbox config", 0.4)
            elif choice == "8":
                show_banner("🛍️  CỬA HÀNG")
                r = FloatPrompt.ask("[cyan]Tỷ lệ (0.0–1.0)[/cyan]", default=cfg.shop_rate)
                s = IntPrompt.ask("[cyan]Scroll (lần)[/cyan]", default=cfg.shop_scroll_times)
                w = FloatPrompt.ask("[cyan]Xem (s)[/cyan]", default=cfg.shop_item_watch_time)
                cfg.shop_rate            = max(0.0, min(1.0, r))
                cfg.shop_scroll_times    = max(1, min(15, s))
                cfg.shop_item_watch_time = max(0.5, min(10.0, w))
                loading_effect("Đã lưu cửa hàng config", 0.4)
            elif choice == "A":
                show_banner("🔍 VERIFY ACCOUNT")
                console.print(Panel("[dim]Sau khi chuyển acc, vào profile kiểm tra @id\nNếu sai → thử lại chuyển account[/dim]",
                                    border_style="bright_cyan", box=box.ROUNDED))
                cfg.enable_verify_account = Confirm.ask("[cyan]Bật Verify?[/cyan]", default=cfg.enable_verify_account)
                loading_effect(("Bật" if cfg.enable_verify_account else "Tắt") + " Verify", 0.4)
            elif choice == "B":
                show_banner("🔢 AUTO 1234 POPUP")
                console.print(Panel("[dim]Tự động nhập '1234' khi gặp popup xác nhận[/dim]",
                                    border_style="bright_blue", box=box.ROUNDED))
                cfg.enable_auto_1234_popup = Confirm.ask("[cyan]Bật Auto 1234?[/cyan]", default=cfg.enable_auto_1234_popup)
                loading_effect(("Bật" if cfg.enable_auto_1234_popup else "Tắt") + " Auto 1234", 0.4)
            elif choice == "C":
                show_banner("⚠️  CHECKPOINT CHECK")
                console.print(Panel("[dim]Phát hiện acc bị checkpoint/warning/banned\nLưu trạng thái: ✅ Khỏe / ⚠️ Checkpoint[/dim]",
                                    border_style="bright_cyan", box=box.ROUNDED))
                cfg.enable_checkpoint_check = Confirm.ask("[cyan]Bật Checkpoint?[/cyan]", default=cfg.enable_checkpoint_check)
                loading_effect(("Bật" if cfg.enable_checkpoint_check else "Tắt") + " Checkpoint", 0.4)
            elif choice == "D":
                show_banner("🔍 PROFILE POPUP SCAN")
                console.print(Panel("[dim]Quét popup khi vào profile — tránh nhầm sang video\nKiểm tra kỹ trước khi đóng popup[/dim]",
                                    border_style="bright_blue", box=box.ROUNDED))
                cfg.enable_profile_popup_scan = Confirm.ask("[cyan]Bật Popup Scan?[/cyan]", default=cfg.enable_profile_popup_scan)
                if cfg.enable_profile_popup_scan:
                    s = IntPrompt.ask("[cyan]Số lần quét tối đa[/cyan]", default=cfg.profile_popup_max_scans)
                    cfg.profile_popup_max_scans = max(1, min(5, s))
                loading_effect("Đã lưu Popup Scan", 0.4)
            elif choice == "E":
                show_banner("🎯 SMART VIDEO INTERACTION")
                console.print(Panel(
                    f"[dim]Video < [bright_red]{cfg.not_interested_threshold}[/bright_red] likes → 'Không quan tâm'\n"
                    f"Video > [bright_green]{cfg.repost_threshold:,}[/bright_green] likes → 'Đăng lại'[/dim]",
                    border_style="bright_cyan", box=box.ROUNDED))
                cfg.enable_smart_video_interaction = Confirm.ask("[cyan]Bật Smart Video?[/cyan]", default=cfg.enable_smart_video_interaction)
                if cfg.enable_smart_video_interaction:
                    lo = IntPrompt.ask("[cyan]Ngưỡng 'Không quan tâm' (<)[/cyan]", default=cfg.not_interested_threshold)
                    hi = IntPrompt.ask("[cyan]Ngưỡng 'Đăng lại' (>)[/cyan]", default=cfg.repost_threshold)
                    cfg.not_interested_threshold = max(0, lo)
                    cfg.repost_threshold         = max(1000, hi)
                loading_effect("Đã lưu Smart Video", 0.4)
            elif choice == "F":
                show_banner("🏆 PRIORITY FARMING")
                console.print(Panel("[dim]Ưu tiên acc có ít sessions/actions nhất để nuôi trước[/dim]",
                                    border_style="bright_blue", box=box.ROUNDED))
                cfg.enable_priority_farming = Confirm.ask("[cyan]Bật Priority?[/cyan]", default=cfg.enable_priority_farming)
                if cfg.enable_priority_farming:
                    console.print("\n  [bright_cyan]1.[/bright_cyan] Sessions  [bright_cyan]2.[/bright_cyan] Actions")
                    m = Prompt.ask("Mode", choices=["1","2"], default="1")
                    cfg.priority_mode = "sessions" if m == "1" else "actions"
                loading_effect("Đã lưu Priority Farming", 0.4)
            elif choice == "G":
                show_banner("✅ FOLLOW VERIFICATION")
                console.print(Panel("[dim]1.Click Follow → 2.Swipe reload → 3.Kiểm tra 'Following'[/dim]",
                                    border_style="bright_cyan", box=box.ROUNDED))
                cfg.enable_follow_verification = Confirm.ask("[cyan]Bật Follow Verify?[/cyan]", default=cfg.enable_follow_verification)
                if cfg.enable_follow_verification:
                    r = IntPrompt.ask("[cyan]Retry tối đa[/cyan]", default=cfg.max_follow_retry)
                    cfg.max_follow_retry = max(0, min(5, r))
                loading_effect("Đã lưu Follow Verify", 0.4)
            elif choice == "H":
                show_banner("😴 REST GIỮA ACC")
                console.print(Panel("[dim]Tắt TikTok và chờ X phút — giúp tránh spam[/dim]",
                                    border_style="bright_blue", box=box.ROUNDED))
                cfg.enable_rest_between_accounts = Confirm.ask("[cyan]Bật Rest Mode?[/cyan]", default=cfg.enable_rest_between_accounts)
                if cfg.enable_rest_between_accounts:
                    m = IntPrompt.ask("[cyan]Phút nghỉ[/cyan]", default=cfg.rest_duration_minutes)
                    cfg.rest_duration_minutes = max(1, min(30, m))
                loading_effect("Đã lưu Rest Mode", 0.4)
            elif choice == "0":
                self.config_manager.save(cfg)
                loading_effect("💾 Đã lưu cài đặt nuôi acc", 0.6)
                break


    # ──────────────────────────────────────────────────────────────
    # Telegram & Discord config (giống hệt v1.4.4)
    # ──────────────────────────────────────────────────────────────

    def config_telegram(self):
        CS = self._ColorScheme
        self._ultimate_ui.clear_screen_animated()
        console.print(Panel(f"[bold {CS.PRIMARY}]📱 TELEGRAM NOTIFICATIONS[/bold {CS.PRIMARY}]",
                            border_style=CS.PRIMARY, box=box.DOUBLE_EDGE))
        console.print()
        console.print(Panel(
            f"[{CS.INFO}]Nhận thông báo realtime qua Telegram Bot\n\n"
            f"Cần có:\n• Bot Token (từ @BotFather)\n• Chat ID (từ @userinfobot)[/{CS.INFO}]",
            border_style=CS.INFO, box=box.ROUNDED))
        console.print()

        self.config.telegram_enabled = Confirm.ask(f"[{CS.PRIMARY}]Bật Telegram notifications?[/{CS.PRIMARY}]", default=self.config.telegram_enabled)

        if self.config.telegram_enabled:
            console.print()
            token = Prompt.ask(f"[{CS.PRIMARY}]Bot Token[/{CS.PRIMARY}]", default=self.config.telegram_bot_token or "")
            if token:
                self.config.telegram_bot_token = token
            chat_id = Prompt.ask(f"[{CS.PRIMARY}]Chat ID[/{CS.PRIMARY}]", default=self.config.telegram_chat_id or "")
            if chat_id:
                self.config.telegram_chat_id = chat_id
            console.print()
            console.print(f"[bold {CS.INFO}]Loại thông báo:[/bold {CS.INFO}]")
            console.print()
            self.config.telegram_notify_start     = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo khi bắt đầu?[/{CS.TEXT_PRIMARY}]", default=self.config.telegram_notify_start)
            self.config.telegram_notify_complete  = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo khi hoàn thành?[/{CS.TEXT_PRIMARY}]", default=self.config.telegram_notify_complete)
            self.config.telegram_notify_error     = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo khi có lỗi?[/{CS.TEXT_PRIMARY}]", default=self.config.telegram_notify_error)
            self.config.telegram_notify_milestone = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo milestone (mỗi 10 acc)?[/{CS.TEXT_PRIMARY}]", default=self.config.telegram_notify_milestone)
            console.print()
            if self.config.telegram_bot_token and self.config.telegram_chat_id:
                if Confirm.ask(f"[{CS.WARNING}]Test kết nối Telegram?[/{CS.WARNING}]", default=True):
                    console.print()
                    console.print(f"[{CS.INFO}]Đang gửi test message...[/{CS.INFO}]")
                    self.notification_manager.configure_telegram(self.config.telegram_bot_token, self.config.telegram_chat_id)
                    results = self.notification_manager.test_connection()
                    if results.get("telegram", False):
                        console.print(f"[{CS.SUCCESS}]✅ Test thành công! Check Telegram.[/{CS.SUCCESS}]")
                    else:
                        console.print(f"[{CS.ERROR}]❌ Test thất bại. Kiểm tra lại token/chat_id.[/{CS.ERROR}]")
            console.print()
            console.print(f"[{CS.SUCCESS}]✅ Telegram đã được cấu hình![/{CS.SUCCESS}]")
        else:
            console.print(f"[{CS.WARNING}]⚠️  Đã tắt Telegram notifications[/{CS.WARNING}]")
        console.print()
        self.config_manager.save(self.config)
        loading_effect("💾 Đã lưu cài đặt Telegram", 0.5)
        Prompt.ask("[dim]Nhấn Enter để tiếp tục...[/dim]")

    def config_discord(self):
        CS = self._ColorScheme
        self._ultimate_ui.clear_screen_animated()
        console.print(Panel(f"[bold {CS.ACCENT}]💬 DISCORD NOTIFICATIONS[/bold {CS.ACCENT}]",
                            border_style=CS.ACCENT, box=box.DOUBLE_EDGE))
        console.print()
        console.print(Panel(
            f"[{CS.INFO}]Nhận thông báo realtime qua Discord Webhook\n\n"
            f"Cách tạo webhook:\n• Vào Server Settings → Integrations → Webhooks\n• Create Webhook → Copy URL[/{CS.INFO}]",
            border_style=CS.INFO, box=box.ROUNDED))
        console.print()

        self.config.discord_enabled = Confirm.ask(f"[{CS.ACCENT}]Bật Discord notifications?[/{CS.ACCENT}]", default=self.config.discord_enabled)

        if self.config.discord_enabled:
            console.print()
            webhook = Prompt.ask(f"[{CS.ACCENT}]Webhook URL[/{CS.ACCENT}]", default=self.config.discord_webhook_url or "")
            if webhook:
                self.config.discord_webhook_url = webhook
            console.print()
            console.print(f"[bold {CS.INFO}]Loại thông báo:[/bold {CS.INFO}]")
            console.print()
            self.config.discord_notify_start     = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo khi bắt đầu?[/{CS.TEXT_PRIMARY}]", default=self.config.discord_notify_start)
            self.config.discord_notify_complete  = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo khi hoàn thành?[/{CS.TEXT_PRIMARY}]", default=self.config.discord_notify_complete)
            self.config.discord_notify_error     = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo khi có lỗi?[/{CS.TEXT_PRIMARY}]", default=self.config.discord_notify_error)
            self.config.discord_notify_milestone = Confirm.ask(f"[{CS.TEXT_PRIMARY}]→ Thông báo milestone (mỗi 10 acc)?[/{CS.TEXT_PRIMARY}]", default=self.config.discord_notify_milestone)
            console.print()
            if self.config.discord_webhook_url:
                if Confirm.ask(f"[{CS.WARNING}]Test kết nối Discord?[/{CS.WARNING}]", default=True):
                    console.print()
                    console.print(f"[{CS.INFO}]Đang gửi test message...[/{CS.INFO}]")
                    self.notification_manager.configure_discord(self.config.discord_webhook_url)
                    results = self.notification_manager.test_connection()
                    if results.get("discord", False):
                        console.print(f"[{CS.SUCCESS}]✅ Test thành công! Check Discord.[/{CS.SUCCESS}]")
                    else:
                        console.print(f"[{CS.ERROR}]❌ Test thất bại. Kiểm tra lại webhook URL.[/{CS.ERROR}]")
            console.print()
            console.print(f"[{CS.SUCCESS}]✅ Discord đã được cấu hình![/{CS.SUCCESS}]")
        else:
            console.print(f"[{CS.WARNING}]⚠️  Đã tắt Discord notifications[/{CS.WARNING}]")
        console.print()
        self.config_manager.save(self.config)
        loading_effect("💾 Đã lưu cài đặt Discord", 0.5)
        Prompt.ask("[dim]Nhấn Enter để tiếp tục...[/dim]")

    # ──────────────────────────────────────────────────────────────
    # AI API Keys menu (giống hệt v1.4.4)
    # ──────────────────────────────────────────────────────────────

    def ai_api_keys_menu(self):
        """v1.4.4: AI API Keys Management Menu"""
        while True:
            self._ultimate_ui.clear_screen_animated()
            console.print(Panel("[bold bright_blue]🤖 AI API KEYS MANAGEMENT[/bold bright_blue]",
                                border_style="bright_blue", box=box.DOUBLE_EDGE))
            console.print()

            keys = self.ai_key_manager.get_all_keys()

            if keys:
                kt = Table(box=box.ROUNDED, show_header=True, header_style="bold bright_cyan")
                kt.add_column("#",      justify="center", style="bright_cyan", width=4)
                kt.add_column("Tên",    style="bright_green", width=18)
                kt.add_column("Model",  style="cyan", width=22)
                kt.add_column("Mã API",style="dim", width=25)
                kt.add_column("Số dùng",justify="right", style="bright_blue", width=6)
                kt.add_column("Trạng thái",justify="center", style="bold", width=10)
                for idx, key in enumerate(keys, 1):
                    if getattr(key, 'is_quota_exhausted', False):
                        status = "✖ HẾT QUOTA"; sty = "bold bright_red"
                    elif getattr(key, 'exhausted_models', []):
                        n_ex = len(key.exhausted_models)
                        status = f"⚡ {n_ex} mdl hết"; sty = "bright_yellow"
                        if key.is_active: status = "▶ " + status
                    elif key.is_active:
                        status = "▶ ĐANG DÙNG"; sty = "bold bright_green"
                    else:
                        status = "○ Chờ"; sty = "dim"
                    kt.add_row(str(idx), key.name, key.model,
                               key.get_masked_key(), str(key.usage_count),
                               f"[{sty}]{status}[/{sty}]")
                console.print(kt)
            else:
                console.print(Panel("[cyan]⚠️  Chưa có API key nào.\nThêm key để sử dụng AI popup detection.[/cyan]",
                                    border_style="bright_blue", box=box.ROUNDED))
            console.print()

            mg = Table.grid(padding=(0, 2))
            mg.add_column(style="bold bright_cyan", width=3)
            mg.add_column(style="bright_white")
            mg.add_row("1", "➕ Thêm API key mới")
            mg.add_row("2", "✅ Chọn key đang dùng")
            mg.add_row("3", "🗑️  Xoá API key")
            mg.add_row("4", "🧪 Kiểm tra API key")
            mg.add_row("5", "🔄 Chuyển sang key tiếp")
            mg.add_row("6", "📦 Đổi model AI")
            mg.add_row("7", "🔃 Reset trạng thái quota")
            mg.add_row("0", "⬅️  Quay lại")
            console.print(Panel(mg, border_style="bright_cyan", box=box.SIMPLE))
            console.print()

            choice = Prompt.ask("[bold bright_cyan]❯[/bold bright_cyan] Chọn", default="0")

            if choice == "1":
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_green]➕ THÊM API KEY GEMINI MỚI[/bold bright_green]", border_style="bright_cyan"))
                console.print()
                console.print("[dim]Lấy Gemini API key miễn phí tại:[/dim]")
                console.print("[bright_blue]https://aistudio.google.com/app/apikey[/bright_blue]")
                console.print()
                name    = Prompt.ask("[cyan]Tên key (để nhận biết)[/cyan]")
                api_key = Prompt.ask("[cyan]Nhập API Key[/cyan]")
                if name and api_key:
                    console.print()
                    console.print("[bright_cyan]🔍 Đang kiểm tra key và tải danh sách model khả dụng...[/bright_cyan]")
                    try:
                        from ai.popup_handler import _GeminiClient, AIPopupHandler
                        available_models = _GeminiClient.get_available_models(api_key)

                        if not available_models:
                            console.print("[bright_red]❌ Key không hợp lệ hoặc không có model nào khả dụng[/bright_red]")
                            console.print("[dim]Key chưa được thêm.[/dim]")
                            time.sleep(3)
                            continue

                        console.print(f"[bright_green]✅ API key hợp lệ! Tìm thấy {len(available_models)} model[/bright_green]")
                        console.print()

                        # Hiển thị bảng models khả dụng
                        mt = Table(box=box.ROUNDED, show_header=True,
                            header_style="bold bright_cyan", border_style="bright_cyan",
                            title="[bold bright_cyan]📋 Models khả dụng từ API[/bold bright_cyan]")
                        mt.add_column("STT", justify="center", style="bright_cyan", width=5)
                        mt.add_column("Model ID", style="bright_green", width=38)
                        mt.add_column("Tên", style="bright_white", width=22)
                        mt.add_column("Vision", justify="center", style="cyan", width=8)
                        mt.add_column("Ghi chú", style="dim", width=18)

                        for idx, m in enumerate(available_models, 1):
                            star = "⭐" if m.get("recommended") else ""
                            vision = "✅" if m.get("vision") else "❌"
                            desc = m.get("desc","")[:17]
                            mt.add_row(
                                str(idx),
                                m["id"],
                                m["name"][:21],
                                vision,
                                f"{star} {desc}".strip()
                            )
                        console.print(mt)
                        console.print()

                        # Gợi ý model tốt nhất (đầu tiên)
                        best = available_models[0]
                        console.print(f"[cyan]💡 Gợi ý: [bright_white]{best['id']}[/bright_white] (model dau tien uu tien)[/cyan]")
                        console.print()

                        max_idx = len(available_models)
                        mc = Prompt.ask(
                            f"[cyan]Chọn số model (1-{max_idx}) hoặc nhập tên tùy chọn[/cyan]",
                            default="1"
                        )
                        try:
                            mc_int = int(mc)
                            if 1 <= mc_int <= max_idx:
                                selected_model = available_models[mc_int - 1]["id"]
                            else:
                                selected_model = best["id"]
                        except ValueError:
                            # Nhập tên model tùy chỉnh
                            selected_model = mc.strip() if mc.strip() else best["id"]

                        console.print(f"[bright_green]✅ Đã chọn: [bold]{selected_model}[/bold][/bright_green]")
                        self.ai_key_manager.add_key(name, api_key, model=selected_model)

                        if self.ai_handler is None and self.config.ai_popup_enabled:
                            try:
                                from ai import AIPopupHandler, TwoLayerPopupHandler
                                self.ai_handler    = AIPopupHandler(self.ai_key_manager)
                                self.popup_handler = TwoLayerPopupHandler(self.ai_handler, self.config)
                                console.print("[bright_green]✅ AI popup handler đã khởi tạo![/bright_green]")
                            except Exception as e:
                                console.print(f"[cyan]⚠️  Cảnh báo: {e}[/cyan]")
                        self._ultimate_ui.show_message(f"✅ Đã thêm: {name} | Model: {selected_model}", "success")
                    except Exception as e:
                        err = str(e).replace("[","[").replace("]","]")
                        console.print(f"[bright_red]❌ Lỗi: {err}[/bright_red]")
                        console.print("[cyan]Key chưa được thêm.[/cyan]")
                else:
                    self._ultimate_ui.show_message("⚠️  Cần nhập tên và key", "warning")
                time.sleep(2)

            elif choice == "2":
                if not keys:
                    self._ultimate_ui.show_message("⚠️  Chưa có key nào", "warning"); time.sleep(1); continue
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_cyan]✅ SELECT ACTIVE KEY[/bold bright_cyan]", border_style="bright_cyan")); console.print()
                for idx, key in enumerate(keys, 1):
                    console.print(f"{'🟢' if key.is_active else '⚪'} {idx}. {key.name}")
                console.print()
                kn = IntPrompt.ask("[cyan]Chọn số key[/cyan]", default=1)
                if 1 <= kn <= len(keys):
                    self.ai_key_manager.select_key(keys[kn-1].id)
                    if self.config.ai_popup_enabled:
                        try:
                            from ai import AIPopupHandler, TwoLayerPopupHandler
                            self.ai_handler    = AIPopupHandler(self.ai_key_manager)
                            self.popup_handler  = TwoLayerPopupHandler(self.ai_handler, self.config)
                        except Exception as e:
                            console.print(f"[cyan]⚠️  Warning: {e}[/cyan]")
                    self._ultimate_ui.show_message(f"✅ Active: {keys[kn-1].name}", "success")
                else:
                    self._ultimate_ui.show_message("❌ Lựa chọn không hợp lệ", "error")
                time.sleep(1)

            elif choice == "3":
                if not keys:
                    self._ultimate_ui.show_message("⚠️  Không có key để xoá", "warning"); time.sleep(1); continue
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_red]🗑️  REMOVE API KEY[/bold bright_red]", border_style="bright_cyan")); console.print()
                for idx, key in enumerate(keys, 1):
                    console.print(f"{idx}. {key.name} ({key.get_masked_key()})")
                console.print()
                kn = IntPrompt.ask("[cyan]Chọn số key cần xoá[/cyan]", default=0)
                if 1 <= kn <= len(keys):
                    selected = keys[kn - 1]
                    if Confirm.ask(f"[bright_red]Xoá '{selected.name}'?[/bright_red]", default=False):
                        self.ai_key_manager.remove_key(selected.id)
                        self._ultimate_ui.show_message(f"✅ Đã xoá: {selected.name}", "success")
                    else:
                        self._ultimate_ui.show_message("❌ Đã huỷ", "info")
                else:
                    self._ultimate_ui.show_message("❌ Lựa chọn không hợp lệ", "error")
                time.sleep(1)

            elif choice == "4":
                if not keys:
                    self._ultimate_ui.show_message("⚠️  Không có key để kiểm tra", "warning"); time.sleep(1); continue
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_blue]🧪 TEST API KEY[/bold bright_blue]", border_style="bright_blue")); console.print()
                for idx, key in enumerate(keys, 1):
                    console.print(f"{'🟢' if key.is_active else '⚪'} {idx}. {key.name}")
                console.print()
                kn = IntPrompt.ask("[cyan]Chọn số key cần test[/cyan]", default=1)
                if 1 <= kn <= len(keys):
                    selected = keys[kn - 1]
                    console.print(f"\n[bright_cyan]🔍 Đang kiểm tra {selected.name}...[/bright_cyan]")
                    try:
                        from ai.popup_handler import _GeminiClient
                        available = _GeminiClient.get_available_models(selected.api_key)
                        if available:
                            console.print(f"[bright_green]✅ Key hợp lệ! Tìm thấy {len(available)} model[/bright_green]")
                            for i, m in enumerate(available[:5], 1):
                                star = " ⭐" if m.get("recommended") else ""
                                console.print(f"  [bright_cyan]{i}.[/bright_cyan] [bright_green]{m['id']}[/bright_green]{star}")
                            if len(available) > 5:
                                console.print(f"  [dim]... và {len(available)-5} model khác[/dim]")
                            selected.mark_used(success=True)
                        else:
                            console.print("[bright_red]❌ Key không hợp lệ hoặc không có model khả dụng[/bright_red]")
                            selected.mark_used(success=False)
                    except Exception as e:
                        console.print(f"[bright_red]❌ Kiểm tra thất bại: {e}[/bright_red]")
                time.sleep(3)

            elif choice == "5":
                if len(keys) < 2:
                    self._ultimate_ui.show_message("⚠️  Cần ít nhất 2 key", "warning"); time.sleep(1); continue
                next_key = self.ai_key_manager.rotate_key()
                if next_key:
                    self._ultimate_ui.show_message(f"🔄 Đã chuyển sang: {next_key.name}", "success")
                else:
                    self._ultimate_ui.show_message("❌ Chuyển key thất bại", "error")
                time.sleep(1)

            elif choice == "6":
                if not keys:
                    self._ultimate_ui.show_message("⚠️  Chưa có key nào", "warning"); time.sleep(1); continue
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_blue]📦 ĐỔI MODEL AI[/bold bright_blue]", border_style="bright_blue"))
                console.print()
                for idx, key in enumerate(keys, 1):
                    console.print(f"  [bright_cyan]{idx}.[/bright_cyan] {key.name} [dim](hiện tại: {key.model})[/dim]")
                console.print()
                kn = IntPrompt.ask("[cyan]Chọn key[/cyan]", default=1)
                if 1 <= kn <= len(keys):
                    selected_key = keys[kn - 1]
                    console.print(f"\n[bright_cyan]🔍 Đang tải danh sách model cho key '{selected_key.name}'...[/bright_cyan]")
                    try:
                        from ai.popup_handler import _GeminiClient
                        available = _GeminiClient.get_available_models(selected_key.api_key)
                        if available:
                            mt2 = Table(box=box.ROUNDED, show_header=True,
                                header_style="bold bright_cyan", border_style="bright_blue")
                            mt2.add_column("STT", justify="center", style="bright_cyan", width=5)
                            mt2.add_column("Model ID", style="bright_green", width=38)
                            mt2.add_column("Vision", justify="center", style="cyan", width=8)
                            mt2.add_column("Ghi chú", style="dim", width=15)
                            for i, m in enumerate(available, 1):
                                star = "⭐" if m.get("recommended") else ""
                                mt2.add_row(str(i), m["id"], "✅" if m.get("vision") else "❌", star)
                            console.print(mt2)
                            console.print()
                            mc = Prompt.ask(
                                f"[cyan]Chọn số model (1-{len(available)}) hoặc nhập tên tùy chỉnh[/cyan]",
                                default="1"
                            )
                            try:
                                mc_int = int(mc)
                                new_model = available[mc_int-1]["id"] if 1 <= mc_int <= len(available) else selected_key.model
                            except ValueError:
                                new_model = mc.strip() if mc.strip() else selected_key.model
                        else:
                            # Fallback to manual input
                            console.print("[yellow]⚠️  Không lấy được danh sách model từ API[/yellow]")
                            new_model = Prompt.ask("[cyan]Nhập tên model[/cyan]", default=selected_key.model)
                    except Exception:
                        new_model = Prompt.ask("[cyan]Nhập tên model[/cyan]", default=selected_key.model)
                    selected_key.model = new_model
                    self.ai_key_manager.save_to_file()
                    self._ultimate_ui.show_message(f"✅ Đã đổi model: {new_model}", "success")
                time.sleep(1)

            elif choice == "7":
                # Reset quota status
                console.print()
                console.print("[bold bright_yellow]🔃 Đặt lại trạng thái quota tất cả keys...[/bold bright_yellow]")
                self.ai_key_manager.reset_all_quota_status()
                self._ultimate_ui.show_message(
                    "✅ Đã reset quota — tất cả models khả dụng trở lại", "success")
                time.sleep(1.5)

            elif choice == "0":
                break

    # ──────────────────────────────────────────────────────────────
    # Proxy Management menu (giống hệt v1.4.4)
    # ──────────────────────────────────────────────────────────────

    def proxy_management_menu(self):
        """v1.4.4: Multi-Proxy Management Menu"""
        from core.config import ProxyType

        while True:
            self._ultimate_ui.clear_screen_animated()
            console.print(Panel("[bold bright_blue]🌐 PROXY MANAGEMENT v1.4.6[/bold bright_blue]",
                                border_style="bright_blue", box=box.DOUBLE_EDGE))
            console.print()

            proxies = self.proxy_manager.get_all_proxies()

            if proxies:
                pt = Table(box=box.ROUNDED, show_header=True, header_style="bold bright_cyan")
                pt.add_column("#",        justify="center", style="bright_cyan", width=4)
                pt.add_column("Tên",      style="bright_green", width=15)
                pt.add_column("Loại",    style="cyan", width=8)
                pt.add_column("Host:Port",style="bright_blue", width=25)
                pt.add_column("Số dùng",  justify="right", style="dim", width=6)
                pt.add_column("Trạng thái",justify="center", style="bold", width=12)
                for idx, proxy in enumerate(proxies, 1):
                    status = "🟢 ĐANG DÙNG" if proxy.is_active else "⚪ Chưa dùng"
                    sty    = "bold bright_green" if proxy.is_active else "dim"
                    pt.add_row(str(idx), proxy.name, proxy.proxy_type,
                               f"{proxy.host}:{proxy.port}",
                               str(getattr(proxy, "usage_count", 0)),
                               f"[{sty}]{status}[/{sty}]")
                console.print(pt)
            else:
                console.print(Panel("[cyan]⚠️  Chưa có proxy nào.\nThêm proxy để sử dụng multi-proxy rotation.[/cyan]",
                                    border_style="bright_blue", box=box.ROUNDED))
            console.print()

            pg = Table.grid(padding=(0, 2))
            pg.add_column(style="bold bright_cyan", width=3)
            pg.add_column(style="bright_white")
            pg.add_row("1", "➕ Thêm proxy mới")
            pg.add_row("2", "✅ Chọn proxy đang dùng")
            pg.add_row("3", "🗑️  Xoá proxy")
            pg.add_row("4", "🧪 Kiểm tra proxy")
            pg.add_row("5", "🔄 Chuyển sang proxy tiếp")
            pg.add_row("6", "⚙️  Cài đặt tự động chuyển")
            pg.add_row("0", "⬅️  Quay lại")
            console.print(Panel(pg, border_style="bright_cyan", box=box.SIMPLE))
            console.print()

            choice = Prompt.ask("[bold bright_cyan]❯[/bold bright_cyan] Chọn", default="0")

            if choice == "1":
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_green]➕ ADD NEW PROXY[/bold bright_green]", border_style="bright_cyan")); console.print()
                name = Prompt.ask("[cyan]Tên proxy[/cyan]")
                console.print("[bright_cyan]Proxy Type:[/bright_cyan]")
                console.print("  1. HTTP  2. HTTPS  3. SOCKS4  4. SOCKS5\n")
                tc = IntPrompt.ask("[cyan]Chọn (1-4)[/cyan]", default=1)
                proxy_types = [ProxyType.HTTP, ProxyType.HTTPS, ProxyType.SOCKS4, ProxyType.SOCKS5]
                ptype = proxy_types[tc - 1].value if 1 <= tc <= 4 else "http"
                host  = Prompt.ask("[cyan]Host (IP/Domain)[/cyan]")
                port  = IntPrompt.ask("[cyan]Port[/cyan]", default=8080)
                use_auth = Confirm.ask("[cyan]Dùng Username/Password?[/cyan]", default=False)
                username = password = ""
                if use_auth:
                    username = Prompt.ask("[cyan]Username[/cyan]", default="")
                    password = Prompt.ask("[cyan]Password[/cyan]", password=True, default="")
                if name and host:
                    self.proxy_manager.add_proxy(name, ptype, host, port, username, password)
                    self._ultimate_ui.show_message(f"✅ Added: {name} ({ptype}://{host}:{port})", "success")
                else:
                    self._ultimate_ui.show_message("⚠️  Cần nhập tên và host", "warning")
                time.sleep(2)

            elif choice == "2":
                if not proxies:
                    self._ultimate_ui.show_message("⚠️  Chưa có proxy nào", "warning"); time.sleep(1); continue
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_cyan]✅ SELECT ACTIVE PROXY[/bold bright_cyan]", border_style="bright_cyan")); console.print()
                for idx, p in enumerate(proxies, 1):
                    console.print(f"{'🟢' if p.is_active else '⚪'} {idx}. {p.name}")
                console.print()
                pn = IntPrompt.ask("[cyan]Chọn số proxy[/cyan]", default=1)
                if 1 <= pn <= len(proxies):
                    self.proxy_manager.select_proxy(proxies[pn-1].id)
                    self._ultimate_ui.show_message(f"✅ Active: {proxies[pn-1].name}", "success")
                else:
                    self._ultimate_ui.show_message("❌ Lựa chọn không hợp lệ", "error")
                time.sleep(1)

            elif choice == "3":
                if not proxies:
                    self._ultimate_ui.show_message("⚠️  Không có proxy để xoá", "warning"); time.sleep(1); continue
                console.print()
                for idx, p in enumerate(proxies, 1):
                    console.print(f"{idx}. {p.name} ({p.host}:{p.port})")
                console.print()
                pn = IntPrompt.ask("[cyan]Chọn số proxy cần xoá[/cyan]", default=0)
                if 1 <= pn <= len(proxies):
                    selected = proxies[pn - 1]
                    if Confirm.ask(f"[bright_red]Xoá '{selected.name}'?[/bright_red]", default=False):
                        self.proxy_manager.remove_proxy(selected.id)
                        self._ultimate_ui.show_message(f"✅ Đã xoá: {selected.name}", "success")
                    else:
                        self._ultimate_ui.show_message("❌ Đã huỷ", "info")
                else:
                    self._ultimate_ui.show_message("❌ Lựa chọn không hợp lệ", "error")
                time.sleep(1)

            elif choice == "4":
                if not proxies:
                    self._ultimate_ui.show_message("⚠️  Không có proxy để kiểm tra", "warning"); time.sleep(1); continue
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_blue]🧪 TEST PROXY[/bold bright_blue]", border_style="bright_blue")); console.print()
                for idx, p in enumerate(proxies, 1):
                    console.print(f"{idx}. {p.name}")
                console.print()
                pn = IntPrompt.ask("[cyan]Chọn số proxy cần test[/cyan]", default=1)
                if 1 <= pn <= len(proxies):
                    selected = proxies[pn - 1]
                    console.print()
                    console.print(f"[bright_cyan]Testing {selected.name}...[/bright_cyan]")
                    try:
                        import requests as _req
                        proxy_url  = selected.get_proxy_url()
                        proxies_d  = {"http": proxy_url, "https": proxy_url}
                        response   = _req.get("https://api.ipify.org?format=json", proxies=proxies_d, timeout=10)
                        if response.status_code == 200:
                            ip = response.json().get("ip", "Không xác định")
                            console.print(f"[bright_green]✅ Proxy hoạt động! IP thực: {ip}[/bright_green]")
                            selected.mark_used(success=True)
                            self.proxy_manager.save_to_file()
                        else:
                            console.print(f"[bright_red]❌ Status {response.status_code}[/bright_red]")
                            selected.mark_used(success=False)
                            self.proxy_manager.save_to_file()
                    except Exception as e:
                        console.print(f"[bright_red]❌ Kiểm tra thất bại: {e}[/bright_red]")
                        selected.mark_used(success=False)
                        self.proxy_manager.save_to_file()
                time.sleep(2)

            elif choice == "5":
                if len(proxies) < 2:
                    self._ultimate_ui.show_message("⚠️  Cần ít nhất 2 proxy", "warning"); time.sleep(1); continue
                next_p = self.proxy_manager.switch_to_next()
                if next_p:
                    self._ultimate_ui.show_message(f"🔄 Đã chuyển sang: {next_p.name}", "success")
                else:
                    self._ultimate_ui.show_message("❌ Chuyển proxy thất bại", "error")
                time.sleep(1)

            elif choice == "6":
                self._ultimate_ui.clear_screen_animated()
                console.print(Panel("[bold bright_blue]⚙️  AUTO-SWITCH SETTINGS[/bold bright_blue]", border_style="bright_blue")); console.print()
                console.print("[dim]Auto-switch proxy sau mỗi account - tránh bị detect bởi TikTok[/dim]\n")
                self.proxy_manager.auto_switch_enabled = Confirm.ask("[cyan]Enable auto-switch?[/cyan]", default=self.proxy_manager.auto_switch_enabled)
                if self.proxy_manager.auto_switch_enabled:
                    console.print()
                    self.config.close_app_before_proxy_switch  = Confirm.ask("[cyan]Close TikTok before switch?[/cyan]",  default=self.config.close_app_before_proxy_switch)
                    self.config.reopen_app_after_proxy_switch  = Confirm.ask("[cyan]Reopen TikTok after switch?[/cyan]", default=self.config.reopen_app_after_proxy_switch)
                    delay = IntPrompt.ask("[cyan]Delay between switch and reopen (seconds)[/cyan]", default=self.config.proxy_switch_delay_seconds)
                    self.config.proxy_switch_delay_seconds = max(1, min(10, delay))
                    console.print()
                    self._ultimate_ui.show_message("✅ Đã cấu hình tự động chuyển!", "success")
                else:
                    self._ultimate_ui.show_message("⚠️  Đã tắt tự động chuyển", "warning")
                self.proxy_manager.save_to_file()
                self.config_manager.save(self.config)
                time.sleep(2)

            elif choice == "0":
                break

    # ──────────────────────────────────────────────────────────────
    # MAIN RUN v1.4.6 — New structure + Neon UI
    # ──────────────────────────────────────────────────────────────

    def run(self):
        """Main loop v1.4.6 — Neon UI"""
        from app.stats_ui import StatsUI
        from core.device_manager import DeviceManager, DeviceHardwareInfo

        # Startup
        show_banner()
        loading_effect("Khởi động AT Tool v1.4.6...", 1.5)

        while True:
            show_banner()

            # Status bar
            devices  = DeviceManager.list_devices()
            ai_key   = self.ai_key_manager.get_active_key()
            n_proxy  = len(self.proxy_manager.proxies)

            sb = Table.grid(padding=(0, 2))
            sb.add_column(style="dim bright_cyan",  width=16)
            sb.add_column(style="bright_white",     width=22)
            sb.add_column(style="dim bright_cyan",  width=16)
            sb.add_column(style="bright_white")

            dev_val = (f"[bold bright_green]✅ {devices[0][:16]}[/bold bright_green]"
                       if devices else "[dim]❌ Không có thiết bị[/dim]")
            ai_val  = (f"[bold bright_green]✅ {ai_key.name[:14]}[/bold bright_green]"
                       if ai_key else "[dim]❌ Chưa có key[/dim]")

            sb.add_row("📱 Thiết bị:", dev_val, "🤖 AI Key:", ai_val)
            sb.add_row(
                "⏱️  Phút/TK:",
                f"[bold bright_yellow]{self.config.minutes_per_account}m[/bold bright_yellow]",
                "🌐 Proxy:",
                f"[cyan]{n_proxy}[/cyan] proxy  "
                + _status(self.config.proxy.enabled)
            )

            console.print(Panel(
                sb,
                title="[bold bright_cyan]📡 TRẠNG THÁI HỆ THỐNG[/bold bright_cyan]",
                border_style="bright_cyan",
                box=box.HEAVY_HEAD,
                padding=(0, 2)))
            console.print()

            # Main menu
            mm = Table.grid(padding=(0, 2))
            mm.add_column(width=10)
            mm.add_column(style="bright_white")
            mm.add_column(style="dim", justify="right", width=22)

            mm.add_row(
                _badge("1", "blue"),
                "[bold bright_white]🌾 Nuôi Tài Khoản[/bold bright_white]\n"
                "  [dim bright_green]Bắt đầu farm ngay — không hỏi thêm gì[/dim bright_green]",
                (f"[dim bright_green]{len(devices)} device sẵn sàng[/dim bright_green]"
                 if devices else "[dim bright_red]⚠️  Chưa kết nối device[/dim bright_red]")
            )
            mm.add_row("", "", "")
            mm.add_row(
                _badge("2", "blue"),
                "[bold bright_white]⚙️  Cài Đặt[/bold bright_white]\n"
                "  [dim bright_cyan]Chung · Nuôi acc · AI · Proxy · Thông báo[/dim bright_cyan]",
                ""
            )
            mm.add_row("", "", "")
            mm.add_row(
                _badge("3", "cyan"),
                "[bold bright_white]📊 Thống Kê[/bold bright_white]\n"
                "  [dim bright_yellow]Hôm nay · Tuần · Tháng · Báo cáo[/dim bright_yellow]",
                ""
            )
            mm.add_row("", "", "")
            mm.add_row(
                _badge("0", "grey46"),
                "[dim bright_white]🚪 Thoát[/dim bright_white]",
                ""
            )

            console.print(Panel(
                mm,
                title="[bold black on bright_blue]  ❯  MENU CHÍNH  ❮  [/bold black on bright_blue]",
                border_style="bright_blue",
                box=box.HEAVY,
                padding=(1, 3)))
            console.print()

            choice = Prompt.ask(
                "[bold bright_blue]❯❯[/bold bright_blue] Chọn",
                choices=["1","2","3","0"], default="1"
            )

            if choice == "1":
                if not devices:
                    console.print(Panel(
                        "[bold bright_red]❌ Không tìm thấy thiết bị!\n\n[/bold bright_red]"
                        "[dim]• Kiểm tra USB Debugging\n• Kiểm tra ADB driver\n• Thử cắm lại cáp USB[/dim]",
                        border_style="bright_cyan", box=box.HEAVY))
                    time.sleep(2)
                    continue

                loading_effect(f"Kết nối {devices[0]}...", 0.8)
                device = DeviceManager.connect_u2(devices[0])
                if not device:
                    console.print("[bright_red]❌ Kết nối thất bại[/bright_red]")
                    time.sleep(2)
                    continue

                try:
                    self.run_farm(device)
                except KeyboardInterrupt:
                    console.print()
                    console.print(Panel(
                        "[bold bright_yellow]⚠️  Đã dừng bởi người dùng (Ctrl+C)[/bold bright_yellow]",
                        border_style="bright_blue", box=box.ROUNDED))
                except Exception as e:
                    emsg = str(e).replace("[","\\[").replace("]","\\]")
                    console.print(Panel(
                        f"[bold bright_red]❌ Lỗi: {emsg}[/bold bright_red]",
                        border_style="bright_cyan", box=box.HEAVY))
                    traceback.print_exc()
                Prompt.ask("\n[dim]Enter để tiếp tục...[/dim]")

            elif choice == "2":
                self.settings_menu()

            elif choice == "3":
                StatsUI.show_stats_menu()

            elif choice == "0":
                show_banner("👋 TẠM BIỆT!")
                console.print(Panel(
                    Align.center(
                        "[bold bright_cyan]Cảm ơn anh đã dùng AT Tool v1.4.6![/bold bright_cyan]\n\n"
                        "[bold bright_blue]Blue Edition[/bold bright_blue]\n\n"
                        "[dim bright_white]Hẹn gặp lại! ❤️[/dim bright_white]"
                    ),
                    border_style="bright_blue",
                    box=box.HEAVY,
                    padding=(2, 6)))
                console.print()
                break
