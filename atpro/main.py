#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════╗
║               🎯 AT PRO v1.4.6 — Blue Edition 🎯             ║
║        CÔNG CỤ NUÔI TIKTOK TỰ ĐỘNG - MODULAR EDITION         ║
╚═══════════════════════════════════════════════════════════════╝

Cách dùng:
  Lần đầu: bash setup.sh
  Mọi lần sau: python3 main.py
"""

import os
import sys
import time
import traceback


def main():
    try:
        from app.farm_app import show_banner, TikTokFarmApp
        show_banner()
        app = TikTokFarmApp()
        app.run()

    except KeyboardInterrupt:
        print("\n⚠️  Thoát (Ctrl+C)")

    except ImportError as e:
        print(f"\n❌ Thiếu thư viện: {e}")
        print("💡 Chạy setup trước: bash setup.sh")
        traceback.print_exc()
        sys.exit(1)

    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        traceback.print_exc()
        sys.exit(1)

    finally:
        try:
            from ui.logger import smart_logger
            smart_logger.shutdown_async_worker()
        except Exception:
            pass
        try:
            time.sleep(0.3)
        except Exception:
            pass


if __name__ == "__main__":
    main()
