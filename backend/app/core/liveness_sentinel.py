# -*- coding: utf-8 -*-
"""事件迴圈活體哨兵（A127-④，2026-09-09）。

## 為什麼要有它

09-08 22:27–23:11 backend「假活」44 分鐘：行程活著、埠綁著、docker healthcheck 連敗 57 次，
而 main.py 原有的 Self-health watchdog **一行警告都沒有** —— 因為它是跑在同一個事件迴圈上的
coroutine，迴圈被佔住時它連 sleep 都醒不來。**偵測「迴圈卡住」的哨兵不能住在那個迴圈裡。**

docker 的 `restart: always` 只看行程有沒有退出，不看 health ⇒ unhealthy 不會自癒。
所以修法是：一條獨立的作業系統執行緒定時打自己的 `/health`，連續拿不到「任何回應」就
`os._exit()`，讓 restart policy 接手。零費用、不需要 docker.sock。

## 判準（刻意的）

* **只有「沒有回應」算失敗**（逾時、連線被拒）。HTTP 503／500 都算活著 ——
  那代表事件迴圈在跑、只是業務檢查不過（例如 DB 暫時掛了）；這種情況重啟行程沒有幫助，
  反而會在 DB 恢復前製造無限重啟。
* 連續 `max_failures` 次才退出，避免單次慢回應（GC、重排程）誤殺。
  ⚠️ 首版預設 3 × (30s + 15s) ≈ 2 分鐘：上線第一晚 02:00 備份＋每日檢核同時跑，/health 有 1.7 分鐘打不到，
  哨兵數到 2/3 才恢復——差一次就把正在備份的行程殺掉。02:00 那種「迴圈被塞住幾分鐘」是可恢復的，
  09-08 那種 44 分鐘的才是要殺的 ⇒ 改成 6 × (30s + 20s) ≈ 5 分鐘。仍比 docker healthcheck 的 57 連敗快十倍。
* 退出碼固定 3，方便在 `docker inspect .State.ExitCode` 與日誌裡認出「是哨兵殺的」，
  不與 uvicorn 自己的退出碼混淆。

## 環境變數

LIVENESS_SENTINEL_ENABLED（預設 true）／LIVENESS_SENTINEL_INTERVAL（秒，預設 30）／
LIVENESS_SENTINEL_TIMEOUT（秒，預設 20）／LIVENESS_SENTINEL_MAX_FAILURES（預設 6）／
BACKEND_PORT（預設 8001；host PM2 模式會設成 8002）。
"""
from __future__ import annotations

import logging
import os
import threading
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

EXIT_CODE = 3


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("%s=%r 不是整數，改用預設 %d", name, raw, default)
        return default


def is_enabled() -> bool:
    return os.environ.get("LIVENESS_SENTINEL_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")


def probe_once(url: str, timeout: float) -> bool:
    """回 True＝事件迴圈有回應（任何 HTTP 狀態碼都算）；False＝逾時或連不上。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 - 固定打 127.0.0.1
            resp.read(64)
        return True
    except urllib.error.HTTPError:
        # 503／500 仍是「迴圈在跑」的證據
        return True
    except Exception:  # noqa: BLE001 - URLError／socket.timeout／ConnectionRefused
        return False


def should_exit(consecutive_failures: int, max_failures: int) -> bool:
    """純函式，給測試用：連續失敗達門檻才退出。"""
    return max_failures > 0 and consecutive_failures >= max_failures


class LivenessSentinel(threading.Thread):
    def __init__(
        self,
        url: str,
        interval: float = 30.0,
        timeout: float = 20.0,
        max_failures: int = 6,
        exit_fn=os._exit,
        probe=probe_once,
        sleep=time.sleep,
    ) -> None:
        super().__init__(name="liveness-sentinel", daemon=True)
        self.url = url
        self.interval = interval
        self.timeout = timeout
        self.max_failures = max_failures
        self._exit_fn = exit_fn
        self._probe = probe
        self._sleep = sleep
        self.failures = 0
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def tick(self) -> bool:
        """跑一輪探測；回 True＝這一輪決定退出（測試用；正式路徑會直接 _exit）。"""
        alive = self._probe(self.url, self.timeout)
        if alive:
            if self.failures:
                logger.warning("liveness sentinel: 回應恢復（先前連續失敗 %d 次）", self.failures)
            self.failures = 0
            return False
        self.failures += 1
        logger.error("liveness sentinel: %s 無回應（連續 %d/%d）", self.url, self.failures, self.max_failures)
        if should_exit(self.failures, self.max_failures):
            logger.critical(
                "liveness sentinel: 事件迴圈連續 %d 次無回應，以 exit %d 結束行程交給 restart policy",
                self.failures, EXIT_CODE,
            )
            self._exit_fn(EXIT_CODE)
            return True
        return False

    def run(self) -> None:
        # 啟動後先等一輪，讓 uvicorn 真的開始 accept
        self._sleep(self.interval)
        while not self._stop.is_set():
            self.tick()
            self._sleep(self.interval)


def start_from_env() -> LivenessSentinel | None:
    if not is_enabled():
        logger.info("liveness sentinel: 由 LIVENESS_SENTINEL_ENABLED 停用")
        return None
    port = _env_int("BACKEND_PORT", 8001)
    sentinel = LivenessSentinel(
        url=f"http://127.0.0.1:{port}/health",
        interval=_env_int("LIVENESS_SENTINEL_INTERVAL", 30),
        timeout=_env_int("LIVENESS_SENTINEL_TIMEOUT", 20),
        max_failures=_env_int("LIVENESS_SENTINEL_MAX_FAILURES", 6),
    )
    sentinel.start()
    logger.info(
        "✅ liveness sentinel started（獨立執行緒；%s，每 %ss，逾時 %ss，連續 %d 次無回應即 exit %d）",
        sentinel.url, sentinel.interval, sentinel.timeout, sentinel.max_failures, EXIT_CODE,
    )
    return sentinel
