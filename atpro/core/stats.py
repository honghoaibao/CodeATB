"""
╔══════════════════════════════════════════════════════╗
║           core/stats.py - v1.4.5                     ║
║   Statistics + Timing - Tất cả thống kê AT Tool     ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py:
  - FarmSession        (line ~4290)
  - AccountDayStats    (line ~4302)
  - DayStats           (line ~4313)
  - StatsManager       (line ~4343)
  - AdvancedStatistics (line ~5509)
  - TimingCalculator   (line ~4232)
"""

import os
import json
import csv
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False

try:
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


from ui.logger import smart_logger
# ─────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────

@dataclass
class FarmSession:
    """Một phiên farm của 1 account"""
    account: str
    start_time: datetime
    end_time: datetime
    duration_seconds: int
    actions: Dict[str, int] = field(default_factory=dict)
    success: bool = True
    proxy_used: Optional[str] = None
    checkpoint_status: str = "unknown"   # unknown | healthy | checkpoint


@dataclass
class AccountDayStats:
    """Thống kê 1 account trong 1 ngày - không trùng lặp"""
    account: str
    total_duration_seconds: int = 0
    total_actions: Dict[str, int] = field(default_factory=lambda: {
        "like": 0, "follow": 0, "comment": 0, "notification": 0, "shop": 0,
        "not_interested": 0, "repost": 0,
    })
    sessions_count: int = 0
    last_session_time: Optional[datetime] = None
    checkpoint_status: str = "unknown"


@dataclass
class DayStats:
    """Thống kê của 1 ngày"""
    date: str                            # YYYY-MM-DD
    accounts: Dict[str, AccountDayStats] = field(default_factory=dict)

    def get_total_accounts(self) -> int:
        return len(self.accounts)

    def get_total_duration_seconds(self) -> int:
        return sum(a.total_duration_seconds for a in self.accounts.values())

    def get_total_actions(self) -> Dict[str, int]:
        total = {"like": 0, "follow": 0, "comment": 0, "notification": 0,
                 "shop": 0, "not_interested": 0, "repost": 0}
        for acc in self.accounts.values():
            for k, v in acc.total_actions.items():
                if k in total:
                    total[k] += v
        return total

    def get_total_sessions(self) -> int:
        return sum(a.sessions_count for a in self.accounts.values())


# ─────────────────────────────────────────────────────────────────
# StatsManager
# ─────────────────────────────────────────────────────────────────

