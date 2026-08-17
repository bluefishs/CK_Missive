"""公司固定利潤率（公司留成）—— 讀取與驗證。

owner 2026-08-18：「若可設定公司固定利潤如 10%，那總金額扣除前述才應該是專案毛利」。

    營收     = 總價 − 稅額
    公司留成 = 營收 × 比率        ← 這裡負責取得「比率」
    專案可用 = 營收 − 公司留成
    專案毛利 = 專案可用 − 成本

# 為什麼單獨一個檔

比率會被三個地方讀（報價服務、報價 repository 的清單聚合、損益彙總），
而它需要 DB 存取 ＋ 驗證 ＋ 快取。塞進 `quotation_service` 會讓那支
純函式 `compute_quotation_profit` 被迫拿到 db session ——
它現在是純函式，被 io/repository/service 三處共用，那是它的價值。

所以維持分工：**這裡負責「比率是多少」，計算仍是純函式**。

# 為什麼要快取

報價清單一次算 N 筆毛利。若每筆都查一次設定表，
50 筆清單就是 50 次查詢，而那個值一天不會變一次。

快取 TTL 60 秒（不是永久）：owner 在 `/admin/site-management` 改了值之後
應該在一分鐘內看到毛利跟著變，而不是要等重啟 ——
「改了設定但畫面沒變」會讓人以為設定沒生效而重複操作。
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

CONFIG_KEY = "erp_company_profit_rate"

#: 快取存活秒數 —— 見模組 docstring
_TTL_SECONDS = 60

#: (值, 取得時間)。行程內快取；多 worker 各有一份，
#: 但因為它只是延遲 60 秒可見，不需要跨行程一致。
_cache: tuple[Decimal, float] | None = None

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _parse(raw: Optional[str]) -> Decimal:
    """把設定值（百分比字串）解析成 0~1 的小數。

    ⚠️ **無法解析時回 0 而不是拋錯**，且一定留下 warning：
    比率算錯的後果是全公司毛利數字錯，而拋錯的後果是報價頁整個打不開。
    回 0 等於「不扣」＝與設定這個功能之前完全相同的行為，
    是這裡唯一不會讓人看到錯誤數字的降級方式。

    但**必須出聲** —— 靜靜回 0 的話，「設定被打錯」與「刻意設 0」
    在畫面上長得一模一樣（ADR-0028）。
    """
    if raw is None or str(raw).strip() == "":
        return ZERO
    try:
        pct = Decimal(str(raw).strip())
    except (InvalidOperation, ValueError):
        logger.error(
            "公司固定利潤率設定值無法解析為數字，暫以 0%% 計算（毛利將不扣公司留成）: %r",
            raw,
        )
        return ZERO

    if pct < ZERO or pct >= HUNDRED:
        # >= 100% 會讓專案可用金額變成 0 或負數 —— 那不是「利潤很高」，
        # 是設定打錯了（例如把 0.1 寫成 10 之後又乘 100）。
        logger.error(
            "公司固定利潤率 %s%% 超出合理範圍（0 <= rate < 100），暫以 0%% 計算", pct
        )
        return ZERO

    return pct / HUNDRED


async def get_company_profit_rate(db: AsyncSession) -> Decimal:
    """取得公司固定利潤率（0~1 的小數；0 表示不扣）。"""
    global _cache
    now = time.monotonic()
    if _cache is not None and (now - _cache[1]) < _TTL_SECONDS:
        return _cache[0]

    try:
        raw = (await db.execute(
            text("SELECT value FROM site_configurations "
                 "WHERE key = :k AND is_active = true"),
            {"k": CONFIG_KEY},
        )).scalar()
    except Exception:
        # 設定表讀不到（連線問題／表不存在）—— 同樣降級為 0 並出聲。
        # **不快取失敗結果**：下一次請求應該再試一次，
        # 否則一次暫時性失敗會讓比率消失 60 秒而沒有人知道。
        logger.exception("讀取公司固定利潤率失敗，暫以 0%% 計算")
        return ZERO

    rate = _parse(raw)
    _cache = (rate, now)
    return rate


def invalidate_cache() -> None:
    """設定值被更新後呼叫，讓下一次讀取立即拿到新值。

    有這支是因為 60 秒 TTL 對「剛按下儲存的人」還是太久 ——
    他會看到舊數字並懷疑自己沒存成功。
    """
    global _cache
    _cache = None
