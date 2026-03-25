"""
╔══════════════════════════════════════════════════════╗
║           ai/popup_handler.py - v1.4.5               ║
║   AI-Powered Popup Detection & 2-Layer Fallback      ║
╚══════════════════════════════════════════════════════╝

Update: Sử dụng google-genai SDK mới (google.genai)
  pip install google-genai pillow

2-Layer System:
  Layer 1 (Priority): Gemini Vision (google.genai) / OpenAI / Anthropic
  Layer 2 (Fallback):  Traditional XML/pattern detection

Migration notes (google-generativeai → google-genai):
  OLD: import google.generativeai as genai
       genai.configure(api_key=key)
       model = genai.GenerativeModel(name)
       response = model.generate_content([prompt, img])

  NEW: from google import genai
       client = genai.Client(api_key=key)
       response = client.models.generate_content(
           model=name, contents=[prompt, img]
       )
"""

import re
import json
import threading
from typing import Dict, List, Optional, Tuple

from models.ai_models import AIModels
from models.ai_keys import AIAPIKeyManager

# ── google-genai (NEW SDK - preferred) ───────────────
try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    try:
        from PIL import Image as PILImage
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False
    GOOGLE_GENAI_AVAILABLE = True
except ImportError:
    GOOGLE_GENAI_AVAILABLE = False
    PIL_AVAILABLE = False

# ── google-generativeai (OLD SDK - fallback) ─────────
GEMINI_LEGACY_AVAILABLE = False
if not GOOGLE_GENAI_AVAILABLE:
    try:
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
        import google.generativeai as genai_legacy
        try:
            from PIL import Image as PILImage
            PIL_AVAILABLE = True
        except ImportError:
            pass
        GEMINI_LEGACY_AVAILABLE = True
    except ImportError:
        pass

# ── OpenAI ───────────────────────────────────────────
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ── Anthropic ────────────────────────────────────────
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# ── NumPy ────────────────────────────────────────────
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# ── SDK detection summary ────────────────────────────
GEMINI_AVAILABLE = GOOGLE_GENAI_AVAILABLE or GEMINI_LEGACY_AVAILABLE
_SDK_NAME = (
    "google-genai (new)" if GOOGLE_GENAI_AVAILABLE
    else "google-generativeai (legacy)" if GEMINI_LEGACY_AVAILABLE
    else "unavailable"
)


# ═══════════════════════════════════════════════════════
# GEMINI CLIENT WRAPPER
# ═══════════════════════════════════════════════════════

