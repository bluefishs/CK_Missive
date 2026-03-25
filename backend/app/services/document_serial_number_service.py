"""
公文流水號服務

管理公文流水號的生成和分配。

@version 2.0.0
@date 2026-01-19
@updated 2026-03-23 — 遷移至 Repository 層 (B3)
"""

import logging
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_stats_repository import DocumentStatsRepository

logger = logging.getLogger(__name__)


class DocumentSerialNumberService:
    """
    公文流水號服務

    職責：
    - 生成下一個自動流水號
    - 批次分配流水號
    - 流水號統計

    流水號格式：
    - 收文: R0001, R0002, ...
    - 發文: S0001, S0002, ...
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._repo = DocumentStatsRepository(db)

    async def get_next_auto_serial(self, category: str = 'receive') -> str:
        """
        產生下一個自動流水號

        Args:
            category: 公文類別 ('receive' 或 'send')

        Returns:
            下一個流水號，如 'R0001' 或 'S0002'
        """
        prefix = 'R' if category == 'receive' else 'S'
        max_serial = await self._repo.get_max_auto_serial(f'{prefix}%')

        if max_serial:
            try:
                next_num = int(max_serial[1:]) + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        new_serial = f'{prefix}{next_num:04d}'
        logger.debug(f"[流水號] 生成新序號: {new_serial} (類別: {category})")
        return new_serial

    async def allocate_batch(self, category: str, count: int) -> List[str]:
        """
        批次分配流水號

        Args:
            category: 公文類別
            count: 需要的數量

        Returns:
            流水號列表
        """
        prefix = 'R' if category == 'receive' else 'S'
        max_serial = await self._repo.get_max_auto_serial(f'{prefix}%')

        if max_serial:
            try:
                start_num = int(max_serial[1:]) + 1
            except ValueError:
                start_num = 1
        else:
            start_num = 1

        serials = [f'{prefix}{start_num + i:04d}' for i in range(count)]
        logger.info(f"[流水號] 批次分配 {count} 個序號: {serials[0]} - {serials[-1]}")
        return serials

    async def get_statistics(self) -> Dict[str, Any]:
        """取得流水號統計資訊"""
        receive_count = await self._repo.count_by_serial_pattern('R%')
        send_count = await self._repo.count_by_serial_pattern('S%')
        latest_receive = await self._repo.get_max_auto_serial('R%')
        latest_send = await self._repo.get_max_auto_serial('S%')

        return {
            'receive': {
                'count': receive_count,
                'latest_serial': latest_receive,
                'next_serial': await self.get_next_auto_serial('receive')
            },
            'send': {
                'count': send_count,
                'latest_serial': latest_send,
                'next_serial': await self.get_next_auto_serial('send')
            },
            'total': receive_count + send_count
        }

    async def check_serial_exists(self, serial: str) -> bool:
        """檢查流水號是否已存在"""
        return await self._repo.count_by(auto_serial=serial) > 0