class StatsManager:
    """Quản lý thống kê v1.4.5 - không trùng lặp accounts"""

    def __init__(self, stats_file: str = "at_tool_stats.json"):
        self.stats_file = stats_file
        self.stats: Dict[str, DayStats] = {}
        self.load()

    def _vn_tz(self):
        if PYTZ_AVAILABLE:
            return pytz.timezone("Asia/Ho_Chi_Minh")
        return None

    # ── Persistence ──────────────────────────────────────────────

    def load(self):
        try:
            if not os.path.exists(self.stats_file):
                return
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for date_str, day_data in data.items():
                accounts_dict: Dict[str, AccountDayStats] = {}
                for acc_name, acc_data in day_data.get("accounts", {}).items():
                    last_session = None
                    if acc_data.get("last_session_time"):
                        try:
                            last_session = datetime.fromisoformat(acc_data["last_session_time"])
                        except Exception:
                            pass
                    accounts_dict[acc_name] = AccountDayStats(
                        account=acc_name,
                        total_duration_seconds=acc_data.get("total_duration_seconds", 0),
                        total_actions=acc_data.get("total_actions", {}),
                        sessions_count=acc_data.get("sessions_count", 0),
                        last_session_time=last_session,
                        checkpoint_status=acc_data.get("checkpoint_status", "unknown"),
                    )
                self.stats[date_str] = DayStats(date=date_str, accounts=accounts_dict)
        except Exception as e:
            print(f"Lỗi load stats: {e}")

    def save(self):
        try:
            data: dict = {}
            for date_str, day_stats in self.stats.items():
                accounts_data: dict = {}
                for acc_name, acc_stats in day_stats.accounts.items():
                    accounts_data[acc_name] = {
                        "account": acc_stats.account,
                        "total_duration_seconds": acc_stats.total_duration_seconds,
                        "total_actions": acc_stats.total_actions,
                        "sessions_count": acc_stats.sessions_count,
                        "last_session_time": (
                            acc_stats.last_session_time.isoformat()
                            if acc_stats.last_session_time else None
                        ),
                        "checkpoint_status": acc_stats.checkpoint_status,
                    }
                data[date_str] = {"date": day_stats.date, "accounts": accounts_data}
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Lỗi save stats: {e}")

    # ── Write ─────────────────────────────────────────────────────

    def add_session(self, session: FarmSession):
        """Thêm session - cộng dồn vào account đã có"""
        tz = self._vn_tz()
        if tz:
            date_str = session.start_time.astimezone(tz).strftime("%Y-%m-%d")
        else:
            date_str = session.start_time.strftime("%Y-%m-%d")

        if date_str not in self.stats:
            self.stats[date_str] = DayStats(date=date_str)

        day_stats = self.stats[date_str]
        acc_name = session.account

        if acc_name not in day_stats.accounts:
            day_stats.accounts[acc_name] = AccountDayStats(account=acc_name)

        acc = day_stats.accounts[acc_name]
        acc.total_duration_seconds += session.duration_seconds
        acc.sessions_count += 1
        acc.last_session_time = session.end_time

        if session.checkpoint_status != "unknown":
            acc.checkpoint_status = session.checkpoint_status

        for action_type, count in session.actions.items():
            if action_type in acc.total_actions:
                acc.total_actions[action_type] += count
            else:
                acc.total_actions[action_type] = count

        self.save()

    # ── Read ──────────────────────────────────────────────────────

    def get_today_stats(self) -> Optional[DayStats]:
        tz = self._vn_tz()
        today = datetime.now(tz).strftime("%Y-%m-%d") if tz else datetime.now().strftime("%Y-%m-%d")
        return self.stats.get(today)

    def get_week_stats(self) -> Dict[str, DayStats]:
        tz = self._vn_tz()
        today = datetime.now(tz).date() if tz else datetime.now().date()
        result: Dict[str, DayStats] = {}
        for i in range(7):
            d = today - timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            if ds in self.stats:
                result[ds] = self.stats[ds]
        return result

    def get_month_stats(self) -> Dict[str, DayStats]:
        tz = self._vn_tz()
        now = datetime.now(tz) if tz else datetime.now()
        month_str = now.strftime("%Y-%m")
        return {ds: v for ds, v in self.stats.items() if ds.startswith(month_str)}

    def get_success_rate(self, days: int = 7) -> Dict:
        tz = self._vn_tz()
        today = (datetime.now(tz) if tz else datetime.now()).date()
        total = checkpoint = healthy = 0
        for i in range(days):
            d = today - timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            if ds in self.stats:
                for acc_stats in self.stats[ds].accounts.values():
                    total += 1
                    if acc_stats.checkpoint_status == "checkpoint":
                        checkpoint += 1
                    elif acc_stats.checkpoint_status == "healthy":
                        healthy += 1
        return {
            "total_accounts": total,
            "healthy": healthy,
            "checkpoint": checkpoint,
            "success_rate": round(healthy / total * 100, 2) if total else 0,
            "checkpoint_rate": round(checkpoint / total * 100, 2) if total else 0,
            "days_analyzed": days,
        }

    def get_trend_analysis(self, days: int = 7) -> Dict[str, list]:
        tz = self._vn_tz()
        today = (datetime.now(tz) if tz else datetime.now()).date()
        trends: Dict[str, list] = {
            "dates": [], "accounts_count": [], "total_sessions": [],
            "total_actions": [], "avg_duration": [],
        }
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            trends["dates"].append(d.strftime("%m/%d"))
            if ds in self.stats:
                day = self.stats[ds]
                n = len(day.accounts)
                sessions = sum(a.sessions_count for a in day.accounts.values())
                actions = sum(sum(a.total_actions.values()) for a in day.accounts.values())
                dur = sum(a.total_duration_seconds for a in day.accounts.values())
                avg_dur = (dur // 60 // n) if n else 0
                trends["accounts_count"].append(n)
                trends["total_sessions"].append(sessions)
                trends["total_actions"].append(actions)
                trends["avg_duration"].append(avg_dur)
            else:
                trends["accounts_count"].append(0)
                trends["total_sessions"].append(0)
                trends["total_actions"].append(0)
                trends["avg_duration"].append(0)
        return trends

    def get_performance_metrics(self) -> Dict:
        total_sessions = total_actions = total_duration = 0
        unique_accounts: set = set()
        for day in self.stats.values():
            for acc_name, acc in day.accounts.items():
                unique_accounts.add(acc_name)
                total_sessions += acc.sessions_count
                total_actions += sum(acc.total_actions.values())
                total_duration += acc.total_duration_seconds
        return {
            "total_sessions": total_sessions,
            "total_actions": total_actions,
            "total_duration_hours": round(total_duration / 3600, 2),
            "unique_accounts": len(unique_accounts),
            "avg_actions_per_session": total_actions // total_sessions if total_sessions else 0,
            "avg_duration_per_session_min": total_duration // total_sessions // 60 if total_sessions else 0,
            "total_days_tracked": len(self.stats),
        }

    def get_account_history(self, account_name: str, days: int = 30) -> Dict[str, list]:
        tz = self._vn_tz()
        today = (datetime.now(tz) if tz else datetime.now()).date()
        history: Dict[str, list] = {
            "dates": [], "sessions": [], "actions": [],
            "duration_min": [], "checkpoint_status": [],
        }
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)
            ds = d.strftime("%Y-%m-%d")
            if ds in self.stats and account_name in self.stats[ds].accounts:
                acc = self.stats[ds].accounts[account_name]
                history["dates"].append(d.strftime("%m/%d"))
                history["sessions"].append(acc.sessions_count)
                history["actions"].append(sum(acc.total_actions.values()))
                history["duration_min"].append(acc.total_duration_seconds // 60)
                history["checkpoint_status"].append(acc.checkpoint_status)
        return history

    def export_to_csv(self, output_file: str = "at_tool_stats.csv") -> bool:
        try:
            with open(output_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Date", "Account", "Sessions", "Duration (min)",
                    "Likes", "Follows", "Comments", "Shops",
                    "Checkpoint Status", "Last Session",
                ])
                for date_str in sorted(self.stats.keys(), reverse=True):
                    for acc_name, acc in self.stats[date_str].accounts.items():
                        acts = acc.total_actions
                        last = acc.last_session_time.strftime("%H:%M:%S") if acc.last_session_time else "N/A"
                        writer.writerow([
                            date_str, acc_name, acc.sessions_count,
                            acc.total_duration_seconds // 60,
                            acts.get("like", 0), acts.get("follow", 0),
                            acts.get("comment", 0), acts.get("shop", 0),
                            acc.checkpoint_status, last,
                        ])
            return True
        except Exception as e:
            print(f"Export CSV failed: {e}")
            return False

    def format_duration(self, seconds: int) -> str:
        """Format thời gian"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h{minutes:02d}m"
        else:
            return f"{minutes}m"

# Global stats manager
stats_manager = StatsManager()

"""
╔═══════════════════════════════════════════════════════════════╗
║           AT TOOL v1.4.3 - NEW FEATURES MODULE                ║
║                 TÍNH NĂNG MỚI v1.4.3                          ║
╚═══════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
import time
import random
import subprocess

