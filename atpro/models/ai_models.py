"""
╔══════════════════════════════════════════════════════╗
║           models/ai_models.py - v1.4.5               ║
║   Catalog tất cả AI models từ mọi providers          ║
╚══════════════════════════════════════════════════════╝
"""

class AIModels:
    """Comprehensive catalog of AI models from all providers"""
    
    # ═══════════════════════════════════════════════════════════════
    # GEMINI MODELS (Google)
    # ═══════════════════════════════════════════════════════════════
    GEMINI = {
        # Gemini 3.x (Future-ready)
        "gemini-3.1-flash": {
            "name": "Gemini 3.1 Flash",
            "description": "Latest Gemini 3.1 Flash (when available)",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        "gemini-3.0-flash": {
            "name": "Gemini 3.0 Flash", 
            "description": "Latest Gemini 3.0 Flash (when available)",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        "gemini-3.0-pro": {
            "name": "Gemini 3.0 Pro",
            "description": "Gemini 3.0 Pro (when available)",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        
        # Gemini 2.x
        "gemini-2.0-flash-exp": {
            "name": "Gemini 2.0 Flash Exp",
            "description": "Experimental 2.0 (fastest)",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        
        # Gemini 1.5 (Current stable)
        "gemini-1.5-flash-latest": {
            "name": "Gemini 1.5 Flash Latest",
            "description": "Stable 1.5 Flash (recommended)",
            "provider": "gemini",
            "vision": True,
            "recommended": True
        },
        "gemini-1.5-flash-002": {
            "name": "Gemini 1.5 Flash 002",
            "description": "Specific 1.5 version",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        "gemini-1.5-flash": {
            "name": "Gemini 1.5 Flash",
            "description": "Standard 1.5 Flash",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        "gemini-1.5-pro-latest": {
            "name": "Gemini 1.5 Pro Latest",
            "description": "Latest 1.5 Pro (higher quality)",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        "gemini-1.5-pro": {
            "name": "Gemini 1.5 Pro",
            "description": "Standard 1.5 Pro",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        },
        
        # Legacy
        "gemini-pro": {
            "name": "Gemini Pro (Legacy)",
            "description": "Legacy Pro model",
            "provider": "gemini",
            "vision": False,
            "recommended": False
        },
        "gemini-pro-vision": {
            "name": "Gemini Pro Vision (Legacy)",
            "description": "Legacy Pro with vision",
            "provider": "gemini",
            "vision": True,
            "recommended": False
        }
    }
    
    # ═══════════════════════════════════════════════════════════════
    # OPENAI MODELS (ChatGPT)
    # ═══════════════════════════════════════════════════════════════
    OPENAI = {
        # GPT-4 with Vision
        "gpt-4-vision-preview": {
            "name": "GPT-4 Vision Preview",
            "description": "GPT-4 with image understanding",
            "provider": "openai",
            "vision": True,
            "recommended": True
        },
        "gpt-4-turbo": {
            "name": "GPT-4 Turbo",
            "description": "Fast GPT-4 (128K context)",
            "provider": "openai",
            "vision": False,
            "recommended": False
        },
        "gpt-4": {
            "name": "GPT-4",
            "description": "Standard GPT-4",
            "provider": "openai",
            "vision": False,
            "recommended": False
        },
        
        # GPT-3.5
        "gpt-3.5-turbo": {
            "name": "GPT-3.5 Turbo",
            "description": "Fast and cheap",
            "provider": "openai",
            "vision": False,
            "recommended": False
        }
    }
    
    # ═══════════════════════════════════════════════════════════════
    # ANTHROPIC MODELS (Claude)
    # ═══════════════════════════════════════════════════════════════
    ANTHROPIC = {
        # Claude 3.5
        "claude-3-5-sonnet-20241022": {
            "name": "Claude 3.5 Sonnet",
            "description": "Latest Claude 3.5 (best quality)",
            "provider": "anthropic",
            "vision": True,
            "recommended": True
        },
        
        # Claude 3
        "claude-3-opus-20240229": {
            "name": "Claude 3 Opus",
            "description": "Most powerful Claude",
            "provider": "anthropic",
            "vision": True,
            "recommended": False
        },
        "claude-3-sonnet-20240229": {
            "name": "Claude 3 Sonnet",
            "description": "Balanced performance",
            "provider": "anthropic",
            "vision": True,
            "recommended": False
        },
        "claude-3-haiku-20240307": {
            "name": "Claude 3 Haiku",
            "description": "Fastest Claude",
            "provider": "anthropic",
            "vision": True,
            "recommended": False
        }
    }
    
    # Thứ tự ưu tiên khi chọn model (mới nhất & ổn định → cũ)
    PREFERRED_ORDER = [
        "gemini-2.5-flash-preview-04-17",
        "gemini-2.5-pro-preview-05-06",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-1.0-pro",
        "gemini-pro-vision",
        "gemini-pro",
    ]

    @classmethod
    def get_all_models(cls):
        """Get all models from all providers"""
        all_models = {}
        all_models.update(cls.GEMINI)
        all_models.update(cls.OPENAI)
        all_models.update(cls.ANTHROPIC)
        return all_models
    
    @classmethod
    def get_provider_models(cls, provider: str):
        """Get models for specific provider"""
        if provider == "gemini":
            return cls.GEMINI
        elif provider == "openai":
            return cls.OPENAI
        elif provider == "anthropic":
            return cls.ANTHROPIC
        else:
            return {}
    
    @classmethod
    def get_recommended_models(cls):
        """Get recommended models from each provider"""
        recommended = {}
        all_models = cls.get_all_models()
        for model_id, info in all_models.items():
            if info.get("recommended"):
                recommended[model_id] = info
        return recommended
    
    @classmethod
    def get_vision_models(cls):
        """Get models that support vision"""
        vision_models = {}
        all_models = cls.get_all_models()
        for model_id, info in all_models.items():
            if info.get("vision"):
                vision_models[model_id] = info
        return vision_models
