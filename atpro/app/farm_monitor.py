"""
app/farm_monitor.py - v1.4.6
FarmBackgroundMonitor
- Thread chống lạc + thread quét popup chạy SONG SONG với vòng nuôi
- Dùng threading.Event để dừng sạch
- Lock để tránh xung đột device
- pause() / resume() để nghỉ hoàn toàn giữa acc (không quét gì cả)
"""
import threading
import time


class FarmBackgroundMonitor:
    """
    Hai daemon thread chạy song song với farming loop:
      1. LostMonitor   — check_lost() mỗi lost_interval giây, tự recover
      2. PopupMonitor  — handle_popup() mỗi popup_interval giây

    Dùng threading.Lock chung để tránh 2 thread gọi device cùng lúc.
    Khi gọi pause() (vd: lúc nghỉ giữa acc), cả 2 thread ngủ hoàn toàn
    cho đến khi resume() được gọi.
    """

    def __init__(
        self,
        automation,
        device,
        config,
        lost_interval: float = 15.0,
        popup_interval: float = 8.0,
    ):
        self.automation     = automation
        self.device         = device
        self.config         = config
        self.lost_interval  = lost_interval
        self.popup_interval = popup_interval

        self._stop_event   = threading.Event()
        self._pause_event  = threading.Event()   # set = đang pause
        self._lock         = threading.Lock()

        self._lost_thread  = threading.Thread(
            target=self._lost_worker, daemon=True, name="LostMonitor"
        )
        self._popup_thread = threading.Thread(
            target=self._popup_worker, daemon=True, name="PopupMonitor"
        )

        # Stats để debug
        self.lost_detections  = 0
        self.popup_detections = 0

    # ── Public API ────────────────────────────────────────────────

    def start(self):
        """Bắt đầu cả 2 thread."""
        self._stop_event.clear()
        self._pause_event.clear()
        self._lost_thread.start()
        self._popup_thread.start()

    def stop(self):
        """Dừng cả 2 thread (non-blocking)."""
        self._pause_event.clear()   # bỏ pause trước khi stop
        self._stop_event.set()

    def pause(self):
        """
        Tạm dừng hoàn toàn cả 2 thread.
        Dùng khi vào trạng thái nghỉ — không quét lạc, không quét popup.
        """
        self._pause_event.set()

    def resume(self):
        """Tiếp tục sau khi nghỉ xong."""
        self._pause_event.clear()

    @property
    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def join(self, timeout: float = 3.0):
        """Chờ thread kết thúc (tùy chọn)."""
        self._lost_thread.join(timeout=timeout)
        self._popup_thread.join(timeout=timeout)

    # ── Internal helpers ─────────────────────────────────────────

    def _wait_or_pause(self, interval: float) -> bool:
        """
        Ngủ interval giây, nhưng:
        - Nếu stop được set trong lúc ngủ → trả về True (thoát worker)
        - Nếu pause được set → ngủ tiếp cho đến khi resume hoặc stop
        Trả về True nếu cần thoát worker.
        """
        # Ngủ theo interval, kiểm tra stop mỗi 0.5s
        deadline = time.monotonic() + interval
        while time.monotonic() < deadline:
            if self._stop_event.is_set():
                return True
            # Nếu đang pause, chờ resume hoặc stop
            while self._pause_event.is_set():
                if self._stop_event.is_set():
                    return True
                time.sleep(0.5)
            time.sleep(0.5)
        return self._stop_event.is_set()

    # ── Workers ───────────────────────────────────────────────────

    def _lost_worker(self):
        """Thread chống lạc — check mỗi lost_interval giây."""
        while True:
            if self._wait_or_pause(self.lost_interval):
                break
            # Kiểm tra lại pause trước khi làm việc
            if self._pause_event.is_set() or self._stop_event.is_set():
                continue
            try:
                with self._lock:
                    lost = self.automation.check_lost()
                if lost:
                    self.lost_detections += 1
                    try:
                        from ui.logger import smart_logger
                        smart_logger.log(
                            f"🛡️  [BG] Phát hiện lạc #{self.lost_detections}! Đang khôi phục...",
                            force=True
                        )
                    except Exception:
                        pass
                    with self._lock:
                        if not self.automation.recover_to_feed():
                            try:
                                self.automation.open_tiktok()
                                time.sleep(3)
                            except Exception:
                                pass
            except Exception:
                pass

    def _popup_worker(self):
        """Thread quét popup — handle mỗi popup_interval giây."""
        # Offset nhỏ để 2 thread không chạy cùng lúc ngay từ đầu
        if self._wait_or_pause(3.0):
            return
        while True:
            if self._wait_or_pause(self.popup_interval):
                break
            if self._pause_event.is_set() or self._stop_event.is_set():
                continue
            try:
                with self._lock:
                    handled = self.automation.handle_comprehensive_popup()
                if handled:
                    self.popup_detections += 1
                    try:
                        from ui.logger import smart_logger
                        smart_logger.log(
                            f"🔔 [BG] Đã xử lý popup #{self.popup_detections}",
                            force=True
                        )
                    except Exception:
                        pass
            except Exception:
                pass