# ═══════════════════════════════════════════════════════════════
# 1. SMART VIDEO INTERACTION v1.4.3
# ✨ Tương tác thông minh dựa trên số likes
# ═══════════════════════════════════════════════════════════════

class SmartVideoInteraction:
    """
    Tương tác video thông minh v1.4.3
    
    Tính năng:
    - Không quan tâm: Video có < 100 likes
    - Đăng lại (Repost): Video có > 10,000 likes
    """
    
    def create_ascii_chart(self, data: list, width: int = 40, height: int = 10, label: str = "") -> str:
        """
        v1.4.3: Create ASCII bar chart
        
        Args:
            data: List of values to chart
            width: Chart width in characters
            height: Chart height in lines
            label: Chart label
            
        Returns:
            ASCII chart string
        """
        if not data or max(data) == 0:
            return f"{label}: No data"
        
        max_value = max(data)
        chart_lines = []
        
        # Title
        chart_lines.append(f"\n{label}")
        chart_lines.append("─" * width)
        
        # Bars
        for i, value in enumerate(data):
            bar_length = int((value / max_value) * (width - 10)) if max_value > 0 else 0
            bar = "█" * bar_length
            chart_lines.append(f"{i+1:2d} │{bar} {value}")
        
        # Footer
        chart_lines.append("─" * width)
        chart_lines.append(f"Max: {max_value} | Avg: {sum(data)//len(data) if data else 0}")
        
        return "\n".join(chart_lines)

    def generate_visual_report(self, days: int = 7) -> str:
        """
        v1.4.3: Generate visual statistics report with ASCII charts
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Formatted report string
        """
        success_rate = self.get_success_rate(days)
        trends = self.get_trend_analysis(days)
        
        report_lines = []
        report_lines.append("\n" + "═" * 60)
        report_lines.append(f"📊 AT TOOL v1.4.3 - STATISTICS REPORT ({days} days)")
        report_lines.append("═" * 60)
        
        # Success rate section
        report_lines.append(f"\n🎯 SUCCESS RATE:")
        report_lines.append(f"  Total Accounts: {success_rate['total_accounts']}")
        report_lines.append(f"  Healthy: {success_rate['healthy']} ({success_rate['success_rate']}%)")
        report_lines.append(f"  Checkpoint: {success_rate['checkpoint']} ({success_rate['checkpoint_rate']}%)")
        
        # Trend charts
        if trends['accounts_count']:
            report_lines.append(self.create_ascii_chart(
                trends['accounts_count'], 
                width=50, 
                label="📈 Daily Accounts"
            ))
        
        if trends['total_actions']:
            report_lines.append(self.create_ascii_chart(
                trends['total_actions'], 
                width=50, 
                label="⚡ Daily Actions"
            ))
        
        report_lines.append("\n" + "═" * 60)
        
        return "\n".join(report_lines)
    
    

