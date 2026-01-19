"""
公文流水號服務

管理公文流水號的生成和分配。

@version 1.0.0
@date 2026-01-19
"""

import logging
from datetime import date
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import OfficialDocument as Document

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
        """
        初始化流水號服務

        Args:
            db: 資料庫會話
        """
        self.db = db

    async def get_next_auto_serial(self, category: str = 'receive') -> str:
        """
        產生下一個自動流水號

        收文使用 R 前綴，發文使用 S 前綴。
        自動從資料庫查詢當前最大序號。

        Args:
            category: 公文類別 ('receive' 或 'send')

        Returns:
            下一個流水號，如 'R0001' 或 'S0002'
        """
        prefix = 'R' if category == 'receive' else 'S'
        pattern = f'{prefix}%'

        # 查詢當前最大序號
        max_serial_query = select(
            func.max(Document.auto_serial)
        ).where(
            Document.auto_serial.like(pattern)
        )

        result = await self.db.execute(max_serial_query)
        max_serial = result.scalar()

        if max_serial:
            # 提取數字部分並加 1
            try:
                current_num = int(max_serial[1:])
                next_num = current_num + 1
            except ValueError:
                next_num = 1
        else:
            next_num = 1

        new_serial = f'{prefix}{next_num:04d}'
        logger.debug(f"[流水號] 生成新序號: {new_serial} (類別: {category})")
        return new_serial

    async def allocate_batch(
        self,
        category: str,
        count: int
    ) -> List[str]:
        """
        批次分配流水號

        Args:
            category: 公文類別
            count: 需要的數量

        Returns:
            流水號列表
        """
        serials = []
        prefix = 'R' if category == 'receive' else 'S'
        pattern = f'{prefix}%'

        # 查詢當前最大序號
        max_serial_query = select(
            func.max(Document.auto_serial)
        ).where(
            Document.auto_serial.like(pattern)
        )

        result = await self.db.execute(max_serial_query)
        max_serial = result.scalar()

        if max_serial:
            try:
                start_num = int(max_serial[1:]) + 1
            except ValueError:
                start_num = 1
        else:
            start_num = 1

        for i in range(count):
            serials.append(f'{prefix}{start_num + i:04d}')

        logger.info(f"[流水號] 批次分配 {count} 個序號: {serials[0]} - {serials[-1]}")
        return serials

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得流水號統計資訊

        Returns:
            統計資訊字典
        """
        # 收文統計
        receive_count_query = select(
            func.count(Document.id)
        ).where(
            Document.auto_serial.like('R%')
        )
        receive_result = await self.db.execute(receive_count_query)
        receive_count = receive_result.scalar() or 0

        # 發文統計
        send_count_query = select(
            func.count(Document.id)
        ).where(
            Document.auto_serial.like('S%')
        )
        send_result = await self.db.execute(send_count_query)
        send_count = send_result.scalar() or 0

        # 最新序號
        latest_receive_query = select(
            func.max(Document.auto_serial)
        ).where(
            Document.auto_serial.like('R%')
        )
        latest_receive_result = await self.db.execute(latest_receive_query)
        latest_receive = latest_receive_result.scalar()

        latest_send_query = select(
            func.max(Document.auto_serial)
        ).where(
            Document.auto_serial.like('S%')
        )
        latest_send_result = await self.db.execute(latest_send_query)
        latest_send = latest_send_result.scalar()

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
        """
        檢查流水號是否已存在

        Args:
            serial: 要檢查的流水號

        Returns:
            是否存在
        """
        query = select(func.count(Document.id)).where(
            Document.auto_serial == serial
        )
        result = await self.db.execute(query)
        count = result.scalar() or 0
        return count > 0
