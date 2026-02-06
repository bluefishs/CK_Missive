"""
DocumentQueryBuilder 單元測試

測試查詢建構器的所有篩選方法、排序、分頁、執行功能。
使用 mock AsyncSession，不做實際 SQL 執行。

@version 1.0.0
@date 2026-02-06
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.query_builders.document_query_builder import DocumentQueryBuilder


class TestDocumentQueryBuilder:
    """DocumentQueryBuilder 測試類"""

    @pytest.fixture
    def mock_db(self):
        """建立模擬的資料庫 session"""
        db = AsyncMock(spec=AsyncSession)
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def mock_result_list(self, mock_db):
        """設定 mock 返回模擬的 ORM 列表"""
        mock_doc1 = MagicMock()
        mock_doc1.id = 1
        mock_doc1.subject = "測試公文一"

        mock_doc2 = MagicMock()
        mock_doc2.id = 2
        mock_doc2.subject = "測試公文二"

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_doc1, mock_doc2]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        return [mock_doc1, mock_doc2]

    @pytest.fixture
    def mock_result_empty(self, mock_db):
        """設定 mock 返回空列表"""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

    @pytest.fixture
    def mock_count_result(self, mock_db):
        """設定 mock 返回計數"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_db.execute.return_value = mock_result

    # =========================================================================
    # 基本操作
    # =========================================================================

    @pytest.mark.asyncio
    async def test_basic_execute(self, mock_db, mock_result_list):
        """空條件執行 → 應返回所有結果"""
        qb = DocumentQueryBuilder(mock_db)
        results = await qb.execute()

        assert len(results) == 2
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_basic_execute_empty(self, mock_db, mock_result_empty):
        """空條件執行 → 無資料時返回空列表"""
        qb = DocumentQueryBuilder(mock_db)
        results = await qb.execute()

        assert results == []

    # =========================================================================
    # 狀態篩選
    # =========================================================================

    @pytest.mark.asyncio
    async def test_with_status(self, mock_db, mock_result_list):
        """with_status 應新增狀態條件"""
        qb = DocumentQueryBuilder(mock_db)
        result_qb = qb.with_status("待處理")

        # 驗證鏈式返回
        assert result_qb is qb
        assert len(qb._conditions) == 1

        await qb.execute()
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_with_statuses(self, mock_db, mock_result_list):
        """with_statuses 應新增 IN 條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_statuses(["待處理", "處理中"])

        assert len(qb._conditions) == 1
        await qb.execute()
        mock_db.execute.assert_called_once()

    # =========================================================================
    # 類型篩選
    # =========================================================================

    @pytest.mark.asyncio
    async def test_with_doc_type(self, mock_db, mock_result_list):
        """with_doc_type 應新增類型條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_doc_type("函")

        assert len(qb._conditions) == 1
        await qb.execute()

    @pytest.mark.asyncio
    async def test_with_category(self, mock_db, mock_result_list):
        """with_category 應新增收發類別條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_category("收文")

        assert len(qb._conditions) == 1

    # =========================================================================
    # 日期篩選
    # =========================================================================

    @pytest.mark.asyncio
    async def test_with_date_range_both(self, mock_db, mock_result_list):
        """with_date_range 起迄日期 → 新增 2 個條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_date_range(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31)
        )

        assert len(qb._conditions) == 2
        await qb.execute()

    @pytest.mark.asyncio
    async def test_with_date_range_start_only(self, mock_db, mock_result_list):
        """with_date_range 僅起始日期 → 新增 1 個條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_date_range(start_date=date(2026, 1, 1))

        assert len(qb._conditions) == 1

    @pytest.mark.asyncio
    async def test_with_date_range_none(self, mock_db, mock_result_list):
        """with_date_range 無日期 → 不新增條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_date_range()

        assert len(qb._conditions) == 0

    @pytest.mark.asyncio
    async def test_with_year(self, mock_db, mock_result_list):
        """with_year 應新增年份條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_year(2026)

        assert len(qb._conditions) == 1

    # =========================================================================
    # 關鍵字搜尋
    # =========================================================================

    @pytest.mark.asyncio
    async def test_with_keyword(self, mock_db, mock_result_list):
        """with_keyword 應新增 ILIKE 條件（5 欄位 OR）"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_keyword("桃園")

        assert len(qb._conditions) == 1
        await qb.execute()

    @pytest.mark.asyncio
    async def test_with_keyword_full(self, mock_db, mock_result_list):
        """with_keyword_full 應新增含 content 的 ILIKE 條件（6 欄位 OR）"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_keyword_full("會勘")

        assert len(qb._conditions) == 1
        await qb.execute()

    @pytest.mark.asyncio
    async def test_with_keywords_full_or(self, mock_db, mock_result_list):
        """with_keywords_full 多關鍵字 OR 邏輯"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_keywords_full(["桃園", "會勘"])

        assert len(qb._conditions) == 1  # 合併為一個 OR 條件
        await qb.execute()

    @pytest.mark.asyncio
    async def test_with_keywords_full_empty(self, mock_db, mock_result_list):
        """with_keywords_full 空列表 → 不新增條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_keywords_full([])

        assert len(qb._conditions) == 0

    @pytest.mark.asyncio
    async def test_with_keywords_and(self, mock_db, mock_result_list):
        """with_keywords AND 邏輯 → 每個關鍵字一個條件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_keywords(["桃園", "會勘"])

        assert len(qb._conditions) == 2  # 每個關鍵字獨立條件

    # =========================================================================
    # 單位篩選
    # =========================================================================

    @pytest.mark.asyncio
    async def test_with_sender_like(self, mock_db, mock_result_list):
        """with_sender_like 模糊篩選發文單位"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_sender_like("桃園市")

        assert len(qb._conditions) == 1

    @pytest.mark.asyncio
    async def test_with_receiver_like(self, mock_db, mock_result_list):
        """with_receiver_like 模糊篩選受文單位"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_receiver_like("中壢區")

        assert len(qb._conditions) == 1

    @pytest.mark.asyncio
    async def test_with_sender_exact(self, mock_db, mock_result_list):
        """with_sender 精確匹配"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_sender("桃園市政府")

        assert len(qb._conditions) == 1

    # =========================================================================
    # 權限與承攬案件
    # =========================================================================

    @pytest.mark.asyncio
    async def test_with_assignee_access(self, mock_db, mock_result_list):
        """with_assignee_access 應新增 RLS 權限條件 (OR: 承辦人匹配 | 無專案)"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_assignee_access("張三")

        assert len(qb._conditions) == 1
        await qb.execute()

    @pytest.mark.asyncio
    async def test_with_contract_case(self, mock_db, mock_result_list):
        """with_contract_case 應 JOIN ContractProject 並篩選案件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_contract_case("某工程案件")

        assert len(qb._conditions) == 1
        await qb.execute()

    # =========================================================================
    # 分頁與排序
    # =========================================================================

    @pytest.mark.asyncio
    async def test_paginate(self, mock_db, mock_result_list):
        """paginate 應設定 offset 和 limit"""
        qb = DocumentQueryBuilder(mock_db)
        qb.paginate(page=3, page_size=20)

        assert qb._offset == 40  # (3-1) * 20
        assert qb._limit == 20

    @pytest.mark.asyncio
    async def test_paginate_page_one(self, mock_db, mock_result_list):
        """paginate 第 1 頁 offset 應為 0"""
        qb = DocumentQueryBuilder(mock_db)
        qb.paginate(page=1, page_size=10)

        assert qb._offset == 0
        assert qb._limit == 10

    @pytest.mark.asyncio
    async def test_limit(self, mock_db, mock_result_list):
        """limit 應設定最大筆數"""
        qb = DocumentQueryBuilder(mock_db)
        qb.limit(50)

        assert qb._limit == 50

    @pytest.mark.asyncio
    async def test_order_by_descending(self, mock_db, mock_result_list):
        """order_by descending 應新增降冪排序"""
        qb = DocumentQueryBuilder(mock_db)
        qb.order_by("doc_date", descending=True)

        assert len(qb._order_columns) == 1
        await qb.execute()

    @pytest.mark.asyncio
    async def test_order_by_ascending(self, mock_db, mock_result_list):
        """order_by ascending 應新增升冪排序"""
        qb = DocumentQueryBuilder(mock_db)
        qb.order_by("doc_date", descending=False)

        assert len(qb._order_columns) == 1

    @pytest.mark.asyncio
    async def test_order_by_invalid_column(self, mock_db, mock_result_list):
        """order_by 無效欄位應 fallback 到 id"""
        qb = DocumentQueryBuilder(mock_db)
        qb.order_by("nonexistent_column")

        assert len(qb._order_columns) == 1
        # 不應拋出例外
        await qb.execute()

    # =========================================================================
    # 鏈式呼叫
    # =========================================================================

    @pytest.mark.asyncio
    async def test_chaining(self, mock_db, mock_result_list):
        """流暢介面鏈式呼叫 → 所有方法應返回 self"""
        qb = (
            DocumentQueryBuilder(mock_db)
            .with_status("待處理")
            .with_doc_type("函")
            .with_category("收文")
            .with_date_range(date(2026, 1, 1), date(2026, 1, 31))
            .with_keyword("桃園")
            .order_by("doc_date", descending=True)
            .paginate(page=1, page_size=20)
        )

        assert len(qb._conditions) == 6  # status + doc_type + category + date_start + date_end + keyword
        assert len(qb._order_columns) == 1
        assert qb._offset == 0
        assert qb._limit == 20

        await qb.execute()
        mock_db.execute.assert_called_once()

    # =========================================================================
    # count / first / execute_with_count
    # =========================================================================

    @pytest.mark.asyncio
    async def test_count(self, mock_db, mock_count_result):
        """count 應返回整數"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_status("待處理")

        count = await qb.count()
        assert count == 42

    @pytest.mark.asyncio
    async def test_count_zero(self, mock_db):
        """count 無結果應返回 0"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        mock_db.execute.return_value = mock_result

        qb = DocumentQueryBuilder(mock_db)
        count = await qb.count()
        assert count == 0

    @pytest.mark.asyncio
    async def test_first_found(self, mock_db, mock_result_list):
        """first 有結果 → 返回第一筆"""
        qb = DocumentQueryBuilder(mock_db)
        result = await qb.first()

        assert result is not None
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_first_not_found(self, mock_db, mock_result_empty):
        """first 無結果 → 返回 None"""
        qb = DocumentQueryBuilder(mock_db)
        result = await qb.first()

        assert result is None

    @pytest.mark.asyncio
    async def test_exists_true(self, mock_db, mock_count_result):
        """exists 有結果 → True"""
        qb = DocumentQueryBuilder(mock_db)
        assert await qb.exists() is True

    @pytest.mark.asyncio
    async def test_exists_false(self, mock_db):
        """exists 無結果 → False"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_result

        qb = DocumentQueryBuilder(mock_db)
        assert await qb.exists() is False

    # =========================================================================
    # 其他篩選
    # =========================================================================

    @pytest.mark.asyncio
    async def test_with_receiver_exact(self, mock_db, mock_result_list):
        """with_receiver 精確匹配受文單位"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_receiver("桃園市政府")
        assert len(qb._conditions) == 1

    @pytest.mark.asyncio
    async def test_with_agency_id(self, mock_db, mock_result_list):
        """with_agency_id 篩選機關 ID（發文或受文）"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_agency_id(10)
        assert len(qb._conditions) == 1

    @pytest.mark.asyncio
    async def test_with_project_id(self, mock_db, mock_result_list):
        """with_project_id 篩選專案關聯"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_project_id(5)
        assert len(qb._conditions) == 1

    @pytest.mark.asyncio
    async def test_with_has_attachment(self, mock_db, mock_result_list):
        """with_has_attachment 篩選有附件"""
        qb = DocumentQueryBuilder(mock_db)
        qb.with_has_attachment(True)
        assert len(qb._conditions) == 1
