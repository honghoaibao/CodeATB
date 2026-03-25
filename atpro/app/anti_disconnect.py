"""
app/anti_disconnect.py - v1.4.5
AntiDisconnectMonitor - Giữ kết nối ADB liên tục
"""
import subprocess
import threading
import time


class AntiDisconnectMonitor:
    """Chống lạc kết nối ADB - Lightweight background thread"""

    def __init__(self, device, check_interval: int = 30):
        self.device = device
        self.check_interval = check_interval
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._monitor, daemon=True)
        self.thread.start()
        print(f"🔄 Anti-disconnect started (every {self.check_interval}s)")

    def stop(self):
        self.running = False

    def _monitor(self):
        while self.running:
            try:
                _ = self.device.info
                time.sleep(self.check_interval)
            except Exception:
                try:
                    import subprocess
                    subprocess.run(['adb', 'reconnect'], capture_output=True, timeout=5)
                    time.sleep(2)
                except Exception:
                    pass

print()
print("=" * 70)
print("✅ AT TOOL v1.4.3 LOADED - NEW UI + FEATURES")
print("=" * 70)
print()
print("🎨 UI v1.4.3:")
print("   • Multi-channel notifications ✅")
print("   • Auto screenshot system ✅")
print("   • Smart filtering & rate limit ✅")
print()
print("🎨 UI/UX v1.4.3:")
print("   • Gradient panels & animations ✅")
print("   • Visual stats with bars ✅")
print()
print("=" * 70)
print()

