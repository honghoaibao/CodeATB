# 🗂️ AT Tool v1.4.5 — Kế Hoạch Tách Module

## Cấu Trúc Mới

```
attv1_4_5/
├── __init__.py              ← Package root (VERSION = "1.4.5")
├── main.py                  ← Entry point (imports tất cả module)
│
├── models/                  ✅ DONE
│   ├── __init__.py
│   ├── ai_models.py         ← AIModels catalog (Gemini/OpenAI/Anthropic)
│   ├── ai_keys.py           ← AIAPIKey dataclass + AIAPIKeyManager
│   └── proxy.py             ← ProxyEntry dataclass + ProxyManager
│
├── ai/                      ✅ DONE
│   ├── __init__.py
│   └── popup_handler.py     ← AIPopupHandler + TwoLayerPopupHandler
│
├── core/                    ✅ DONE (partial)
│   ├── __init__.py
│   ├── human_behavior.py    ← HumanBehavior (random timing, swipe curves, fatigue)
│   └── detection.py         ← ScreenState + DetectionResult + DivineEye
│
├── ui/                      ✅ DONE (partial)
│   ├── __init__.py
│   ├── constants.py         ← AppConstants + ColorScheme
│   └── logger.py            ← SmartLogger + global smart_logger
│
└── utils/                   ⬜ TODO
    └── __init__.py
```

---

## Roadmap: Các Bước Tiếp Theo

### v1.4.6 — Config & Stats
| File | Class từ v1.4.4 | Dòng gốc |
|------|-----------------|----------|
| `core/config.py` | `ProxyType`, `ProxyConfig`, `Config`, `ConfigManager` | ~6031 |
| `core/stats.py` | `FarmSession`, `AccountDayStats`, `DayStats`, `StatsManager`, `AdvancedStatistics` | ~4290 |
| `utils/timing.py` | `TimingCalculator` | ~4232 |

### v1.4.7 — UI Components
| File | Class từ v1.4.4 | Dòng gốc |
|------|-----------------|----------|
| `ui/ultimate_ui.py` | `UltimateUI` | ~2695 |
| `ui/notifications.py` | `NotificationManager` | ~3002 |
| `ui/stats_ui.py` | `StatsUI`, `DashboardComponents` | ~9627 |

### v1.4.8 — Core Automation
| File | Class từ v1.4.4 | Dòng gốc |
|------|-----------------|----------|
| `utils/xml_parser.py` | `XMLParser`, `XMLParserContinued` | ~6421 |
| `utils/ui_helper.py` | `UIHelper` | ~7324 |
| `utils/progress_tracker.py` | `ProgressTracker` | ~8483 |
| `utils/action_handler.py` | `SmartActionHandler` | ~8564 |
| `core/enhanced_detection.py` | `EnhancedDetection` | ~8842 |

### v1.4.9 — App Layer
| File | Class từ v1.4.4 | Dòng gốc |
|------|-----------------|----------|
| `core/device_manager.py` | `TikTokPackage`, `DeviceManager`, `DeviceHardwareInfo` | ~5968 |
| `core/video_interaction.py` | `SmartVideoInteraction` | ~4801 |
| `core/priority_account.py` | `PriorityAccountManager`, `FollowVerifier` | ~5208 |
| `core/automation.py` | `TikTokAutomation` | ~9116 |
| `app/farm_app.py` | `TikTokFarmApp` | ~10442 |

---

## Nguyên Tắc Khi Tách Module

1. **Không breaking change** — mọi hàm/class giữ nguyên interface
2. **Import rõ ràng** — `from models import AIModels` thay vì `from attv1_4_4 import *`
3. **Global singletons** — `smart_logger`, `divine_eye` được khởi tạo 1 lần trong module
   và import ở nơi cần dùng
4. **Circular imports** — tránh bằng cách: `models/` không import từ `core/` hay `ui/`
5. **Test từng module độc lập** trước khi tích hợp vào `main.py`

---

## Dependency Graph

```
models/     ← không phụ thuộc gì
  ↑
ai/         ← phụ thuộc models/
  ↑
ui/         ← phụ thuộc ui/constants (internal)
  ↑
core/       ← phụ thuộc models/, ui/
  ↑
utils/      ← phụ thuộc core/, models/
  ↑
main.py     ← import tất cả
```
