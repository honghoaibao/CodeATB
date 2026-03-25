"""
╔══════════════════════════════════════════════════════╗
║           models/proxy.py - v1.4.5                   ║
║   Quản lý Proxy với auto-switch và health tracking   ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → ProxyEntry + ProxyManager (line ~376)
"""

import os
import json
import uuid
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Set
from threading import Lock


@dataclass
class ProxyEntry:
    """
    Một proxy entry với tracking usage và success rate
    """

    id: str
    name: str
    proxy_type: str  # http, https, socks4, socks5
    host: str
    port: int
    username: str = ""
    password: str = ""
    is_active: bool = False
    created_at: str = ""
    last_used: Optional[str] = None
    usage_count: int = 0
    success_count: int = 0
    fail_count: int = 0

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def mark_used(self, success: bool = True):
        """Record usage result"""
        self.last_used = datetime.now().isoformat()
        self.usage_count += 1
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1

    def get_success_rate(self) -> float:
        """Return success rate (0.0 – 1.0). Returns 1.0 if never used."""
        if self.usage_count == 0:
            return 1.0
        return self.success_count / self.usage_count

    def get_proxy_url(self) -> str:
        """Build proxy URL string"""
        if self.username and self.password:
            return f"{self.proxy_type}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.proxy_type}://{self.host}:{self.port}"

    def get_masked_password(self) -> str:
        """Return masked password for display"""
        if not self.password:
            return ""
        if len(self.password) <= 2:
            return "*" * len(self.password)
        return self.password[0] + "*" * (len(self.password) - 2) + self.password[-1]


class ProxyManager:
    """
    Quản lý nhiều proxies với auto-switch
    """

    def __init__(self, storage_path: str = "proxies.json"):
        self.storage_path = storage_path
        self.proxies: List[ProxyEntry] = []
        self.auto_switch_enabled: bool = False
        self.lock = Lock()
        self.load_from_file()

    # ───────────────────────────────────────
    # CRUD operations
    # ───────────────────────────────────────

    def add_proxy(
        self,
        name: str,
        proxy_type: str,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
    ) -> ProxyEntry:
        """Add new proxy"""
        with self.lock:
            proxy = ProxyEntry(
                id=str(uuid.uuid4()),
                name=name,
                proxy_type=proxy_type,
                host=host,
                port=port,
                username=username,
                password=password,
                is_active=len(self.proxies) == 0,  # First proxy is active
            )
            self.proxies.append(proxy)
            self.save_to_file()
            return proxy

    def remove_proxy(self, proxy_id: str) -> bool:
        """Remove proxy by id"""
        with self.lock:
            for i, proxy in enumerate(self.proxies):
                if proxy.id == proxy_id:
                    if proxy.is_active and len(self.proxies) > 1:
                        next_idx = (i + 1) % len(self.proxies)
                        self.proxies[next_idx].is_active = True
                    self.proxies.pop(i)
                    self.save_to_file()
                    return True
            return False

    def select_proxy(self, proxy_id: str) -> bool:
        """Set active proxy by id"""
        with self.lock:
            for proxy in self.proxies:
                proxy.is_active = False
            for proxy in self.proxies:
                if proxy.id == proxy_id:
                    proxy.is_active = True
                    self.save_to_file()
                    return True
            return False

    # ───────────────────────────────────────
    # Getters
    # ───────────────────────────────────────

    def get_active_proxy(self) -> Optional[ProxyEntry]:
        """Get active proxy. Auto-activates first proxy if none active."""
        for proxy in self.proxies:
            if proxy.is_active:
                return proxy
        if self.proxies:
            self.proxies[0].is_active = True
            self.save_to_file()
            return self.proxies[0]
        return None

    def get_all_proxies(self) -> List[ProxyEntry]:
        """Get copy of all proxies"""
        return self.proxies.copy()

    # ───────────────────────────────────────
    # Auto-switch
    # ───────────────────────────────────────

    def switch_to_next(self) -> Optional[ProxyEntry]:
        """Rotate to the next proxy in the list"""
        with self.lock:
            if not self.proxies:
                return None

            current_idx = next(
                (i for i, p in enumerate(self.proxies) if p.is_active), -1
            )
            next_idx = (current_idx + 1) % len(self.proxies)

            for proxy in self.proxies:
                proxy.is_active = False
            self.proxies[next_idx].is_active = True
            self.save_to_file()
            return self.proxies[next_idx]

    # ───────────────────────────────────────
    # Persistence (secure atomic write)
    # ───────────────────────────────────────

    def save_to_file(self):
        """Save proxies to JSON with secure permissions (600)"""
        try:
            data = {
                "version": "1.4.5",
                "auto_switch_enabled": self.auto_switch_enabled,
                "proxies": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "proxy_type": p.proxy_type,
                        "host": p.host,
                        "port": p.port,
                        "username": p.username,
                        "password": p.password,
                        "is_active": p.is_active,
                        "created_at": p.created_at,
                        "last_used": p.last_used,
                        "usage_count": p.usage_count,
                        "success_count": p.success_count,
                        "fail_count": p.fail_count,
                    }
                    for p in self.proxies
                ],
            }

            parent = os.path.dirname(self.storage_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            temp_path = self.storage_path + ".tmp"
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)

            try:
                os.chmod(temp_path, 0o600)
            except Exception:
                pass

            os.replace(temp_path, self.storage_path)

            try:
                os.chmod(self.storage_path, 0o600)
            except Exception:
                pass

        except Exception as e:
            print(f"⚠️  Failed to save proxies: {e}")

    def load_from_file(self):
        """Load proxies from JSON file"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    data = json.load(f)

                self.auto_switch_enabled = data.get("auto_switch_enabled", False)
                self.proxies = [
                    ProxyEntry(
                        id=p["id"],
                        name=p["name"],
                        proxy_type=p["proxy_type"],
                        host=p["host"],
                        port=p["port"],
                        username=p.get("username", ""),
                        password=p.get("password", ""),
                        is_active=p["is_active"],
                        created_at=p["created_at"],
                        last_used=p.get("last_used"),
                        usage_count=p.get("usage_count", 0),
                        success_count=p.get("success_count", 0),
                        fail_count=p.get("fail_count", 0),
                    )
                    for p in data.get("proxies", [])
                ]
        except Exception as e:
            print(f"⚠️  Failed to load proxies: {e}")
            self.proxies = []
            self.auto_switch_enabled = False
