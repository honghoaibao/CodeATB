"""
╔══════════════════════════════════════════════════════╗
║           app/stats_ui.py - v1.4.6                   ║
║   StatsUI + DashboardComponents - Hiển thị thống kê ║
╚══════════════════════════════════════════════════════╝
"""

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.align import Align
    from rich.columns import Columns
    from rich import box
    from rich.prompt import Prompt
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

import time
from core.stats import stats_manager, StatsManager, AdvancedStatistics
from datetime import datetime
from ui.logger import smart_logger
from ui.ultimate_ui import UltimateUI as _UltimateUI
_ultimate_ui_instance = _UltimateUI()
ultimate_ui = _ultimate_ui_instance

class StatsUI:
    """UI hiển thị thống kê v1.4.3 - Fixed trùng lặp"""
    
    @staticmethod
    def show_today_stats():
        """Hiển thị thống kê hôm nay - v1.4.3"""
        ultimate_ui.clear_screen_animated()
        
        # Header với gradient
        header_text = """
╔═══════════════════════════════════════════════════════════════╗
║              📊 THỐNG KÊ HÔM NAY - v1.4.3 📊                   ║
╚═══════════════════════════════════════════════════════════════╝"""
        
        console.print(header_text, style="bold bright_cyan")
        console.print()
        
        today_stats = stats_manager.get_today_stats()
        
        if not today_stats or not today_stats.accounts:
            console.print(Panel(
                "[yellow]Chưa có dữ liệu hôm nay[/yellow]",
                border_style="yellow",
                box=box.ROUNDED
            ))
            return
        
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        today_date = datetime.now(vn_tz).strftime("%d/%m/%Y")
        
        # Tổng quan
        total_accounts = today_stats.get_total_accounts()
        total_duration = today_stats.get_total_duration_seconds()
        duration_str = stats_manager.format_duration(total_duration)
        total_sessions = today_stats.get_total_sessions()
        total_actions = today_stats.get_total_actions()
        
        overview = f"""[bright_yellow]📅 Ngày:[/bright_yellow] [bright_green]{today_date}[/bright_green]
[bright_yellow]👥 Tài khoản UNIQUE:[/bright_yellow] [bold bright_green]{total_accounts}[/bold bright_green]
[bright_yellow]🔄 Tổng phiên farm:[/bright_yellow] [bright_green]{total_sessions}[/bright_green]
[bright_yellow]⏱️  Tổng thời gian:[/bright_yellow] [bold bright_cyan]{duration_str}[/bold bright_cyan]"""
        
        console.print(Panel(
            overview, 
            title="[bold bright_cyan]═══ TỔNG QUAN ═══[/bold bright_cyan]",
            border_style="bright_cyan", 
            box=box.DOUBLE_EDGE
        ))
        console.print()
        
        # Bảng actions tổng
        actions_table = Table(
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold bright_yellow",
            border_style="bright_magenta",
            title="[bold bright_magenta]═══ TỔNG THAO TÁC ═══[/bold bright_magenta]"
        )
        
        actions_table.add_column("Thao tác", style="bright_cyan bold", width=20)
        actions_table.add_column("Số lần", justify="center", style="bright_green bold", width=15)
        
        actions_table.add_row("❤️  Like", str(total_actions.get('like', 0)))
        actions_table.add_row("👥 Follow", str(total_actions.get('follow', 0)))
        actions_table.add_row("💬 Comment", str(total_actions.get('comment', 0)))
        actions_table.add_row("📬 Thông báo", str(total_actions.get('notification', 0)))
        actions_table.add_row("🛍️  Cửa hàng", str(total_actions.get('shop', 0)))
        if total_actions.get('not_interested', 0) > 0:
            actions_table.add_row("[yellow]🚫 Không quan tâm[/yellow]", f"[yellow]{total_actions['not_interested']}[/yellow]")
        if total_actions.get('repost', 0) > 0:
            actions_table.add_row("[yellow]🔄 Đăng lại[/yellow]", f"[yellow]{total_actions['repost']}[/yellow]")
        
        console.print(actions_table)
        console.print()
        
        # Bảng chi tiết từng account - KHÔNG TRÙNG LẶP
        console.print("[bold bright_cyan]═══ CHI TIẾT TỪNG TÀI KHOẢN ═══[/bold bright_cyan]")
        console.print()
        
        accounts_table = Table(
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold bright_yellow",
            border_style="bright_cyan",
            title="[bold bright_cyan]Danh sách accounts đã farm[/bold bright_cyan]"
        )
        
        accounts_table.add_column("STT", justify="center", style="bright_cyan bold", width=6)
        accounts_table.add_column("Account", style="bright_green bold", width=20)
        accounts_table.add_column("Phiên", justify="center", style="bright_yellow", width=8)
        accounts_table.add_column("Thời gian", justify="center", style="bright_magenta", width=12)
        accounts_table.add_column("Actions", style="dim bright_white", width=40)
        accounts_table.add_column("Follow Được", justify="center", style="bright_green", width=12)
        accounts_table.add_column("Status", justify="center", style="bold", width=12)
        
        # Sort accounts by name
        sorted_accounts = sorted(today_stats.accounts.items(), key=lambda x: x[0])
        
        for idx, (acc_name, acc_stats) in enumerate(sorted_accounts, 1):
            duration = stats_manager.format_duration(acc_stats.total_duration_seconds)
            
            actions_parts = [
                f"❤️{acc_stats.total_actions.get('like', 0)}",
                f"👥{acc_stats.total_actions.get('follow', 0)}",
                f"💬{acc_stats.total_actions.get('comment', 0)}"
            ]
            if acc_stats.total_actions.get('not_interested', 0) > 0:
                actions_parts.append(f"🚫{acc_stats.total_actions['not_interested']}")
            if acc_stats.total_actions.get('repost', 0) > 0:
                actions_parts.append(f"🔄{acc_stats.total_actions['repost']}")
            actions_str = " ".join(actions_parts)
            
            # Status với màu
            if acc_stats.checkpoint_status == "healthy":
                status = "[green]✅ Khỏe[/green]"
            elif acc_stats.checkpoint_status == "checkpoint":
                status = "[red]⚠️  Checkpoint[/red]"
            else:
                status = "[dim]❓ Unknown[/dim]"
            
            # Follow success count
            follow_count = acc_stats.total_actions.get('follow', 0)
            follow_display = f"[bright_green]{follow_count}[/bright_green]" if follow_count > 0 else "[dim]0[/dim]"
            
            accounts_table.add_row(
                str(idx),
                acc_name,
                str(acc_stats.sessions_count),
                duration,
                actions_str,
                follow_display,
                status
            )
        
        console.print(accounts_table)
    
    @staticmethod
    def show_week_stats():
        """Hiển thị thống kê tuần này - v1.4.3"""
        ultimate_ui.clear_screen_animated()
        
        header_text = """
╔═══════════════════════════════════════════════════════════════╗
║          📊 THỐNG KÊ TUẦN NÀY (7 NGÀY) - v1.4.3 📊            ║
╚═══════════════════════════════════════════════════════════════╝"""
        
        console.print(header_text, style="bold bright_cyan")
        console.print()
        
        week_stats = stats_manager.get_week_stats()
        
        if not week_stats:
            console.print(Panel(
                "[yellow]Chưa có dữ liệu tuần này[/yellow]",
                border_style="yellow",
                box=box.ROUNDED
            ))
            return
        
        # Tổng hợp unique accounts trong tuần
        all_accounts = set()
        total_seconds = 0
        total_sessions = 0
        total_actions = {'like': 0, 'follow': 0, 'comment': 0, 'notification': 0, 'shop': 0}
        
        for day_stats in week_stats.values():
            all_accounts.update(day_stats.accounts.keys())
            total_seconds += day_stats.get_total_duration_seconds()
            total_sessions += day_stats.get_total_sessions()
            
            day_actions = day_stats.get_total_actions()
            for action_type, count in day_actions.items():
                total_actions[action_type] += count
        
        total_accounts = len(all_accounts)
        total_duration_str = stats_manager.format_duration(total_seconds)
        
        # Tổng quan tuần
        overview = f"""[bright_yellow]📅 Khoảng:[/bright_yellow] [bright_green]7 ngày gần nhất[/bright_green]
[bright_yellow]📊 Số ngày có data:[/bright_yellow] [bright_green]{len(week_stats)}[/bright_green]
[bright_yellow]👥 Tổng accounts UNIQUE:[/bright_yellow] [bold bright_green]{total_accounts}[/bold bright_green]
[bright_yellow]🔄 Tổng phiên farm:[/bright_yellow] [bright_green]{total_sessions}[/bright_green]
[bright_yellow]⏱️  Tổng thời gian:[/bright_yellow] [bold bright_cyan]{total_duration_str}[/bold bright_cyan]
[bright_yellow]📊 Tổng actions:[/bright_yellow] [bright_green]❤️{total_actions.get('like',0)} 👥{total_actions.get('follow',0)} 💬{total_actions.get('comment',0)} 📬{total_actions.get('notification',0)} 🛍️{total_actions.get('shop',0)}[/bright_green]"""
        
        # Add v1.4.3 actions to overview
        if total_actions.get('not_interested', 0) > 0:
            overview += f"\n[bright_yellow]        🚫 Không quan tâm: {total_actions['not_interested']:,}[/bright_yellow]"
        if total_actions.get('repost', 0) > 0:
            overview += f"\n[bright_yellow]        🔄 Đăng lại: {total_actions['repost']:,}[/bright_yellow]"
        
        overview = overview  # Keep as is
        
        console.print(Panel(
            overview,
            title="[bold bright_cyan]═══ TỔNG QUAN TUẦN ═══[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.DOUBLE_EDGE
        ))
        console.print()
        
        # Bảng chi tiết theo ngày
        days_table = Table(
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold bright_yellow",
            border_style="bright_magenta",
            title="[bold bright_magenta]Chi tiết theo ngày[/bold bright_magenta]"
        )
        
        days_table.add_column("Ngày", style="bright_cyan bold", width=12)
        days_table.add_column("Accounts", justify="center", style="bright_green bold", width=10)
        days_table.add_column("Phiên", justify="center", style="bright_yellow", width=8)
        days_table.add_column("Thời gian", justify="center", style="bright_magenta", width=12)
        days_table.add_column("Actions", style="dim bright_white", width=40)
        
        sorted_dates = sorted(week_stats.keys(), reverse=True)
        
        for date_str in sorted_dates:
            day = week_stats[date_str]
            
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_display = date_obj.strftime("%d/%m/%Y")
            
            accounts_count = day.get_total_accounts()
            sessions_count = day.get_total_sessions()
            duration = stats_manager.format_duration(day.get_total_duration_seconds())
            
            day_actions = day.get_total_actions()
            actions_parts = [
                f"❤️{day_actions.get('like', 0)}",
                f"👥{day_actions.get('follow', 0)}",
                f"💬{day_actions.get('comment', 0)}",
                f"📬{day_actions.get('notification', 0)}",
                f"🛍️{day_actions.get('shop', 0)}"
            ]
            if day_actions.get('not_interested', 0) > 0:
                actions_parts.append(f"🚫{day_actions['not_interested']}")
            if day_actions.get('repost', 0) > 0:
                actions_parts.append(f"🔄{day_actions['repost']}")
            actions_str = " ".join(actions_parts)
            
            days_table.add_row(
                date_display,
                str(accounts_count),
                str(sessions_count),
                duration,
                actions_str
            )
        
        console.print(days_table)
    
    @staticmethod
    def show_month_stats():
        """Hiển thị thống kê tháng này - v1.4.3"""
        ultimate_ui.clear_screen_animated()
        
        header_text = """
╔═══════════════════════════════════════════════════════════════╗
║              📊 THỐNG KÊ THÁNG NÀY - v1.4.3 📊                ║
╚═══════════════════════════════════════════════════════════════╝"""
        
        console.print(header_text, style="bold bright_cyan")
        console.print()
        
        month_stats = stats_manager.get_month_stats()
        
        if not month_stats:
            console.print(Panel(
                "[yellow]Chưa có dữ liệu tháng này[/yellow]",
                border_style="yellow",
                box=box.ROUNDED
            ))
            return
        
        # Tổng hợp unique accounts trong tháng
        all_accounts = set()
        total_seconds = 0
        total_sessions = 0
        total_actions = {'like': 0, 'follow': 0, 'comment': 0, 'notification': 0, 'shop': 0}
        
        for day_stats in month_stats.values():
            all_accounts.update(day_stats.accounts.keys())
            total_seconds += day_stats.get_total_duration_seconds()
            total_sessions += day_stats.get_total_sessions()
            
            day_actions = day_stats.get_total_actions()
            for action_type, count in day_actions.items():
                total_actions[action_type] += count
        
        total_accounts = len(all_accounts)
        total_duration_str = stats_manager.format_duration(total_seconds)
        
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        month_name = datetime.now(vn_tz).strftime("%m/%Y")
        
        # Tổng quan tháng
        overview = f"""[bright_yellow]📅 Tháng:[/bright_yellow] [bright_green]{month_name}[/bright_green]
[bright_yellow]📊 Số ngày có data:[/bright_yellow] [bright_green]{len(month_stats)}[/bright_green]
[bright_yellow]👥 Tổng accounts UNIQUE:[/bright_yellow] [bold bright_green]{total_accounts}[/bold bright_green]
[bright_yellow]🔄 Tổng phiên farm:[/bright_yellow] [bright_green]{total_sessions}[/bright_green]
[bright_yellow]⏱️  Tổng thời gian:[/bright_yellow] [bold bright_cyan]{total_duration_str}[/bold bright_cyan]
[bright_yellow]📊 Tổng actions:[/bright_yellow] [bright_green]❤️{total_actions.get('like',0)} 👥{total_actions.get('follow',0)} 💬{total_actions.get('comment',0)} 📬{total_actions.get('notification',0)} 🛍️{total_actions.get('shop',0)}[/bright_green]"""
        
        # Add v1.4.3 actions to overview
        if total_actions.get('not_interested', 0) > 0:
            overview += f"\n[bright_yellow]        🚫 Không quan tâm: {total_actions['not_interested']:,}[/bright_yellow]"
        if total_actions.get('repost', 0) > 0:
            overview += f"\n[bright_yellow]        🔄 Đăng lại: {total_actions['repost']:,}[/bright_yellow]"
        
        overview = overview  # Keep as is
        
        console.print(Panel(
            overview,
            title="[bold bright_cyan]═══ TỔNG QUAN THÁNG ═══[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.DOUBLE_EDGE
        ))
        console.print()
        
        # Bảng chi tiết theo ngày
        days_table = Table(
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold bright_yellow",
            border_style="bright_magenta",
            title="[bold bright_magenta]Chi tiết theo ngày[/bold bright_magenta]"
        )
        
        days_table.add_column("Ngày", style="bright_cyan bold", width=10)
        days_table.add_column("Accounts", justify="center", style="bright_green bold", width=10)
        days_table.add_column("Phiên", justify="center", style="bright_yellow", width=8)
        days_table.add_column("Thời gian", justify="center", style="bright_magenta", width=12)
        days_table.add_column("Actions", style="dim bright_white", width=40)
        
        sorted_dates = sorted(month_stats.keys(), reverse=True)
        
        for date_str in sorted_dates:
            day = month_stats[date_str]
            
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_display = date_obj.strftime("%d/%m")
            
            accounts_count = day.get_total_accounts()
            sessions_count = day.get_total_sessions()
            duration = stats_manager.format_duration(day.get_total_duration_seconds())
            
            day_actions = day.get_total_actions()
            actions_parts = [
                f"❤️{day_actions.get('like', 0)}",
                f"👥{day_actions.get('follow', 0)}",
                f"💬{day_actions.get('comment', 0)}",
                f"📬{day_actions.get('notification', 0)}",
                f"🛍️{day_actions.get('shop', 0)}"
            ]
            if day_actions.get('not_interested', 0) > 0:
                actions_parts.append(f"🚫{day_actions['not_interested']}")
            if day_actions.get('repost', 0) > 0:
                actions_parts.append(f"🔄{day_actions['repost']}")
            actions_str = " ".join(actions_parts)
            
            days_table.add_row(
                date_display,
                str(accounts_count),
                str(sessions_count),
                duration,
                actions_str
            )
        
        console.print(days_table)
    
    @staticmethod
    def show_stats_menu():
        """Menu thống kê - v1.4.3 ULTIMATE UI"""
        while True:
            ultimate_ui.clear_screen_animated()
            
            # Header
            console.print(Panel(
                "[bold bright_cyan]📊 MENU THỐNG KÊ v1.4.3[/bold bright_cyan]",
                border_style="bright_cyan",
                box=box.DOUBLE,
                padding=(0, 2)
            ))
            console.print()
            
            # Create beautiful stats menu with 2-column panels
            from rich.columns import Columns
            
            # Left panel: Daily/Weekly/Monthly
            left_content = """[bold bright_cyan]📅 BÁO CÁO THỜI GIAN[/bold bright_cyan]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold bright_yellow]1[/bold bright_yellow]  📅 [bright_white]Thống kê hôm nay[/bright_white]
   [dim]Chi tiết từng account[/dim]

[bold bright_yellow]2[/bold bright_yellow]  📆 [bright_white]Thống kê tuần này[/bright_white]
   [dim]7 ngày gần nhất[/dim]

[bold bright_yellow]3[/bold bright_yellow]  📊 [bright_white]Thống kê tháng này[/bright_white]
   [dim]Breakdown theo tuần[/dim]"""
            
            left_panel = Panel(
                left_content,
                border_style="bright_cyan",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            
            # Right panel: Advanced Reports
            right_content = f"""[bold bright_yellow]📈 BÁO CÁO NÂNG CAO[/bold bright_yellow]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold bright_yellow]4[/bold bright_yellow]  📈 [bright_white]Weekly Report[/bright_white]
   [dim bright_yellow]NEW v1.4.3[/dim bright_yellow]

[bold bright_yellow]5[/bold bright_yellow]  📊 [bright_white]Monthly Report[/bright_white]
   [dim bright_yellow]NEW v1.4.3[/dim bright_yellow]

[bold bright_yellow]6[/bold bright_yellow]  💾 [bright_white]Export Logs[/bright_white]
   [dim bright_yellow]NEW v1.4.3[/dim bright_yellow]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[bold bright_green]0[/bold bright_green]  ⬅️  [bright_white]Quay lại[/bright_white]"""
            
            right_panel = Panel(
                right_content,
                border_style="bright_yellow",
                box=box.ROUNDED,
                padding=(1, 2)
            )
            
            # Display columns
            columns = Columns([left_panel, right_panel], equal=True, expand=True)
            console.print(columns)
            console.print()
            
            choice = Prompt.ask(
                "[bold bright_cyan]❯[/bold bright_cyan] Chọn báo cáo",
                choices=["1", "2", "3", "4", "5", "6", "0"],
                default="1"
            )
            
            if choice == "1":
                StatsUI.show_today_stats()
                Prompt.ask("\n[dim bright_cyan]Enter để tiếp tục...[/dim bright_cyan]")
            elif choice == "2":
                StatsUI.show_week_stats()
                Prompt.ask("\n[dim bright_cyan]Enter để tiếp tục...[/dim bright_cyan]")
            elif choice == "3":
                StatsUI.show_month_stats()
                Prompt.ask("\n[dim bright_cyan]Enter để tiếp tục...[/dim bright_cyan]")
            elif choice == "4":
                # v1.4.3: WEEKLY REPORT
                ultimate_ui.clear_screen_animated()
                
                console.print(Panel(
                    "[bold bright_cyan]📈 GENERATING WEEKLY REPORT...[/bold bright_cyan]",
                    border_style="bright_cyan"
                ))
                
                try:
                    weekly = AdvancedStatistics.get_weekly_report(stats_manager)
                    if weekly:
                        ultimate_ui.clear_screen_animated()
                        panel = AdvancedStatistics.format_weekly_report(weekly)
                        console.print(panel)
                    else:
                        console.print(Panel("[red]Không có dữ liệu[/red]", border_style="red"))
                except Exception as e:
                    error_msg = str(e).replace('[', '\\[').replace(']', '\\]')
                    console.print(Panel(f"[red]Lỗi: {error_msg}[/red]", border_style="red"))
                
                Prompt.ask("[dim]Enter để tiếp tục...[/dim]")
            
            elif choice == "5":
                # v1.4.3: MONTHLY REPORT
                ultimate_ui.clear_screen_animated()
                
                console.print(Panel(
                    "[bold bright_magenta]📊 GENERATING MONTHLY REPORT...[/bold bright_magenta]",
                    border_style="bright_magenta"
                ))
                
                try:
                    monthly = AdvancedStatistics.get_monthly_report(stats_manager)
                    if monthly:
                        ultimate_ui.clear_screen_animated()
                        panel = AdvancedStatistics.format_monthly_report(monthly)
                        console.print(panel)
                    else:
                        console.print(Panel("[red]Không có dữ liệu[/red]", border_style="red"))
                except Exception as e:
                    error_msg = str(e).replace('[', '\\[').replace(']', '\\]')
                    console.print(Panel(f"[red]Lỗi: {error_msg}[/red]", border_style="red"))
                
                Prompt.ask("[dim]Enter để tiếp tục...[/dim]")
            
            elif choice == "6":
                # v1.4.3: EXPORT DATA - Enhanced
                ultimate_ui.clear_screen_animated()
                
                console.print(Panel(
                    "[bold bright_blue]💾 EXPORT DATA v1.4.3[/bold bright_blue]",
                    border_style="bright_blue"
                ))
                console.print()
                
                # Export menu
                export_options = """[bright_cyan]Chọn loại export:[/bright_cyan]

[bold bright_yellow]1[/bold bright_yellow]  💾 Export Statistics to CSV
   [dim]Toàn bộ stats → CSV file[/dim]

[bold bright_yellow]2[/bold bright_yellow]  📝 Export Logs
   [dim]Session logs → text file[/dim]

[bold bright_yellow]3[/bold bright_yellow]  📊 Visual Report
   [dim]ASCII charts & trends[/dim]

[bold bright_yellow]0[/bold bright_yellow]  ⬅️  Back"""
                
                console.print(Panel(export_options, border_style="bright_cyan"))
                console.print()
                
                export_choice = Prompt.ask(
                    "[bold bright_cyan]❯[/bold bright_cyan] Select export type",
                    choices=["1", "2", "3", "0"],
                    default="1"
                )
                
                if export_choice == "1":
                    # CSV Export
                    try:
                        filename = f"at_tool_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                        success = stats_manager.export_to_csv(filename)
                        if success:
                            ultimate_ui.show_message(f"✅ Stats exported to {filename}!", "success")
                        else:
                            ultimate_ui.show_message(f"❌ Export failed", "error")
                    except Exception as e:
                        error_msg = str(e).replace('[', '\\[').replace(']', '\\]')
                        console.print(Panel(f"[red]Error: {error_msg}[/red]", border_style="red"))
                
                elif export_choice == "2":
                    # Logs Export
                    try:
                        success = smart_logger.export_logs()
                        if success:
                            ultimate_ui.show_message(f"✅ Logs exported successfully!", "success")
                        else:
                            ultimate_ui.show_message(f"❌ Export failed", "error")
                    except Exception as e:
                        error_msg = str(e).replace('[', '\\[').replace(']', '\\]')
                        console.print(Panel(f"[red]Error: {error_msg}[/red]", border_style="red"))
                
                elif export_choice == "3":
                    # Visual Report
                    try:
                        ultimate_ui.clear_screen_animated()
                        report = stats_manager.generate_visual_report(days=7)
                        console.print(report)
                    except Exception as e:
                        error_msg = str(e).replace('[', '\\[').replace(']', '\\]')
                        console.print(Panel(f"[red]Error: {error_msg}[/red]", border_style="red"))
                
                
                time.sleep(2)
            
            elif choice == "0":
                break

# ══════════════════════════════════════════════════════════════════
# END OF PART 7/8
# ══════════════════════════════════════════════════════════════════
        """Hiển thị thống kê hôm nay - v1.4.3"""
        ultimate_ui.clear_screen_animated()
        
        # Header với gradient
        header_text = """
╔═══════════════════════════════════════════════════════════════╗
║              📊 THỐNG KÊ HÔM NAY - v1.4.3 📊                   ║
╚═══════════════════════════════════════════════════════════════╝"""
        
        console.print(header_text, style="bold bright_cyan")
        console.print()
        
        today_stats = stats_manager.get_today_stats()
        
        if not today_stats or not today_stats.accounts:
            console.print(Panel(
                "[yellow]Chưa có dữ liệu hôm nay[/yellow]",
                border_style="yellow",
                box=box.ROUNDED
            ))
            return
        
        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        today_date = datetime.now(vn_tz).strftime("%d/%m/%Y")
        
        # Tổng quan
        total_accounts = today_stats.get_total_accounts()
        total_duration = today_stats.get_total_duration_seconds()
        duration_str = stats_manager.format_duration(total_duration)
        total_sessions = today_stats.get_total_sessions()
        total_actions = today_stats.get_total_actions()
        
        overview = f"""[bright_yellow]📅 Ngày:[/bright_yellow] [bright_green]{today_date}[/bright_green]
[bright_yellow]👥 Tài khoản UNIQUE:[/bright_yellow] [bold bright_green]{total_accounts}[/bold bright_green]
[bright_yellow]🔄 Tổng phiên farm:[/bright_yellow] [bright_green]{total_sessions}[/bright_green]
[bright_yellow]⏱️  Tổng thời gian:[/bright_yellow] [bold bright_cyan]{duration_str}[/bold bright_cyan]"""
        
        console.print(Panel(
            overview, 
            title="[bold bright_cyan]═══ TỔNG QUAN ═══[/bold bright_cyan]",
            border_style="bright_cyan", 
            box=box.DOUBLE_EDGE
        ))
        console.print()
        
        # Bảng actions tổng
        actions_table = Table(
            box=box.HEAVY_EDGE,
            show_header=True,
            header_style="bold bright_yellow",
            border_style="bright_magenta",
            title="[bold bright_magenta]═══ TỔNG THAO TÁC ═══[/bold bright_magenta]"
        )
        
        actions_table.add_column("Thao tác", style="bright_cyan bold", width=20)
        actions_table.add_column("Số lần", justify="center", style="bright_green bold", width=15)
        
        actions_table.add_row("❤️  Like", str(total_actions.get('like', 0)))
        actions_table.add_row("👥 Follow", str(total_actions.get('follow', 0)))
        actions_table.add_row("💬 Comment", str(total_actions.get('comment', 0)))
        actions_table.add_row("📬 Thông báo", str(total_actions.get('notification', 0)))
        actions_table.add_row("🛍️  Cửa hàng", str(total_actions.get('shop', 0)))
        if total_actions.get('not_interested', 0) > 0:
            actions_table.add_row("[yellow]🚫 Không quan tâm[/yellow]", f"[yellow]{total_actions['not_interested']}[/yellow]")
        if total_actions.get('repost', 0) > 0:
            actions_table.add_row("[yellow]🔄 Đăng lại[/yellow]", f"[yellow]{total_actions['repost']}[/yellow]")
        
        console.print(actions_table)
        console.print()
        
        # Bảng chi tiết từng account - KHÔNG TRÙNG LẶP
        console.print("[bold bright_cyan]═══ CHI TIẾT TỪNG TÀI KHOẢN ═══[/bold bright_cyan]")
        console.print()
        
        accounts_table = Table(
            box=box.DOUBLE_EDGE,
            show_header=True,
            header_style="bold bright_yellow",
            border_style="bright_cyan",
            title="[bold bright_cyan]Danh sách accounts đã farm[/bold bright_cyan]"
        )
        
        accounts_table.add_column("STT", justify="center", style="bright_cyan bold", width=6)
        accounts_table.add_column("Account", style="bright_green bold", width=20)
        accounts_table.add_column("Phiên", justify="center", style="bright_yellow", width=8)
        accounts_table.add_column("Thời gian", justify="center", style="bright_magenta", width=12)
        accounts_table.add_column("Actions", style="dim bright_white", width=40)
        accounts_table.add_column("Follow Được", justify="center", style="bright_green", width=12)
        accounts_table.add_column("Status", justify="center", style="bold", width=12)
        
        # Sort accounts by name
        sorted_accounts = sorted(today_stats.accounts.items(), key=lambda x: x[0])
        
        for idx, (acc_name, acc_stats) in enumerate(sorted_accounts, 1):
            duration = stats_manager.format_duration(acc_stats.total_duration_seconds)
            
            actions_parts = [
                f"❤️{acc_stats.total_actions.get('like', 0)}",
                f"👥{acc_stats.total_actions.get('follow', 0)}",
                f"💬{acc_stats.total_actions.get('comment', 0)}"
            ]
            if acc_stats.total_actions.get('not_interested', 0) > 0:
                actions_parts.append(f"🚫{acc_stats.total_actions['not_interested']}")
            if acc_stats.total_actions.get('repost', 0) > 0:
                actions_parts.append(f"🔄{acc_stats.total_actions['repost']}")
            actions_str = " ".join(actions_parts)
            
            # Status với màu
            if acc_stats.checkpoint_status == "healthy":
                status = "[green]✅ Khỏe[/green]"
            elif acc_stats.checkpoint_status == "checkpoint":
                status = "[red]⚠️  Checkpoint[/red]"
            else:
                status = "[dim]❓ Unknown[/dim]"
            
            # Follow success count
            follow_count = acc_stats.total_actions.get('follow', 0)
            follow_display = f"[bright_green]{follow_count}[/bright_green]" if follow_count > 0 else "[dim]0[/dim]"
            
            accounts_table.add_row(
                str(idx),
                acc_name,
                str(acc_stats.sessions_count),
                duration,
                actions_str,
                follow_display,
                status
            )
        console.print(accounts_table)
# ═══════════════════════════════════════════════════════════════
# 📊 PROFESSIONAL DASHBOARD COMPONENTS v1.4.6
# ═══════════════════════════════════════════════════════════════
class DashboardComponents:
    """Professional dashboard components for live monitoring"""

    @staticmethod
    def create_metric_card(title: str, value: str, icon: str = "📊",
                           color: str = None, subtitle: str = None):
        if not RICH_AVAILABLE:
            return None
        from ui.constants import ColorScheme
        if color is None:
            color = ColorScheme.PRIMARY
        content = f"[bold {color}]{icon}[/bold {color}]\n\n[bold white]{value}[/bold white]\n"
        if subtitle:
            content += f"[dim]{subtitle}[/dim]"
        return Panel(
            Align.center(content, vertical="middle"),
            title=f"[bold dim]{title}[/bold dim]",
            border_style=color, box=box.ROUNDED, padding=(1, 2), height=7
        )

    @staticmethod
    def create_progress_bar(current: int, total: int, width: int = 30) -> str:
        if total == 0:
            return "[dim]N/A[/dim]"
        percentage = current / total * 100
        filled     = int(width * current / total)
        color = "bright_red" if percentage < 30 else ("bright_yellow" if percentage < 70 else "bright_green")
        bar = "█" * filled + "░" * (width - filled)
        return f"[{color}]{bar}[/{color}] [{color}]{current}/{total} ({percentage:.1f}%)[/{color}]"

    @staticmethod
    def create_status_badge(status: str) -> str:
        status_map = {
            "active":  ("bright_green",  "●", "ACTIVE"),
            "idle":    ("bright_yellow", "●", "IDLE"),
            "error":   ("bright_red",    "●", "ERROR"),
            "success": ("bright_green",  "✓", "SUCCESS"),
            "pending": ("bright_cyan",   "○", "PENDING"),
        }
        color, icon, text = status_map.get(status.lower(), ("dim", "○", "KHÔNG RÕ"))
        return f"[{color}]{icon} {text}[/{color}]"
