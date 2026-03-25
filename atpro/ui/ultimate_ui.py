"""
╔══════════════════════════════════════════════════════╗
║           ui/ultimate_ui.py - v1.4.5                 ║
║   UltimateUI - Toàn bộ UI components của AT Tool    ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → UltimateUI (line ~2695)

Cung cấp:
  - Banner, section dividers
  - Mega stats tables với visual bars
  - Interactive tree menus
  - Styled message panels
  - Progress panels
  - Animated loading spinners
"""

import time
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.align import Align
from rich.rule import Rule
from rich.tree import Tree
from rich import box

from .constants import ColorScheme

console = Console()


class UltimateUI:
    """
    Ultimate UI Components v1.4.5

    Tất cả UI elements dùng trong AT Tool:
    - Banners, headers, dividers
    - Stats tables với ASCII bars
    - Interactive menus
    - Message panels (success/error/warning/info/critical)
    - Progress tracking panels
    - Animated loading
    """

    # ─────────────────────────────────────────
    # Banner / Header
    # ─────────────────────────────────────────

    @staticmethod
    def show_ultimate_banner(title: str, subtitle: str = "", version: str = "v1.4.5"):
        """Hiển thị banner lớn với gradient title"""
        console.clear()
        gradient_title = ColorScheme.gradient_text(title, ["blue", "cyan", "bright_blue"])

        banner_lines = [
            "",
            f"[bold]╔{'═' * 63}╗[/bold]",
            f"[bold]║[/bold] {gradient_title.center(70)} [bold]║[/bold]",
        ]
        if subtitle:
            banner_lines.append(
                f"[bold]║[/bold] [dim]{subtitle.center(61)}[/dim] [bold]║[/bold]"
            )
        banner_lines.extend([
            f"[bold]║[/bold] [dim]{f'{version} Professional Edition'.center(61)}[/dim] [bold]║[/bold]",
            f"[bold]╚{'═' * 63}╝[/bold]",
            "",
        ])

        console.print(Panel(
            "\n".join(banner_lines),
            border_style=ColorScheme.PRIMARY,
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
            expand=False,
        ))
        console.print()

    @staticmethod
    def show_section_divider(title: str, icon: str = "", style: str = None):
        """Hiển thị divider đẹp giữa các section"""
        if style is None:
            style = ColorScheme.PRIMARY
        display_text = f"{icon} {title}" if icon else title
        console.print()
        console.print(Rule(
            f"[bold {style}]{display_text}[/bold {style}]",
            style=style,
            characters="━",
        ))
        console.print()

    # ─────────────────────────────────────────
    # Stats table
    # ─────────────────────────────────────────

    @staticmethod
    def show_mega_stats(stats: dict, title: str = "Statistics", show_bars: bool = True):
        """Bảng thống kê với ASCII progress bars"""
        table = Table(
            show_header=True,
            header_style=f"bold {ColorScheme.PRIMARY}",
            border_style=ColorScheme.PRIMARY,
            box=box.HEAVY_EDGE,
            pad_edge=True,
            expand=True,
        )
        table.add_column("📊 Metric", style=f"bold {ColorScheme.TEXT_PRIMARY}", width=25)
        table.add_column("Value", style=ColorScheme.SUCCESS, justify="right", width=15)
        if show_bars:
            table.add_column("Biểu đồ", width=35)

        numeric_values = [
            v for v in stats.values()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        max_val = max(numeric_values) if numeric_values else 100

        for key, value in stats.items():
            if isinstance(value, float):
                value_str = f"{value:.2f}"
            elif isinstance(value, bool):
                value_str = "✅" if value else "❌"
            else:
                value_str = str(value)

            if show_bars and isinstance(value, (int, float)) and not isinstance(value, bool):
                percentage = (value / max_val * 100) if max_val > 0 else 0
                bar_width = int(percentage / 5)
                bar_color = (
                    ColorScheme.SUCCESS if percentage >= 80
                    else ColorScheme.WARNING if percentage >= 50
                    else ColorScheme.ERROR
                )
                bar = "█" * bar_width + "░" * (20 - bar_width)
                visual = f"[{bar_color}]{bar}[/{bar_color}] {percentage:.0f}%"
                table.add_row(key, value_str, visual)
            else:
                if show_bars:
                    table.add_row(key, value_str, "")
                else:
                    table.add_row(key, value_str)

        console.print(Panel(
            table,
            title=f"[bold {ColorScheme.PRIMARY}]📊 {title}[/bold {ColorScheme.PRIMARY}]",
            border_style=ColorScheme.PRIMARY,
            box=box.HEAVY_EDGE,
            padding=(1, 2),
        ))
        console.print()

    # ─────────────────────────────────────────
    # Interactive menu
    # ─────────────────────────────────────────

    @staticmethod
    def show_interactive_menu(title: str, options: dict, description: str = "") -> str:
        """Menu dạng tree với Rich styling"""
        console.print()
        console.print(Panel(
            Align.center(f"[bold {ColorScheme.PRIMARY}]{title}[/bold {ColorScheme.PRIMARY}]"),
            border_style=ColorScheme.PRIMARY,
            box=box.HEAVY_EDGE,
        ))

        if description:
            console.print(f"[dim]{description}[/dim]")
        console.print()

        tree = Tree(
            f"[bold {ColorScheme.ACCENT}]📋 Available Options[/bold {ColorScheme.ACCENT}]",
            guide_style=ColorScheme.PRIMARY,
        )

        for key, value in options.items():
            parts = value.split(maxsplit=1)
            if len(parts) == 2:
                icon, text = parts
                display = (
                    f"[{ColorScheme.TEXT_PRIMARY}]{key}[/{ColorScheme.TEXT_PRIMARY}]"
                    f" → {icon} {text}"
                )
            else:
                display = (
                    f"[{ColorScheme.TEXT_PRIMARY}]{key}[/{ColorScheme.TEXT_PRIMARY}]"
                    f" → {value}"
                )
            tree.add(display)

        console.print(Panel(
            tree,
            border_style=ColorScheme.PRIMARY,
            box=box.ROUNDED,
            padding=(1, 2),
        ))
        console.print()

        return Prompt.ask(
            f"[bold {ColorScheme.ACCENT}]❯ Your choice[/bold {ColorScheme.ACCENT}]",
            choices=list(options.keys()),
            show_choices=False,
        )

    # ─────────────────────────────────────────
    # Message panels
    # ─────────────────────────────────────────

    @staticmethod
    def show_message(message: str, message_type: str = "info", details: str = "", title: str = ""):
        """Panel thông báo với icon và màu sắc theo loại"""
        type_config = {
            "success": {
                "icon": "✅",
                "color": ColorScheme.SUCCESS,
                "box_style": box.HEAVY_EDGE,
                "default_title": "Thành công",
            },
            "error": {
                "icon": "❌",
                "color": ColorScheme.ERROR,
                "box_style": box.HEAVY_EDGE,
                "default_title": "Error",
            },
            "warning": {
                "icon": "⚠️",
                "color": ColorScheme.WARNING,
                "box_style": box.HEAVY_EDGE,
                "default_title": "Warning",
            },
            "info": {
                "icon": "ℹ️",
                "color": ColorScheme.INFO,
                "box_style": box.ROUNDED,
                "default_title": "Thông tin",
            },
            "critical": {
                "icon": "🚨",
                "color": ColorScheme.CRITICAL,
                "box_style": box.DOUBLE_EDGE,
                "default_title": "CRITICAL",
            },
        }

        cfg = type_config.get(message_type, type_config["info"])
        display_title = title or cfg["default_title"]
        content = f"[bold {cfg['color']}]{cfg['icon']} {message}[/bold {cfg['color']}]"
        if details:
            content += f"\n\n[dim]{details}[/dim]"

        console.print(Panel(
            Align.center(content),
            title=f"[bold {cfg['color']}]{display_title}[/bold {cfg['color']}]",
            border_style=cfg["color"],
            box=cfg["box_style"],
            padding=(1, 2),
        ))
        console.print()

    # ─────────────────────────────────────────
    # Progress panel
    # ─────────────────────────────────────────

    @staticmethod
    def show_progress_panel(items: list, title: str = "Progress"):
        """Bảng progress với status icons và visual bars"""
        table = Table(
            show_header=True,
            header_style=f"bold {ColorScheme.PRIMARY}",
            border_style=ColorScheme.PRIMARY,
            box=box.ROUNDED,
            pad_edge=True,
        )
        table.add_column("Item", style=ColorScheme.TEXT_PRIMARY, width=30)
        table.add_column("Trạng thái", justify="center", width=10)
        table.add_column("Progress", width=35)

        status_icons = {
            "completed": f"[{ColorScheme.SUCCESS}]✅[/{ColorScheme.SUCCESS}]",
            "running":   f"[{ColorScheme.STATUS_RUNNING}]🔄[/{ColorScheme.STATUS_RUNNING}]",
            "pending":   f"[{ColorScheme.STATUS_PENDING}]⏳[/{ColorScheme.STATUS_PENDING}]",
            "error":     f"[{ColorScheme.ERROR}]❌[/{ColorScheme.ERROR}]",
            "warning":   f"[{ColorScheme.WARNING}]⚠️[/{ColorScheme.WARNING}]",
        }

        bar_colors = {
            "completed": ColorScheme.SUCCESS,
            "error":     ColorScheme.ERROR,
            "running":   ColorScheme.STATUS_RUNNING,
        }

        for item in items:
            name     = item.get("name", "Không rõ")
            status   = item.get("status", "pending")
            progress = item.get("progress", 0)

            status_icon = status_icons.get(status, "•")
            bar_color   = bar_colors.get(status, ColorScheme.STATUS_PENDING)
            bar_width   = int(progress / 5)
            bar         = "█" * bar_width + "░" * (20 - bar_width)
            progress_display = f"[{bar_color}]{bar}[/{bar_color}] {progress}%"

            table.add_row(name, status_icon, progress_display)

        console.print(Panel(
            table,
            title=f"[bold {ColorScheme.PRIMARY}]⚡ {title}[/bold {ColorScheme.PRIMARY}]",
            border_style=ColorScheme.PRIMARY,
            box=box.HEAVY_EDGE,
        ))
        console.print()

    # ─────────────────────────────────────────
    # Animations
    # ─────────────────────────────────────────

    @staticmethod
    def show_animated_loading(message: str, duration: float = 2.0, spinner: str = "dots12"):
        """Spinner animation trong khi loading"""
        with Progress(
            SpinnerColumn(spinner_name=spinner, style=ColorScheme.PRIMARY),
            TextColumn(f"[{ColorScheme.INFO}]{message}...[/{ColorScheme.INFO}]"),
            transient=True,
        ) as progress:
            progress.add_task("loading", total=None)
            time.sleep(duration)

    @staticmethod
    def clear_screen_animated():
        """Clear screen with smooth animation"""
        console.clear()
        time.sleep(0.1)

# Global Ultimate UI instance
ultimate_ui = UltimateUI()

# ═══════════════════════════════════════════════════════════════
# 🎨 ULTIMATE UI COMPONENTS v1.4.3
# ═══════════════════════════════════════════════════════════════
    
