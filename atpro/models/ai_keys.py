"""
╔══════════════════════════════════════════════════════╗
║           models/ai_keys.py - v1.4.5                 ║
║   Quản lý AI API Keys (Gemini / OpenAI / Anthropic)  ║
╚══════════════════════════════════════════════════════╝

Tách từ attv1_4_4-fix3.py → AIAPIKey + AIAPIKeyManager (line ~342)
"""

import os
import json
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Set
from threading import Lock


@dataclass
class AIAPIKey:
    """
    Multi-Provider AI API Key
    Supports: Gemini, OpenAI, Anthropic
    """

    id: str
    name: str
    api_key: str
    provider: str = "gemini"
    model: str = "gemini-1.5-flash-latest"
    is_active: bool = False
    created_at: str = ""
    last_used: Optional[str] = None
    usage_count: int = 0
    # ── Quota / model rotation tracking ──────────────────
    exhausted_models: list = None   # danh sách model đã hết quota trong session
    is_quota_exhausted: bool = False  # True khi tất cả models đều hết quota

    def __post_init__(self):
        if self.exhausted_models is None:
            self.exhausted_models = []
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def mark_used(self):
        """Mark this key as used"""
        self.last_used = datetime.now().isoformat()
        self.usage_count += 1

    def mark_model_exhausted(self, model: str) -> None:
        """Đánh dấu model này đã hết quota"""
        if model not in self.exhausted_models:
            self.exhausted_models.append(model)

    def reset_quota_status(self) -> None:
        """Reset trạng thái quota (mỗi ngày mới)"""
        self.exhausted_models = []
        self.is_quota_exhausted = False

    def get_masked_key(self) -> str:
        """Get masked version of API key for display"""
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return self.api_key[:4] + "*" * (len(self.api_key) - 8) + self.api_key[-4:]


