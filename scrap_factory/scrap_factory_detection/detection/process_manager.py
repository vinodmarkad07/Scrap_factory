"""
ProcessManager
==============
Manages the detection thread lifecycle.
Each call to start() spawns a daemon thread running the belt+person detector.
stop() signals the thread to exit cleanly.
"""

import logging
import threading
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class ProcessManager:

    def __init__(self) -> None:
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._timestamp: Optional[str] = None
        self._lock = threading.Lock()

    def start(self) -> dict:
        with self._lock:
            if self._is_alive():
                raise RuntimeError("Detection is already running.")

            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_detection,
                daemon=True,
                name="scrap-detection-thread",
            )
            self._thread.start()
            self._timestamp = datetime.now().strftime("%m/%d/%Y %I:%M %p")

            logger.info("Detection STARTED — thread=%s", self._thread.name)
            print(f"\n{'='*50}")
            print("  scrap DETECTION STARTED")
            print(f"  Time: {self._timestamp}")
            print(f"{'='*50}\n")

            return self.status

    def stop(self) -> dict:
        with self._lock:
            if not self._is_alive():
                raise RuntimeError("Detection is not running.")

            self._stop_event.set()
            self._thread.join(timeout=10)

            if self._thread.is_alive():
                logger.warning("Detection thread did not exit after 10s — forcing clear.")

            self._thread = None
            self._timestamp = datetime.now().strftime("%m/%d/%Y %I:%M %p")

            logger.info("Detection STOPPED")
            print(f"\n{'='*50}")
            print("  scrap DETECTION STOPPED")
            print(f"  Time: {self._timestamp}")
            print(f"{'='*50}\n")

            return self.status

    @property
    def status(self) -> dict:
        alive = self._is_alive()
        return {
            "status": "running" if alive else "stopped",
            "pid": self._thread.ident if alive else None,
            "timestamp": self._timestamp,
        }

    def _is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run_detection(self):
        from belt_detector.detector import run_detection
        try:
            run_detection(self._stop_event)
        except Exception as e:
            logger.error("Detection crashed: %s", e)
            print(f"\n[ERROR] Detection crashed: {e}\n")
        finally:
            logger.info("Detection thread exited.")
            print("\n[EXIT] Detection thread exited.\n")


# Singleton
process_manager = ProcessManager()