# Global stats manager
stats_manager = StatsManager()

"""
╔═══════════════════════════════════════════════════════════════╗
║           AT TOOL v1.4.3 - NEW FEATURES MODULE                ║
║                 TÍNH NĂNG MỚI v1.4.3                          ║
╚═══════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
import time
import random
import subprocess

# ═══════════════════════════════════════════════════════════════
# 1. SMART VIDEO INTERACTION v1.4.3
# ✨ Tương tác thông minh dựa trên số likes
# ═══════════════════════════════════════════════════════════════

    
    

# Global stats manager
stats_manager = StatsManager()

"""
╔═══════════════════════════════════════════════════════════════╗
║           AT TOOL v1.4.3 - NEW FEATURES MODULE                ║
║                 TÍNH NĂNG MỚI v1.4.3                          ║
╚═══════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
import time
import random
import subprocess

# ═══════════════════════════════════════════════════════════════
# 1. SMART VIDEO INTERACTION v1.4.3
# ✨ Tương tác thông minh dựa trên số likes
# ═══════════════════════════════════════════════════════════════

    
    

# Global stats manager
stats_manager = StatsManager()

"""
╔═══════════════════════════════════════════════════════════════╗
║           AT TOOL v1.4.3 - NEW FEATURES MODULE                ║
║                 TÍNH NĂNG MỚI v1.4.3                          ║
╚═══════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import re
import time
import random
import subprocess

# ═══════════════════════════════════════════════════════════════
# 1. SMART VIDEO INTERACTION v1.4.3
# ✨ Tương tác thông minh dựa trên số likes
# ═══════════════════════════════════════════════════════════════

    

    


# ─────────────────────────────────────────────────────────────────
# AdvancedStatistics
# ─────────────────────────────────────────────────────────────────

class AdvancedStatistics:
    """Thống kê nâng cao - Weekly / Monthly / So sánh"""

    @staticmethod
    def get_weekly_report(stats_manager: StatsManager) -> Dict:
        tz = stats_manager._vn_tz()
        today = (datetime.now(tz) if tz else datetime.now()).date()
        monday = today - timedelta(days=today.weekday())

        report: Dict = {
            "week_start": monday.strftime("%d/%m/%Y"),
            "week_end": today.strftime("%d/%m/%Y"),
            "total_sessions": 0,
            "total_accounts": 0,
            "total_actions": {"like": 0, "follow": 0, "comment": 0,
                               "notification": 0, "shop": 0,
                               "not_interested": 0, "repost": 0},
            "daily_breakdown": [],
        }

        unique_accounts: set = set()
        for i in range(7):
            d = monday + timedelta(days=i)
            if d > today:
                break
            ds = d.strftime("%Y-%m-%d")
            day_data = {"date": d.strftime("%d/%m"), "sessions": 0, "accounts": 0, "actions": {}}
            if ds in stats_manager.stats:
                day = stats_manager.stats[ds]
                day_data["sessions"] = day.get_total_sessions()
                day_data["accounts"] = day.get_total_accounts()
                day_data["actions"] = day.get_total_actions()
                unique_accounts.update(day.accounts.keys())
                report["total_sessions"] += day_data["sessions"]
                for k, v in day.get_total_actions().items():
                    if k in report["total_actions"]:
                        report["total_actions"][k] += v
            report["daily_breakdown"].append(day_data)

        report["total_accounts"] = len(unique_accounts)
        return report

    @staticmethod
    def get_monthly_report(stats_manager) -> Dict:
        """
        Báo cáo tháng
        
        Returns:
            {
                'month': str (YYYY-MM),
                'total_sessions': int,
                'total_actions': Dict,
                'total_accounts': int,
                'weekly_breakdown': List[Dict]
            }
        """
        try:
            vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
            now = datetime.now(vn_tz)
            month_str = now.strftime("%Y-%m")
            
            # First day of month
            first_day = now.replace(day=1).date()
            
            # Last day of month
            if now.month == 12:
                last_day = now.replace(year=now.year+1, month=1, day=1).date() - timedelta(days=1)
            else:
                last_day = now.replace(month=now.month+1, day=1).date() - timedelta(days=1)
            
            report = {
                'month': month_str,
                'start_date': first_day.strftime("%Y-%m-%d"),
                'end_date': last_day.strftime("%Y-%m-%d"),
                'total_sessions': 0,
                'total_actions': {'like': 0, 'follow': 0, 'comment': 0,
                                 'notification': 0, 'shop': 0,
                                 'not_interested': 0, 'repost': 0},
                'total_accounts': set(),
                'weekly_breakdown': []
            }
            
            # Break down by weeks
            current_date = first_day
            week_num = 1
            
            while current_date <= last_day:
                week_end = min(current_date + timedelta(days=6), last_day)
                
                week_data = {
                    'week': week_num,
                    'start': current_date.strftime("%Y-%m-%d"),
                    'end': week_end.strftime("%Y-%m-%d"),
                    'sessions': 0,
                    'accounts': set(),
                    'actions': {'like': 0, 'follow': 0, 'comment': 0,
                               'notification': 0, 'shop': 0,
                               'not_interested': 0, 'repost': 0}
                }
                
                # Collect data for this week
                date = current_date
                while date <= week_end:
                    date_str = date.strftime("%Y-%m-%d")
                    
                    if date_str in stats_manager.stats:
                        day_stats = stats_manager.stats[date_str]
                        
                        week_data['sessions'] += day_stats.get_total_sessions()
                        
                        for acc in day_stats.accounts.keys():
                            week_data['accounts'].add(acc)
                            report['total_accounts'].add(acc)
                        
                        day_actions = day_stats.get_total_actions()
                        for action_type, count in day_actions.items():
                            if action_type in week_data['actions']:
                                week_data['actions'][action_type] += count
                    
                    date += timedelta(days=1)
                
                # Aggregate to monthly total
                report['total_sessions'] += week_data['sessions']
                
                for action_type, count in week_data['actions'].items():
                    if action_type in report['total_actions']:
                        report['total_actions'][action_type] += count
                
                week_data['accounts'] = len(week_data['accounts'])
                report['weekly_breakdown'].append(week_data)
                
                current_date = week_end + timedelta(days=1)
                week_num += 1
            
            report['total_accounts'] = len(report['total_accounts'])
            
            return report
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi get_monthly_report: {e}", force=True)
            return None
    
    @staticmethod
    def compare_periods(stats_manager, period1: Tuple[str, str], 
                       period2: Tuple[str, str]) -> Dict:
        """
        So sánh 2 khoảng thời gian
        
        Args:
            period1: (start_date, end_date) YYYY-MM-DD
            period2: (start_date, end_date) YYYY-MM-DD
            
        Returns:
            Comparison dict
        """
        try:
            def get_period_stats(start: str, end: str) -> Dict:
                """Helper to get stats for a period"""
                stats = {
                    'sessions': 0,
                    'accounts': set(),
                    'actions': {'like': 0, 'follow': 0, 'comment': 0,
                               'notification': 0, 'shop': 0,
                               'not_interested': 0, 'repost': 0}
                }
                
                from datetime import datetime
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
                
                current = start_date
                while current <= end_date:
                    date_str = current.strftime("%Y-%m-%d")
                    
                    if date_str in stats_manager.stats:
                        day_stats = stats_manager.stats[date_str]
                        stats['sessions'] += day_stats.get_total_sessions()
                        
                        for acc in day_stats.accounts.keys():
                            stats['accounts'].add(acc)
                        
                        day_actions = day_stats.get_total_actions()
                        for action_type, count in day_actions.items():
                            if action_type in stats['actions']:
                                stats['actions'][action_type] += count
                    
                    current += timedelta(days=1)
                
                stats['accounts'] = len(stats['accounts'])
                return stats
            
            period1_stats = get_period_stats(period1[0], period1[1])
            period2_stats = get_period_stats(period2[0], period2[1])
            
            comparison = {
                'period1': {
                    'dates': f"{period1[0]} → {period1[1]}",
                    'stats': period1_stats
                },
                'period2': {
                    'dates': f"{period2[0]} → {period2[1]}",
                    'stats': period2_stats
                },
                'changes': {}
            }
            
            # Calculate changes
            for key in ['sessions', 'accounts']:
                diff = period2_stats[key] - period1_stats[key]
                if period1_stats[key] > 0:
                    percent = (diff / period1_stats[key]) * 100
                else:
                    percent = 0 if diff == 0 else 100
                
                comparison['changes'][key] = {
                    'diff': diff,
                    'percent': percent
                }
            
            # Actions changes
            comparison['changes']['actions'] = {}
            for action_type in period1_stats['actions'].keys():
                diff = period2_stats['actions'][action_type] - period1_stats['actions'][action_type]
                if period1_stats['actions'][action_type] > 0:
                    percent = (diff / period1_stats['actions'][action_type]) * 100
                else:
                    percent = 0 if diff == 0 else 100
                
                comparison['changes']['actions'][action_type] = {
                    'diff': diff,
                    'percent': percent
                }
            
            return comparison
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi compare_periods: {e}", force=True)
            return None


    def get_stats_for_date(stats_manager, date_str: str) -> Optional[Dict]:
        """
        Lấy stats cho ngày cụ thể
        
        Args:
            date_str: "YYYY-MM-DD"
            
        Returns:
            Stats dict hoặc None
        """
        try:
            if date_str not in stats_manager.stats:
                return None
            
            day_stats = stats_manager.stats[date_str]
            
            return {
                'date': date_str,
                'total_sessions': day_stats.get_total_sessions(),
                'total_accounts': day_stats.get_total_accounts(),
                'total_actions': day_stats.get_total_actions(),
                'accounts_detail': {
                    acc: {
                        'sessions': acc_stats.sessions_count,
                        'actions': acc_stats.total_actions,
                        'duration': acc_stats.total_duration_seconds
                    }
                    for acc, acc_stats in day_stats.accounts.items()
                }
            }
            
        except Exception as e:
            smart_logger.log(f"❌ Lỗi get_stats_for_date: {e}", force=True)
            return None


    def format_weekly_report(report: Dict) -> Panel:
        """
        Format weekly report thành Panel
        """
        if not report:
            return Panel("[red]Không có dữ liệu[/red]", title="Weekly Report")
        
        # Summary table
        summary = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
        summary.add_column("Metric", style="bright_cyan")
        summary.add_column("Value", style="bright_yellow")
        
        summary.add_row("📅 Tuần", f"{report['start_date']} → {report['end_date']}")
        summary.add_row("🎯 Tổng Sessions", f"{report['total_sessions']:,}")
        summary.add_row("👥 Tổng Accounts", f"{report['total_accounts']:,}")
        summary.add_row("❤️  Likes", f"{report['total_actions']['like']:,}")
        summary.add_row("👤 Follows", f"{report['total_actions']['follow']:,}")
        summary.add_row("💬 Comments", f"{report['total_actions']['comment']:,}")
        summary.add_row("🛒 Shop", f"{report['total_actions']['shop']:,}")
        summary.add_row("🔔 Notifications", f"{report['total_actions']['notification']:,}")
        
        # v1.4.3 new actions
        if 'not_interested' in report['total_actions']:
            summary.add_row("🚫 Không quan tâm", f"{report['total_actions']['not_interested']:,}")
        if 'repost' in report['total_actions']:
            summary.add_row("🔄 Đăng lại", f"{report['total_actions']['repost']:,}")
        
        # Daily breakdown table
        daily = Table(title="📊 Chi Tiết Theo Ngày", box=box.ROUNDED, padding=(0, 1))
        daily.add_column("Ngày", style="bright_cyan")
        daily.add_column("Sessions", justify="right", style="bright_yellow")
        daily.add_column("Accounts", justify="right", style="bright_green")
        daily.add_column("Actions", justify="left", style="bright_magenta", width=50)
        
        for day in report['daily_breakdown']:
            # Build detailed actions string
            acts = day['actions']
            actions_str = f"❤️{acts.get('like',0)} 👥{acts.get('follow',0)} 💬{acts.get('comment',0)} 📬{acts.get('notification',0)} 🛍️{acts.get('shop',0)}"
            if acts.get('not_interested', 0) > 0:
                actions_str += f" 🚫{acts['not_interested']}"
            if acts.get('repost', 0) > 0:
                actions_str += f" 🔄{acts['repost']}"
            
            daily.add_row(
                day['date'],
                str(day['sessions']),
                str(day['accounts']),
                actions_str
            )
        
        content = f"{summary}\n\n{daily}"
        
        return Panel(
            content,
            title="[bold bright_cyan]📈 BÁO CÁO TUẦN[/bold bright_cyan]",
            border_style="bright_cyan",
            box=box.DOUBLE_EDGE
        )


    def format_monthly_report(report: Dict) -> Panel:
        """
        Format monthly report thành Panel
        """
        if not report:
            return Panel("[red]Không có dữ liệu[/red]", title="Monthly Report")
        
        # Summary
        summary = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
        summary.add_column("Metric", style="bright_cyan")
        summary.add_column("Value", style="bright_yellow")
        
        summary.add_row("📅 Tháng", report['month'])
        summary.add_row("🎯 Tổng Sessions", f"{report['total_sessions']:,}")
        summary.add_row("👥 Tổng Accounts", f"{report['total_accounts']:,}")
        summary.add_row("❤️  Likes", f"{report['total_actions']['like']:,}")
        summary.add_row("👤 Follows", f"{report['total_actions']['follow']:,}")
        summary.add_row("💬 Comments", f"{report['total_actions']['comment']:,}")
        
        # v1.4.3
        if 'not_interested' in report['total_actions']:
            summary.add_row("🚫 Không quan tâm", f"{report['total_actions']['not_interested']:,}")
        if 'repost' in report['total_actions']:
            summary.add_row("🔄 Đăng lại", f"{report['total_actions']['repost']:,}")
        
        # Weekly breakdown
        weekly = Table(title="📊 Chi Tiết Theo Tuần", box=box.ROUNDED, padding=(0, 1))
        weekly.add_column("Tuần", style="bright_cyan")
        weekly.add_column("Ngày", style="dim")
        weekly.add_column("Sessions", justify="right", style="bright_yellow")
        weekly.add_column("Accounts", justify="right", style="bright_green")
        weekly.add_column("Actions", justify="left", style="bright_magenta", width=50)
        
        for week in report['weekly_breakdown']:
            # Build detailed actions string
            acts = week['actions']
            actions_str = f"❤️{acts.get('like',0)} 👥{acts.get('follow',0)} 💬{acts.get('comment',0)} 📬{acts.get('notification',0)} 🛍️{acts.get('shop',0)}"
            if acts.get('not_interested', 0) > 0:
                actions_str += f" 🚫{acts['not_interested']}"
            if acts.get('repost', 0) > 0:
                actions_str += f" 🔄{acts['repost']}"
            
            weekly.add_row(
                f"Tuần {week['week']}",
                f"{week['start']} → {week['end']}",
                str(week['sessions']),
                str(week['accounts']),
                actions_str
            )
        
        content = f"{summary}\n\n{weekly}"
        
        return Panel(
            content,
            title="[bold bright_magenta]📊 BÁO CÁO THÁNG[/bold bright_magenta]",
            border_style="bright_magenta",
            box=box.DOUBLE_EDGE
        )
    
    
    


"""
═══════════════════════════════════════════════════════════════
✅ ADVANCED STATISTICS v1.4.3 - COMPLETED
═══════════════════════════════════════════════════════════════