class _GeminiClient:
    """
    Thin wrapper ẩn sự khác biệt giữa 2 SDK.

    Cung cấp interface thống nhất:
      client = _GeminiClient(api_key, model_name)
      text   = client.generate(prompt, image)
    """

    def __init__(self, api_key: str, model_name: str):
        self.api_key    = api_key
        self.model_name = model_name
        self._client    = None
        self._legacy_model = None

        if GOOGLE_GENAI_AVAILABLE:
            self._client = google_genai.Client(api_key=api_key)
        elif GEMINI_LEGACY_AVAILABLE:
            genai_legacy.configure(api_key=api_key)
            self._legacy_model = genai_legacy.GenerativeModel(model_name)

    def generate(self, prompt: str, image=None, timeout: int = 30) -> Optional[str]:
        """
        Gọi Gemini và trả về text response.

        Args:
            prompt:  Text prompt
            image:   PIL Image hoặc None
            timeout: Seconds (default 30)

        Returns:
            Response text hoặc None nếu lỗi / timeout
        """
        result: Dict = {}

        def _call():
            try:
                if GOOGLE_GENAI_AVAILABLE and self._client:
                    # ── NEW SDK ──────────────────────────────────────────
                    contents: List = [prompt]
                    if image is not None:
                        # PIL Image được accept trực tiếp bởi new SDK
                        contents.append(image)

                    response = self._client.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                    )
                    result["text"] = response.text.strip()

                elif GEMINI_LEGACY_AVAILABLE and self._legacy_model:
                    # ── LEGACY SDK ───────────────────────────────────────
                    contents = [prompt]
                    if image is not None:
                        contents.append(image)
                    response = self._legacy_model.generate_content(contents)
                    result["text"] = response.text.strip()

            except Exception as exc:
                result["error"] = exc

        t = threading.Thread(target=_call, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            return None  # Timeout

        if "error" in result:
            raise result["error"]

        return result.get("text")

    @staticmethod
    def list_models(api_key: str) -> List[str]:
        """Liệt kê models hỗ trợ vision từ API key"""
        names: List[str] = []
        if GOOGLE_GENAI_AVAILABLE:
            try:
                client = google_genai.Client(api_key=api_key)
                for m in client.models.list():
                    # Lọc models hỗ trợ generateContent và vision
                    if hasattr(m, "name"):
                        names.append(m.name.replace("models/", ""))
            except Exception:
                pass
        elif GEMINI_LEGACY_AVAILABLE:
            try:
                genai_legacy.configure(api_key=api_key)
                for m in genai_legacy.list_models():
                    if "generateContent" in getattr(m, "supported_generation_methods", []):
                        names.append(m.name.replace("models/", ""))
            except Exception:
                pass
        return names

    @staticmethod
    def get_available_models(api_key: str) -> list:
        """
        Lấy danh sách models khả dụng từ API key (gọi API thật).
        Returns list of (model_id, display_name, supports_vision) tuples.
        """
        from models.ai_models import AIModels

        raw_names = _GeminiClient.list_models(api_key)
        all_info  = AIModels.get_all_models()
        preferred_order = getattr(AIModels, "PREFERRED_ORDER", [])

        results = []
        seen    = set()

        # 1. Sắp xếp models API trả về theo thứ tự ưu tiên
        for preferred in preferred_order:
            clean = preferred.replace("models/", "")
            if clean in [r.replace("models/", "") for r in raw_names] and clean not in seen:
                info = all_info.get(clean, {})
                results.append({
                    "id":          clean,
                    "name":        info.get("name", clean),
                    "vision":      info.get("vision", True),
                    "desc":        info.get("description", ""),
                    "recommended": info.get("recommended", False),
                })
                seen.add(clean)

        # 2. Thêm models API trả về mà chưa có trong preferred list
        for mid in raw_names:
            clean = mid.replace("models/", "")
            if clean not in seen:
                info = all_info.get(clean, {})
                results.append({
                    "id":          clean,
                    "name":        info.get("name", clean),
                    "vision":      info.get("vision", True),
                    "desc":        info.get("description", ""),
                    "recommended": False,
                })
                seen.add(clean)

        # 3. Nếu API không trả về gì, fallback về danh sách tĩnh
        if not results:
            for mid in preferred_order:
                info = all_info.get(mid, {})
                results.append({
                    "id":          mid,
                    "name":        info.get("name", mid),
                    "vision":      info.get("vision", True),
                    "desc":        info.get("description", "Offline/fallback"),
                    "recommended": info.get("recommended", False),
                })

        return results

    @staticmethod
    def test_model(api_key: str, model_name: str) -> bool:
        """Kiểm tra model có hoạt động không (text-only test)"""
        try:
            if GOOGLE_GENAI_AVAILABLE:
                client = google_genai.Client(api_key=api_key)
                client.models.generate_content(
                    model=model_name,
                    contents=["Hi"],
                )
                return True
            elif GEMINI_LEGACY_AVAILABLE:
                genai_legacy.configure(api_key=api_key)
                m = genai_legacy.GenerativeModel(model_name)
                m.generate_content("Hi")
                return True
        except Exception:
            pass
        return False


# ═══════════════════════════════════════════════════════
# AI POPUP HANDLER
# ═══════════════════════════════════════════════════════

class AIPopupHandler:
    """
    AI-Powered Popup Detection v1.4.5 (google-genai SDK).

    Nhận screenshot → gọi AI → trả về action để xử lý popup.
    Timeout 30s để tránh block farming.
    """

    # Danh sách model ưu tiên (mới nhất → cũ nhất)
    # Thứ tự ưu tiên — Gemini 2.5 Flash đứng đầu (nhanh + mạnh nhất)
    PREFERRED_MODELS = [
        "gemini-2.5-flash-preview-04-17",   # ⭐ Khuyên dùng: nhanh + mạnh
        "gemini-2.5-pro-preview-05-06",     # Mạnh nhất 2.5
        "gemini-2.0-flash",                 # Ổn định 2.0
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash-latest",          # Legacy
        "gemini-1.5-flash-002",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-pro-vision",
    ]

    POPUP_PROMPT = """You are a TikTok app automation assistant. Analyze this screenshot carefully.

Your task:
1. Detect if there's ANY popup, dialog, overlay, or modal window
2. Identify the type of popup (age verification, login prompt, 1234 code entry, account switch, error message, etc.)
3. Describe what the popup is asking or showing
4. Suggest the best action to dismiss or handle it
5. If there's a button to click, identify its text and approximate location

Respond ONLY in valid JSON format (no markdown, no code blocks):
{
    "has_popup": true or false,
    "popup_type": "age_verification" or "login_required" or "1234_code" or "account_switch" or "error" or "other",
    "confidence": 0.0 to 1.0,
    "description": "brief description of what the popup shows",
    "suggested_action": "enter_1234" or "click_back" or "click_continue" or "press_back_button" or "swipe_up" or "none",
    "button_text": "text on the button to click, if any",
    "button_location": {"x_percent": 0.5, "y_percent": 0.8}
}

If no popup detected, return: {"has_popup": false, "confidence": 1.0}"""

    def __init__(self, api_key_manager: AIAPIKeyManager):
        self.api_manager    = api_key_manager
        self.gemini_client: Optional[_GeminiClient] = None
        self.last_api_key   = None
        self.is_initialized = False
        self._active_model  = None

        if not GEMINI_AVAILABLE:
            print(
                "⚠️  Gemini AI không khả dụng.\n"
                "     Cài đặt: pip install google-genai pillow\n"
                f"     SDK status: {_SDK_NAME}"
            )
            return

        print(f"✅ Gemini SDK: {_SDK_NAME}")
        self._initialize_model()

    # ─────────────────────────────────────────
    # Initialization
    # ─────────────────────────────────────────

    def _detect_best_model(self, api_key: str) -> Optional[str]:
        """Tìm model tốt nhất cho API key này"""
        # Thử từ danh sách ưu tiên
        for model_name in self.PREFERRED_MODELS:
            if _GeminiClient.test_model(api_key, model_name):
                return model_name

        # Fallback: liệt kê từ API
        available = _GeminiClient.list_models(api_key)
        for preferred in self.PREFERRED_MODELS:
            if preferred in available:
                return preferred

        # Trả về model đầu tiên có "flash" hoặc "pro"
        for m in available:
            if "flash" in m.lower() or "pro" in m.lower():
                return m

        return available[0] if available else None

    def _initialize_model(self) -> bool:
        """Khởi tạo Gemini client với active API key"""
        try:
            api_key = self.api_manager.get_active_key()
            if not api_key:
                print("⚠️  Không có active API key")
                return False

            if api_key.api_key == self.last_api_key and self.is_initialized:
                return True  # Đã init rồi

            # Tìm model tốt nhất
            model_name = getattr(api_key, "model", None) or self._detect_best_model(api_key.api_key)

            if not model_name:
                print("⚠️  Không tìm được Gemini model phù hợp")
                self.is_initialized = False
                return False

            self.gemini_client = _GeminiClient(api_key.api_key, model_name)
            self._active_model = model_name
            self.last_api_key  = api_key.api_key
            self.is_initialized = True
            print(f"✅ AI model: {model_name}  |  SDK: {_SDK_NAME}")

            api_key.mark_used()
            self.api_manager.save_to_file()
            return True

        except Exception as e:
            print(f"⚠️  AI init failed: {e}")
            self.is_initialized = False
            return False

    # ─────────────────────────────────────────
    # JSON helpers
    # ─────────────────────────────────────────

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict]:
        """Robust JSON extraction với multiple fallback strategies"""
        # Strategy 1: direct
        try:
            return json.loads(text.strip())
        except Exception:
            pass
        # Strategy 2: strip markdown fences
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        # Strategy 3: regex first JSON object
        for m in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL):
            try:
                return json.loads(m.group(0))
            except Exception:
                continue
        # Strategy 4: fix single quotes & trailing commas
        try:
            fixed = re.sub(r",(\s*[}\]])", r"\1", text.replace("'", '"'))
            return json.loads(fixed)
        except Exception:
            pass
        return None

    @staticmethod
    def _detect_available_model(api_key: str, provider: str = "gemini") -> Optional[str]:
        """
        Auto-detect available model for this API key
        Tries multiple models in order of preference
        
        Args:
            api_key: API key to test
            provider: "gemini", "openai", or "anthropic"
        
        Returns:
            Model name if found, None if none available
        """
        if provider == "gemini":
            # Gemini models to try (latest to oldest, including future 3.x)
            models_to_try = [
                # Future Gemini 3.x (try these first)
                'gemini-3.1-flash',
                'gemini-3.0-flash',
                'gemini-3.0-pro',
                
                # Gemini 2.x
                'gemini-2.0-flash-exp',
                
                # Gemini 1.5 (stable)
                'gemini-1.5-flash-latest',
                'gemini-1.5-flash-002',
                'gemini-1.5-flash',
                'gemini-1.5-pro-latest',
                'gemini-1.5-pro',
                
                # Legacy
                'gemini-pro-vision',
                'gemini-pro',
                'gemini-1.0-pro-latest',
                'gemini-1.0-pro'
            ]
            
            try:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=api_key)
                
                for model_name in models_to_try:
                    try:
                        model = genai_legacy.GenerativeModel(model_name)
                        response = model.generate_content("Test")
                        # If no exception, model works!
                        return model_name
                    except Exception:
                        continue
            except Exception:
                pass
        
        elif provider == "openai":
            # OpenAI models to try
            models_to_try = [
                'gpt-4-vision-preview',  # Best for vision
                'gpt-4-turbo',
                'gpt-4',
                'gpt-3.5-turbo'
            ]
            
            try:
                client = openai.OpenAI(api_key=api_key)
                
                for model_name in models_to_try:
                    try:
                        # Simple test
                        response = client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": "Test"}],
                            max_tokens=5
                        )
                        return model_name
                    except Exception:
                        continue
            except Exception:
                pass
        
        elif provider == "anthropic":
            # Anthropic Claude models to try
            models_to_try = [
                'claude-3-5-sonnet-20241022',  # Latest 3.5
                'claude-3-opus-20240229',
                'claude-3-sonnet-20240229',
                'claude-3-haiku-20240307'
            ]
            
            try:
                client = anthropic.Anthropic(api_key=api_key)
                
                for model_name in models_to_try:
                    try:
                        response = client.messages.create(
                            model=model_name,
                            max_tokens=5,
                            messages=[{"role": "user", "content": "Test"}]
                        )
                        return model_name
                    except Exception:
                        continue
            except Exception:
                pass
        
        return None
    
    @staticmethod
    def _validate(data: Dict) -> bool:
        if not isinstance(data, dict):
            return False
        if "has_popup" not in data:
            return False
        if not isinstance(data["has_popup"], bool):
            return False
        if "confidence" in data:
            try:
                float(data["confidence"])
            except Exception:
                return False
        return True

    @staticmethod
    def _sanitize(data: Dict) -> Dict:
        return {
            "has_popup":        bool(data.get("has_popup", False)),
            "popup_type":       str(data.get("popup_type", "unknown")),
            "confidence":       max(0.0, min(1.0, float(data.get("confidence", 0.0)))),
            "description":      str(data.get("description", "")),
            "suggested_action": str(data.get("suggested_action", "none")),
            "button_text":      str(data.get("button_text", "")),
            "button_location":  data.get("button_location", {"x_percent": 0.5, "y_percent": 0.8}),
        }

    # ─────────────────────────────────────────
    # Core detection
    # ─────────────────────────────────────────

    def detect_popup(self, screenshot) -> Dict:
        """
        v1.4.4 FIX 3: Enhanced popup detection with robust error handling
        
        Detect popup using AI Vision
        
        Args:
            screenshot: PIL Image or device screenshot
            
        Returns:
            {
                'has_popup': bool,
                'popup_type': str,
                'confidence': float,
                'description': str,
                'suggested_action': str,
                'button_text': str,
                'button_location': {'x_percent': float, 'y_percent': float}
            }
        """
        if not self.is_initialized:
            if not self._initialize_model():
                return {'has_popup': False, 'error': 'AI not initialized'}
        
        img = None
        try:
            # Convert screenshot to PIL Image if needed
            if hasattr(screenshot, 'convert'):
                img = screenshot
            else:
                img = Image.fromarray(np.array(screenshot))
            
            # FIX 3: Check if model supports vision
            api_key = self.api_manager.get_active_key()
            if api_key:
                model_info = AIModels.get_all_models().get(api_key.model, {})
                if not model_info.get('vision', False):
                    return {
                        'has_popup': False,
                        'error': f'Model {api_key.model} does not support vision',
                        'confidence': 0.0
                    }
            
            # Prepare prompt
            prompt = """You are a TikTok app automation assistant. Analyze this screenshot carefully.

Your task:
1. Detect if there's ANY popup, dialog, overlay, or modal window
2. Identify the type of popup (age verification, login prompt, 1234 code entry, account switch, error message, etc.)
3. Describe what the popup is asking or showing
4. Suggest the best action to dismiss or handle it
5. If there's a button to click, identify its text and approximate location

Respond ONLY in valid JSON format (no markdown, no code blocks):
{
    "has_popup": true or false,
    "popup_type": "age_verification" or "login_required" or "1234_code" or "account_switch" or "error" or "other",
    "confidence": 0.0 to 1.0,
    "description": "brief description of what the popup shows",
    "suggested_action": "enter_1234" or "click_back" or "click_continue" or "press_back_button" or "swipe_up" or "none",
    "button_text": "text on the button to click, if any",
    "button_location": {"x_percent": 0.5, "y_percent": 0.8}
}

If no popup detected, return: {"has_popup": false, "confidence": 1.0}"""
            
            # FIX 3: Call AI with timeout
            import threading
            result_container = {}
            error_container = {}
            
            def call_ai():
                try:
                    response = self.model.generate_content([prompt, img])
                    result_container['response'] = response.text.strip()
                except Exception as e:
                    error_container['error'] = e
            
            thread = threading.Thread(target=call_ai)
            thread.daemon = True
            thread.start()
            thread.join(timeout=30)  # 30 second timeout
            
            if thread.is_alive():
                return {'has_popup': False, 'error': 'AI request timeout (30s)'}
            
            if 'error' in error_container:
                raise error_container['error']
            
            if 'response' not in result_container:
                return {'has_popup': False, 'error': 'No response from AI'}
            
            response_text = result_container['response']
            
            # FIX 3: Robust JSON extraction
            parsed_data = self._extract_json_from_text(response_text)
            
            if parsed_data is None:
                # Log the problematic response
                print(f"⚠️  Failed to parse AI response. Raw text (first 200 chars): {response_text[:200]}")
                return {
                    'has_popup': False,
                    'error': 'Failed to parse JSON from AI response',
                    'raw_response': response_text[:500]  # Truncated for logging
                }
            
            # FIX 3: Validate response structure
            if not self._validate_popup_response(parsed_data):
                print(f"⚠️  Invalid AI response structure: {parsed_data}")
                return {
                    'has_popup': False,
                    'error': 'Invalid response structure',
                    'raw_data': str(parsed_data)[:500]
                }
            
            # FIX 3: Sanitize and return
            result = self._sanitize_popup_response(parsed_data)
            
            return result
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # FIX 3: Enhanced error logging with context
            api_key = self.api_manager.get_active_key()
            provider = api_key.provider if api_key else "unknown"
            model = api_key.model if api_key else "unknown"
            
            print(f"⚠️  AI Error [{provider}/{model}] {error_type}: {error_msg[:200]}")
            
            # FIX 3: Specific error handling with exponential backoff
            retry_count = getattr(self, '_retry_count', 0)
            max_retries = 3
            
            # ── Phân loại lỗi ──────────────────────────────────
            is_quota_error = any(k in error_msg.lower() for k in
                ['quota', 'rate', '429', 'resource_exhausted',
                 'too many requests', 'limit exceeded', 'daily limit'])
            is_auth_error  = any(k in error_msg.lower() for k in
                ['invalid', 'unauthorized', '401', '403', 'permission', 'api_key'])
            is_timeout     = 'timeout' in error_msg.lower() or error_type in ['TimeoutError', 'Timeout']
            is_model_error = any(k in error_msg.lower() for k in
                ['model', 'not found', 'not supported', '404', 'deprecated'])
            
            # ── QUOTA / RATE LIMIT → Chuyển model trước, rồi chuyển key ──
            if is_quota_error and retry_count < max_retries:
                print(f"🔄 Quota/rate limit (attempt {retry_count + 1}/{max_retries})")
                print(f"   Key: {api_key.name if api_key else 'N/A'} | Model: {model}")
                
                # Bước 1: Thử chuyển model khác trong cùng key
                new_model = self.api_manager.rotate_model_for_key(api_key)
                if new_model:
                    print(f"✨ Chuyển model: {model} → {new_model}")
                    try:
                        from ui.logger import smart_logger
                        smart_logger.log(f"🔄 Quota hết, chuyển model: {model} → {new_model}", force=True)
                    except Exception:
                        pass
                    self._initialize_model(force_model=new_model)
                    import time; time.sleep(1)
                    self._retry_count = retry_count + 1
                    result = self.detect_popup(screenshot)
                    self._retry_count = 0
                    return result
                
                # Bước 2: Hết models của key này → chuyển key
                print(f"⚠️  Hết models của '{api_key.name}', chuyển key...")
                rotated_key = self.api_manager.rotate_key_smart()
                if rotated_key:
                    print(f"✅ Chuyển key: {rotated_key.name} | Model: {rotated_key.model}")
                    try:
                        from ui.logger import smart_logger
                        smart_logger.log(
                            f"🔑 Hết quota, chuyển key: {rotated_key.name} [{rotated_key.model}]",
                            force=True)
                    except Exception:
                        pass
                    self._initialize_model()
                    import time
                    backoff = 2 ** retry_count
                    print(f"⏳ Chờ {backoff}s...")
                    time.sleep(backoff)
                    self._retry_count = retry_count + 1
                    result = self.detect_popup(screenshot)
                    self._retry_count = 0
                    return result
                else:
                    print("❌ Tất cả API keys và models đã hết quota!")
                    try:
                        from ui.logger import smart_logger
                        smart_logger.log("❌ Tất cả AI keys hết quota — AI tạm dừng", force=True)
                    except Exception:
                        pass
            
            # ── MODEL NOT FOUND → thử model khác ──
            elif is_model_error and retry_count < max_retries:
                print(f"🔄 Model '{model}' không khả dụng, thử model khác...")
                new_model = self.api_manager.rotate_model_for_key(api_key)
                if new_model:
                    print(f"✨ Chuyển model: {model} → {new_model}")
                    self._initialize_model(force_model=new_model)
                    self._retry_count = retry_count + 1
                    result = self.detect_popup(screenshot)
                    self._retry_count = 0
                    return result

            # ── TIMEOUT → retry với backoff ──
            elif is_timeout and retry_count < max_retries:
                import time
                backoff = 2 ** retry_count
                print(f"⏳ Timeout, retry trong {backoff}s (lần {retry_count + 1}/{max_retries})")
                time.sleep(backoff)
                self._retry_count = retry_count + 1
                result = self.detect_popup(screenshot)
                self._retry_count = 0
                return result
            
            # ── AUTH ERROR → không retry ──
            elif is_auth_error:
                print(f"❌ Lỗi xác thực — API key không hợp lệ")
                if api_key:
                    print(f"⚠️  Xem lại key: {api_key.name}")
                    
            # Reset retry counter
            self._retry_count = 0
            
            # Return error with full context
            return {
                'has_popup': False,
                'error': error_msg,
                'error_type': error_type,
                'provider': provider,
                'model': model,
                'retry_count': retry_count
            }
        
        finally:
            # FIX 3: Clean up image to prevent memory leak
            if img is not None and img != screenshot:
                try:
                    img.close()
                    del img
                except:
                    pass
    
    def handle_popup_with_ai(self, device) -> Dict:
        """
        Chụp màn hình → detect → xử lý popup trên device.

        Returns:
            {"handled": bool, "method": str, "details": dict}
        """
        import time
        try:
            screenshot = device.screenshot()
            detection  = self.detect_popup(screenshot)

            if not detection.get("has_popup"):
                return {"handled": False, "method": "no_popup", "details": detection}

            confidence = detection.get("confidence", 0.0)
            if confidence < 0.5:
                return {"handled": False, "method": "low_confidence", "details": detection}

            action = detection.get("suggested_action", "none")

            if action == "enter_1234":
                return {"handled": False, "method": "defer_to_1234_handler", "details": detection}

            elif action in ("click_back", "press_back_button"):
                device.press("back")
                time.sleep(1)
                return {"handled": True, "method": "press_back", "details": detection}

            elif action in ("click_continue", "swipe_up"):
                loc = detection.get("button_location", {"x_percent": 0.5, "y_percent": 0.8})
                w, h = device.window_size()
                x = int(w * loc.get("x_percent", 0.5))
                y = int(h * loc.get("y_percent", 0.8))
                device.click(x, y)
                time.sleep(0.5)
                return {"handled": True, "method": f"click_{x}_{y}", "details": detection}

            else:
                return {"handled": False, "method": f"unknown_action:{action}", "details": detection}

        except Exception as e:
            return {"handled": False, "method": "exception", "details": {"error": str(e)}}

    def get_sdk_info(self) -> Dict:
        """Thông tin SDK đang sử dụng"""
        return {
            "sdk": _SDK_NAME,
            "google_genai_available": GOOGLE_GENAI_AVAILABLE,
            "legacy_available": GEMINI_LEGACY_AVAILABLE,
            "active_model": self._active_model,
            "initialized": self.is_initialized,
            "pil_available": PIL_AVAILABLE,
        }

    def _extract_json_from_text(text: str) -> Optional[Dict]:
        """
        v1.4.4 FIX 3: Robust JSON extraction with multiple fallback strategies
        
        Handles:
        - Markdown code blocks (```json ... ```)
        - Extra text before/after JSON
        - Malformed JSON
        - Missing quotes
        
        Returns:
            Parsed dict or None if cannot extract
        """
        import re
        
        # Strategy 1: Try direct parse
        try:
            return json.loads(text.strip())
        except:
            pass
        
        # Strategy 2: Remove markdown code blocks
        cleaned = text.strip()
        if cleaned.startswith('```'):
            # Remove opening ```json or ```
            cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned)
            # Remove closing ```
            cleaned = re.sub(r'\n?```\s*$', '', cleaned)
            try:
                return json.loads(cleaned)
            except:
                pass
        
        # Strategy 3: Find JSON block with regex
        # Look for { ... } pattern
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.finditer(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                potential_json = match.group(0)
                return json.loads(potential_json)
            except:
                continue
        
        # Strategy 4: Try to fix common issues
        # Replace single quotes with double quotes
        try:
            fixed = text.replace("'", '"')
            # Remove trailing commas
            fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
            return json.loads(fixed)
        except:
            pass
        
        return None

    def _validate_popup_response(data: Dict) -> bool:
        """
        v1.4.4 FIX 3: Validate AI response has required fields
        
        Required fields:
        - has_popup (bool)
        - confidence (float)
        
        Returns:
            True if valid, False otherwise
        """
        if not isinstance(data, dict):
            return False
        
        # Check required fields
        if 'has_popup' not in data:
            return False
        
        if not isinstance(data['has_popup'], bool):
            return False
        
        # Confidence optional but should be float if present
        if 'confidence' in data:
            try:
                float(data['confidence'])
            except:
                return False
        
        return True

    def _sanitize_popup_response(data: Dict) -> Dict:
        """
        v1.4.4 FIX 3: Sanitize and set defaults for popup response
        
        Ensures all expected fields exist with proper types
        """
        sanitized = {
            'has_popup': bool(data.get('has_popup', False)),
            'popup_type': str(data.get('popup_type', 'unknown')),
            'confidence': float(data.get('confidence', 0.0)),
            'description': str(data.get('description', '')),
            'suggested_action': str(data.get('suggested_action', 'none')),
            'button_text': str(data.get('button_text', '')),
            'button_location': data.get('button_location', {'x_percent': 0.5, 'y_percent': 0.8})
        }
        
        # Ensure confidence is between 0 and 1
        sanitized['confidence'] = max(0.0, min(1.0, sanitized['confidence']))
        
        return sanitized

    def analyze_screen(self, screenshot, query: str) -> str:
        """
        General purpose screen analysis
        
        Args:
            screenshot: PIL Image
            query: Question to ask about the screen
            
        Returns:
            AI response as string
        """
        if not self.is_initialized:
            if not self._initialize_model():
                return "AI not initialized"
        
        try:
            if hasattr(screenshot, 'convert'):
                img = screenshot
            else:
                img = Image.fromarray(np.array(screenshot))
            
            response = self.model.generate_content([query, img])
            return response.text
        except Exception as e:
            return f"Error: {e}"

    def find_button(self, screenshot, button_text: str) -> Optional[Tuple[int, int]]:
        """
        Use AI to find specific button
        
        Args:
            screenshot: PIL Image
            button_text: Text on the button to find
            
        Returns:
            (x, y) coordinates or None
        """
        if not self.is_initialized:
            if not self._initialize_model():
                return None
        
        try:
            if hasattr(screenshot, 'convert'):
                img = screenshot
            else:
                img = Image.fromarray(np.array(screenshot))
            
            prompt = f"""Find the button with text "{button_text}" in this screenshot.
Respond in JSON format:
{{
    "found": true or false,
    "x_percent": 0.0 to 1.0,
    "y_percent": 0.0 to 1.0,
    "confidence": 0.0 to 1.0
}}"""
            
            response = self.model.generate_content([prompt, img])
            response_text = response.text.strip()
            
            # Remove markdown
            if response_text.startswith('```'):
                response_text = response_text.split('\n', 1)[1].rsplit('\n', 1)[0]
            
            result = json.loads(response_text)
            
            if result.get('found') and result.get('confidence', 0) > 0.7:
                # Get screen size (assume full HD for now, will be adjusted by caller)
                x_percent = result.get('x_percent', 0.5)
                y_percent = result.get('y_percent', 0.5)
                return (x_percent, y_percent)
            
            return None
        except Exception as e:
            print(f"⚠️  Button finding error: {e}")
            return None

    def get_quota_status(self) -> dict:
        """Lấy trạng thái quota hiện tại của tất cả keys"""
        keys = self.api_manager.get_all_keys()
        active = self.api_manager.get_active_key()
        return {
            "total_keys":     len(keys),
            "active_key":     active.name if active else None,
            "active_model":   active.model if active else None,
            "exhausted_keys": [k.name for k in keys if getattr(k, "is_quota_exhausted", False)],
            "partial_keys":   [k.name for k in keys if getattr(k, "exhausted_models", []) and not getattr(k, "is_quota_exhausted", False)],
            "healthy_keys":   [k.name for k in keys if not getattr(k, "is_quota_exhausted", False)],
            "all_exhausted":  all(getattr(k, "is_quota_exhausted", False) for k in keys) if keys else True,
        }



# ═══════════════════════════════════════════════════════════════
# 🤖 v1.4.4 ADDITIONAL: HUMAN BEHAVIOR ENGINE
# ═══════════════════════════════════════════════════════════════

    

    

    

    

    


# ═══════════════════════════════════════════════════════
# TWO-LAYER POPUP HANDLER
# ═══════════════════════════════════════════════════════

class TwoLayerPopupHandler:
    """
    2-Layer Popup Detection System v1.4.5

    Layer 1 (Priority): AI Vision (Gemini google-genai / OpenAI / Anthropic)
    Layer 2 (Fallback):  Traditional XML/pattern-based detection
    """

    def __init__(self, ai_handler: Optional[AIPopupHandler], config):
        self.ai_handler    = ai_handler
        self.config        = config
        self.use_ai_priority = (
            getattr(config, "ai_popup_enabled", False) and ai_handler is not None
        )

        self.ai_success_count            = 0
        self.ai_fail_count               = 0
        self.traditional_success_count   = 0
        self.traditional_fail_count      = 0

    def detect_and_handle(self, device, traditional_handler_func) -> bool:
        """
        Detect and handle popup with 2-layer system
        
        Args:
            device: uiautomator2 device
            traditional_handler_func: Function for traditional popup handling
            
        Returns:
            True if popup handled, False otherwise
        """
        
        # LAYER 1: AI Detection (if enabled and available)
        if self.use_ai_priority and self.ai_handler:
            try:
                result = self.ai_handler.handle_popup_with_ai(device)
                
                if result.get('handled'):
                    self.ai_success_count += 1
                    details = result.get('details', {})
                    popup_type = details.get('popup_type', 'unknown')
                    confidence = details.get('confidence', 0)
                    
                    print(f"✅ AI Layer: Handled {popup_type} popup (confidence: {confidence:.0%})")
                    return True
                
                # AI detected popup but couldn't handle it
                if result.get('method') == 'defer_to_1234_handler':
                    # Special case: defer to specialized handler
                    print("🔄 AI detected 1234 popup, deferring to specialized handler")
                    self.ai_fail_count += 1
                    # Fall through to Layer 2
                
                elif result.get('details', {}).get('has_popup'):
                    # AI detected popup but failed to handle
                    print(f"⚠️  AI detected popup but couldn't handle: {result.get('method')}")
                    self.ai_fail_count += 1
                    # Fall through to Layer 2
                else:
                    # No popup detected by AI
                    return False
                    
            except Exception as e:
                print(f"⚠️  AI layer error: {e}")
                self.ai_fail_count += 1
                # Fall through to Layer 2
        
        # LAYER 2: Traditional Detection (fallback)
        try:
            result = traditional_handler_func(device)
            if result:
                self.traditional_success_count += 1
                print("✅ Traditional Layer: Popup handled")
            else:
                self.traditional_fail_count += 1
            return result
        except Exception as e:
            print(f"⚠️  Traditional layer error: {e}")
            self.traditional_fail_count += 1
            return False
    
    def get_stats(self) -> Dict:
        """Get handler statistics"""
        total_ai = self.ai_success_count + self.ai_fail_count
        total_traditional = self.traditional_success_count + self.traditional_fail_count
        
        return {
            'ai_success': self.ai_success_count,
            'ai_fail': self.ai_fail_count,
            'ai_success_rate': self.ai_success_count / total_ai if total_ai > 0 else 0,
            'traditional_success': self.traditional_success_count,
            'traditional_fail': self.traditional_fail_count,
            'traditional_success_rate': self.traditional_success_count / total_traditional if total_traditional > 0 else 0,
            'total_handled': self.ai_success_count + self.traditional_success_count,
        }


# ═══════════════════════════════════════════════════════════════
# 🔮 DIVINE EYE - AI VISION SYSTEM v1.0
# ═══════════════════════════════════════════════════════════════
"""
╔═══════════════════════════════════════════════════════════════╗
║                   🔮 DIVINE EYE v1.0 🔮                       ║
║              AI Vision System for TikTok Automation           ║
║                  Smart Detection & Memory Optimization        ║
╚═══════════════════════════════════════════════════════════════╝

✨ FEATURES:
- 🎯 Screen State Detection (Lost, Popup, Normal, Error)
- 🧠 Memory-Optimized Image Processing
- ⚡ Fast OCR for text detection
- 🔍 Element position tracking
- 📊 Confidence scoring
- 💾 Minimal RAM usage (< 100MB)
- 🚀 Real-time detection (< 100ms)

🎯 DETECTIONS:
1. Lost State: Không ở màn hình chính TikTok
2. Popup Detection: Bất kỳ popup nào
3. Account Switch: Popup chuyển account
4. Following Tab: Đang ở tab Following
5. Error Screens: Lỗi, crash, không kết nối
6. Video State: Đang xem video bình thường
"""

import cv2
import numpy as np
from PIL import Image
import io
import gc
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum
import time
import hashlib

# ═══════════════════════════════════════════════════════════════
# 📊 DETECTION RESULTS & ENUMS
# ═══════════════════════════════════════════════════════════════

class ScreenState(Enum):
    """Các trạng thái màn hình"""
    NORMAL_VIDEO = "normal_video"  # Đang xem video bình thường
    LOST = "lost"  # Lạc đường, không ở TikTok
    POPUP_ACCOUNT_SWITCH = "popup_account_switch"  # Popup chuyển account
    POPUP_GENERIC = "popup_generic"  # Popup khác
    FOLLOWING_TAB = "following_tab"  # Tab Following
    FOR_YOU_TAB = "for_you_tab"  # Tab For You
    PROFILE_PAGE = "profile_page"  # Trang profile
    ERROR_SCREEN = "error_screen"  # Màn hình lỗi
    NO_INTERNET = "no_internet"  # Không có mạng
    LOADING = "loading"  # Đang load
    UNKNOWN = "unknown"  # Không xác định

