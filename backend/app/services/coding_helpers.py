"""編碼生成輔助工具 (ADR-0013 併發保護)

提供 `retry_on_code_conflict` helper — 在自動生成業務碼 (billing_code /
invoice_ref / ledger_code / asset_code) 時處理高併發 race condition。

背景:
- 生成器 `CaseCodeService.generate_*_code` 使用 `SELECT MAX(code) + 1` 策略
- 兩個並行 request 可能同時讀到相同 max → 產生相同 next_serial
- DB 有 unique constraint，後 flush 的那筆會 `IntegrityError`
- 此 helper 在錯誤時 rollback savepoint 並重試，重新生成下一個序號

設計抉擇:
- 使用 SAVEPOINT (db.begin_nested)，避免污染外層交易
- 只重試指定 unique_field，其他 IntegrityError 原樣拋出
- 預設 3 次重試 (與 ADR-0013 對齊)
"""
from __future__ import annotations

import logging
from typing import Awaitable, Callable, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def retry_on_code_conflict(
    db: AsyncSession,
    operation: Callable[[], Awaitable[T]],
    unique_field: str,
    max_attempts: int = 3,
) -> T:
    """在 SAVEPOINT 內執行 operation，碰到指定欄位的 unique 衝突時重試。

    Args:
        db: SQLAlchemy async session
        operation: 完整業務操作 (含編碼生成 + insert + flush)
        unique_field: 受保護的唯一欄位名 (e.g. "billing_code")
        max_attempts: 最大嘗試次數 (預設 3)

    Returns:
        operation 的回傳值

    Raises:
        IntegrityError: 若超過 max_attempts 仍衝突，或是其他非目標欄位的衝突
    """
    last_error: IntegrityError | None = None

    for attempt in range(1, max_attempts + 1):
        sp = await db.begin_nested()
        try:
            result = await operation()
            await sp.commit()
            if attempt > 1:
                logger.info(
                    "[CODE_RETRY] %s 第 %d 次重試成功", unique_field, attempt
                )
            return result
        except IntegrityError as exc:
            await sp.rollback()
            last_error = exc

            # 判斷是否為目標欄位的衝突；否則直接拋出
            err_msg = str(exc).lower()
            if unique_field.lower() not in err_msg:
                raise

            if attempt < max_attempts:
                logger.warning(
                    "[CODE_RETRY] %s 衝突，第 %d 次重試 (剩餘 %d 次)",
                    unique_field,
                    attempt,
                    max_attempts - attempt,
                )
                continue

            logger.error(
                "[CODE_RETRY] %s 重試 %d 次仍失敗", unique_field, max_attempts
            )
            raise

    # 防禦性 — 理論上不會到達
    assert last_error is not None
    raise last_error