✅ Weekly reports với daily breakdown
✅ Monthly reports với weekly breakdown
✅ Date picker support
✅ Period comparison
✅ Rich formatting với Tables/Panels

➡️  Integration với main app
═══════════════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════════════
# TIKTOK PACKAGE ENUM
# ═══════════════════════════════════════════════════════════════


# ─────────────────────────────────────────────────────────────────
# TimingCalculator
# ─────────────────────────────────────────────────────────────────

class TimingCalculator:
    """Calculator thời gian chính xác"""

    @staticmethod
    def calculate_total_time(start_time: datetime, end_time: datetime,
                             wait_time_seconds: int = 0,
                             rest_time_seconds: int = 0) -> Dict:
        elapsed = end_time - start_time
        total = int(elapsed.total_seconds())
        active = max(0, total - wait_time_seconds - rest_time_seconds)
        return {
            "total_seconds":   total,
            "active_seconds":  active,
            "wait_seconds":    wait_time_seconds,
            "rest_seconds":    rest_time_seconds,
            "total_formatted":  TimingCalculator.format_duration(total),
            "active_formatted": TimingCalculator.format_duration(active),
            "wait_formatted":   TimingCalculator.format_duration(wait_time_seconds),
            "rest_formatted":   TimingCalculator.format_duration(rest_time_seconds),
        }

    @staticmethod
    def format_duration(seconds: int) -> str:
        if seconds < 0:
            return "0s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        parts = []
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        if s or not parts: parts.append(f"{s}s")
        return " ".join(parts)

    @staticmethod
    def estimate_completion_time(current_index: int, total_items: int,
                                 elapsed_seconds: int) -> str:
        if current_index == 0:
            return "Calculating..."
        avg = elapsed_seconds / current_index
        remaining = int(avg * (total_items - current_index))
        return TimingCalculator.format_duration(remaining)


# ─────────────────────────────────────────────────────────────────
# Global singleton
# ─────────────────────────────────────────────────────────────────
stats_manager = StatsManager()