class AIAPIKeyManager:
    """
    AI API Key Manager
    Quản lý nhiều API keys với auto-rotation khi fail
    """

    def __init__(self, storage_path: str = "ai_api_keys.json"):
        self.storage_path = storage_path
        self.keys: List[AIAPIKey] = []
        self.lock = Lock()
        self.load_from_file()

    # ───────────────────────────────────────
    # CRUD operations
    # ───────────────────────────────────────

    def add_key(
        self,
        name: str,
        api_key: str,
        provider: str = "gemini",
        model: str = "gemini-1.5-flash-latest",
    ) -> AIAPIKey:
        """Add new API key"""
        with self.lock:
            key = AIAPIKey(
                id=str(uuid.uuid4()),
                name=name,
                api_key=api_key,
                provider=provider,
                model=model,
                is_active=len(self.keys) == 0,  # First key is active by default
            )
            self.keys.append(key)
            self.save_to_file()
            return key

    def remove_key(self, key_id: str) -> bool:
        """Remove API key by id"""
        with self.lock:
            for i, key in enumerate(self.keys):
                if key.id == key_id:
                    # Promote next key if removing active key
                    if key.is_active and len(self.keys) > 1:
                        next_idx = (i + 1) % len(self.keys)
                        self.keys[next_idx].is_active = True
                    self.keys.pop(i)
                    self.save_to_file()
                    return True
            return False

    def select_key(self, key_id: str) -> bool:
        """Set active key by id"""
        with self.lock:
            for key in self.keys:
                key.is_active = False
            for key in self.keys:
                if key.id == key_id:
                    key.is_active = True
                    self.save_to_file()
                    return True
            return False

    # ───────────────────────────────────────
    # Getters
    # ───────────────────────────────────────

    def get_active_key(self) -> Optional[AIAPIKey]:
        """Get currently active key. Auto-activates first key if none active."""
        for key in self.keys:
            if key.is_active:
                return key
        if self.keys:
            self.keys[0].is_active = True
            self.save_to_file()
            return self.keys[0]
        return None

    def get_all_keys(self) -> List[AIAPIKey]:
        """Get copy of all keys"""
        return self.keys.copy()

    # ───────────────────────────────────────
    # Rotation / failover
    # ───────────────────────────────────────

    def get_fallback_models(self, provider: str = "gemini") -> list:
        """
        Lấy danh sách models fallback cho provider theo thứ tự ưu tiên.
        Dùng khi model hiện tại hết quota.
        """
        # Gemini fallback order: flash → pro → lite → experimental
        GEMINI_FALLBACK_ORDER = [
            "gemini-1.5-flash-latest",    # miễn phí, phổ biến nhất
            "gemini-1.5-flash-002",
            "gemini-1.5-flash",
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
            "gemini-2.0-flash-exp",
            "gemini-pro",
            "gemini-pro-vision",
        ]
        OPENAI_FALLBACK_ORDER = [
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4",
        ]
        if provider == "gemini":
            return GEMINI_FALLBACK_ORDER
        elif provider in ("openai", "openai_compat"):
            return OPENAI_FALLBACK_ORDER
        return []

    def rotate_model_for_key(self, key: 'AIAPIKey') -> Optional[str]:
        """
        Chuyển sang model tiếp theo cho key hiện tại khi hết quota.

        Returns:
            model_name mới nếu còn model khả dụng, None nếu hết tất cả.
        """
        fallback_models = self.get_fallback_models(key.provider)
        current_model   = key.model

        # Nếu không có danh sách fallback → không chuyển được
        if not fallback_models:
            key.is_quota_exhausted = True
            return None

        # Bắt đầu từ model ngay sau model hiện tại
        try:
            start_idx = fallback_models.index(current_model) + 1
        except ValueError:
            start_idx = 0  # model hiện tại không trong list → thử từ đầu

        # Tìm model tiếp theo chưa bị exhausted
        for model in fallback_models[start_idx:] + fallback_models[:start_idx]:
            if model not in key.exhausted_models and model != current_model:
                key.mark_model_exhausted(current_model)
                key.model = model
                self.save_to_file()
                return model

        # Hết tất cả models
        key.mark_model_exhausted(current_model)
        key.is_quota_exhausted = True
        self.save_to_file()
        return None

    def rotate_key_smart(self) -> Optional['AIAPIKey']:
        """
        Smart rotation: ưu tiên key chưa bị exhausted.
        Returns key mới hoặc None nếu tất cả đều exhausted.
        """
        with self.lock:
            if not self.keys:
                return None
            current_idx = next((i for i, k in enumerate(self.keys) if k.is_active), -1)
            # Thử lần lượt các key tiếp theo
            for offset in range(1, len(self.keys) + 1):
                next_idx = (current_idx + offset) % len(self.keys)
                next_key = self.keys[next_idx]
                if not next_key.is_quota_exhausted:
                    for k in self.keys: k.is_active = False
                    next_key.is_active = True
                    self.save_to_file()
                    return next_key
            return None  # tất cả keys đã exhausted

    def reset_all_quota_status(self) -> None:
        """Reset trạng thái quota tất cả keys (gọi mỗi ngày mới)"""
        with self.lock:
            for key in self.keys:
                key.reset_quota_status()
            self.save_to_file()

    def rotate_key(self) -> Optional[AIAPIKey]:
        """Rotate to next key (for failover)"""
        with self.lock:
            if not self.keys:
                return None

            current_idx = next(
                (i for i, k in enumerate(self.keys) if k.is_active), -1
            )
            next_idx = (current_idx + 1) % len(self.keys)

            for key in self.keys:
                key.is_active = False
            self.keys[next_idx].is_active = True
            self.save_to_file()
            return self.keys[next_idx]

    # ───────────────────────────────────────
    # Persistence (secure atomic write)
    # ───────────────────────────────────────

    def save_to_file(self):
        """Save keys to JSON file with secure permissions (600)"""
        try:
            data = {
                "version": "1.4.5",
                "keys": [
                    {
                        "id": k.id,
                        "name": k.name,
                        "api_key": k.api_key,
                        "provider": k.provider,
                        "model": k.model,
                        "is_active": k.is_active,
                        "created_at": k.created_at,
                        "last_used": k.last_used,
                        "usage_count": k.usage_count,
                        "exhausted_models": k.exhausted_models or [],
                        "is_quota_exhausted": k.is_quota_exhausted,
                    }
                    for k in self.keys
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
            print(f"⚠️  Failed to save AI keys: {e}")

    def load_from_file(self):
        """Load keys from JSON file"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, "r") as f:
                    data = json.load(f)

                self.keys = [
                    AIAPIKey(
                        id=k["id"],
                        name=k["name"],
                        api_key=k["api_key"],
                        provider=k.get("provider", "gemini"),
                        model=k.get("model", "gemini-1.5-flash-latest"),
                        is_active=k["is_active"],
                        created_at=k["created_at"],
                        last_used=k.get("last_used"),
                        usage_count=k.get("usage_count", 0),
                        exhausted_models=k.get("exhausted_models", []),
                        is_quota_exhausted=k.get("is_quota_exhausted", False),
                    )
                    for k in data.get("keys", [])
                ]
        except Exception as e:
            print(f"⚠️  Failed to load AI keys: {e}")
            self.keys = []
