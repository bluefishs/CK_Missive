"""
電子發票同步功能單元測試

測試範圍:
- MofApiClient: HMAC 簽章、日期轉換、API 參數構建
- EInvoiceSyncService: 同步流程、重複過濾、收據關聯
"""
import hashlib
import hmac
import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================
# MofApiClient Tests
# ============================================================

class TestMofApiClient:
    """財政部 API 客戶端測試"""

    def _make_client(self):
        from app.services.einvoice.mof_api_client import MofApiClient
        return MofApiClient(
            app_id="TEST_APP_ID",
            api_key="TEST_API_KEY",
            company_ban="12345678",
        )

    def test_is_configured_true(self):
        client = self._make_client()
        assert client.is_configured is True

    def test_is_configured_false_missing_app_id(self):
        from app.services.einvoice.mof_api_client import MofApiClient
        client = MofApiClient(app_id="", api_key="key", company_ban="12345678")
        assert client.is_configured is False

    def test_is_configured_false_missing_ban(self):
        from app.services.einvoice.mof_api_client import MofApiClient
        client = MofApiClient(app_id="id", api_key="key", company_ban="")
        assert client.is_configured is False

    def test_date_to_roc(self):
        client = self._make_client()
        # 2026-03-21 → 民國 115/03/21
        assert client._date_to_roc(date(2026, 3, 21)) == "115/03/21"
        # 2024-01-01 → 民國 113/01/01
        assert client._date_to_roc(date(2024, 1, 1)) == "113/01/01"

    def test_roc_to_date(self):
        client = self._make_client()
        # 1150321 → 2026-03-21
        assert client._roc_to_date("1150321") == date(2026, 3, 21)
        # 1130101 → 2024-01-01
        assert client._roc_to_date("1130101") == date(2024, 1, 1)
        # 帶斜線格式
        assert client._roc_to_date("115/03/21") == date(2026, 3, 21)

    def test_roc_to_date_invalid(self):
        client = self._make_client()
        with pytest.raises(ValueError, match="無法解析民國日期"):
            client._roc_to_date("abc")

    def test_build_period(self):
        client = self._make_client()
        # 1月 → 11501 (1-2月期)
        assert client._build_period(date(2026, 1, 15)) == "11501"
        # 2月 → 11501 (1-2月期)
        assert client._build_period(date(2026, 2, 15)) == "11501"
        # 3月 → 11503 (3-4月期)
        assert client._build_period(date(2026, 3, 15)) == "11503"
        # 12月 → 11511 (11-12月期)
        assert client._build_period(date(2026, 12, 1)) == "11511"

    def test_generate_signature(self):
        """驗證 HMAC-SHA256 簽章產生"""
        client = self._make_client()
        params = {"appID": "TEST_APP_ID", "buyerBan": "12345678"}
        sig = client._generate_signature(params)

        # 手動計算預期簽章
        expected_str = "appID=TEST_APP_ID&buyerBan=12345678"
        expected_sig = hmac.new(
            b"TEST_API_KEY", expected_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        assert sig == expected_sig

    def test_parse_invoice_header_basic(self):
        """測試發票表頭解析"""
        client = self._make_client()
        raw = {
            "invNum": "AB12345678",
            "invDate": "1150321",
            "sellerBan": "87654321",
            "buyerBan": "12345678",
            "invAmount": 2500,
            "taxAmount": 125,
            "sellerName": "測試公司",
            "invStatus": "正常",
            "invPeriod": "11503",
        }
        result = client._parse_invoice_header(raw)

        assert result["inv_num"] == "AB12345678"
        assert result["date"] == date(2026, 3, 21)
        assert result["seller_ban"] == "87654321"
        assert result["amount"] == Decimal("2500")
        assert result["tax_amount"] == Decimal("125")
        assert result["seller_name"] == "測試公司"

    @pytest.mark.asyncio
    async def test_query_buyer_invoices_no_ban(self):
        """未設定統編時應拋出 MofApiError"""
        from app.services.einvoice.mof_api_client import MofApiClient, MofApiError
        client = MofApiClient(app_id="id", api_key="key", company_ban="")
        with pytest.raises(MofApiError, match="未設定公司統編"):
            await client.query_buyer_invoices(date(2026, 3, 1), date(2026, 3, 21))

    @pytest.mark.asyncio
    async def test_query_buyer_invoices_success(self):
        """模擬 API 成功回應"""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "code": "200",
            "msg": "success",
            "details": [
                {
                    "invNum": "AB12345678",
                    "invDate": "1150321",
                    "sellerBan": "87654321",
                    "buyerBan": "12345678",
                    "invAmount": 2500,
                    "sellerName": "測試公司",
                },
            ],
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        client._client = mock_client

        result = await client.query_buyer_invoices(date(2026, 3, 1), date(2026, 3, 21))
        assert len(result) == 1
        assert result[0]["inv_num"] == "AB12345678"

    @pytest.mark.asyncio
    async def test_query_buyer_invoices_api_error(self):
        """模擬 API 回傳錯誤碼"""
        from app.services.einvoice.mof_api_client import MofApiError
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "code": "900",
            "msg": "API 金鑰無效",
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        client._client = mock_client

        with pytest.raises(MofApiError, match="API 金鑰無效"):
            await client.query_buyer_invoices(date(2026, 3, 1), date(2026, 3, 21))

    @pytest.mark.asyncio
    async def test_query_invoice_detail_success(self):
        """模擬發票明細查詢成功"""
        client = self._make_client()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "code": "200",
            "details": [
                {
                    "description": "A4 影印紙",
                    "quantity": "10",
                    "unitPrice": "250",
                    "amount": "2500",
                },
            ],
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        client._client = mock_client

        result = await client.query_invoice_detail("AB12345678", date(2026, 3, 21))
        assert len(result) == 1
        assert result[0]["item_name"] == "A4 影印紙"
        assert result[0]["qty"] == Decimal("10")
        assert result[0]["amount"] == Decimal("2500")


# ============================================================
# EInvoiceSyncService Tests
# ============================================================

class TestEInvoiceSyncService:
    """電子發票同步服務測試"""

    def _make_service(self, db_mock=None, client_mock=None):
        from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService
        db = db_mock or AsyncMock()
        client = client_mock or MagicMock()
        client.is_configured = True
        client.company_ban = "12345678"
        return EInvoiceSyncService(db=db, client=client)

    @pytest.mark.asyncio
    async def test_sync_skipped_when_not_configured(self):
        """API 未設定時應跳過同步"""
        from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService
        client = MagicMock()
        client.is_configured = False
        service = EInvoiceSyncService(db=AsyncMock(), client=client)

        result = await service.sync_invoices()
        assert result["status"] == "skipped"
        assert "未設定" in result["reason"]

    @pytest.mark.asyncio
    async def test_sync_new_invoices(self):
        """測試正常同步新發票"""
        from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService

        db = AsyncMock()
        # flush 和 commit 不需要回傳值
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        # 模擬 _get_existing_inv_nums 回傳空集合 (沒有重複)
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        client = AsyncMock()
        client.is_configured = True
        client.company_ban = "12345678"
        client.query_buyer_invoices = AsyncMock(return_value=[
            {
                "inv_num": "CD87654321",
                "date": date(2026, 3, 20),
                "amount": Decimal("1500"),
                "seller_ban": "11111111",
                "buyer_ban": "12345678",
                "seller_name": "文具店",
                "inv_period": "11503",
            },
        ])
        client.query_invoice_detail = AsyncMock(return_value=[
            {
                "item_name": "原子筆",
                "qty": Decimal("5"),
                "unit_price": Decimal("300"),
                "amount": Decimal("1500"),
            },
        ])
        client.close = AsyncMock()

        service = EInvoiceSyncService(db=db, client=client)
        result = await service.sync_invoices(
            start_date=date(2026, 3, 18), end_date=date(2026, 3, 21)
        )

        assert result["total_fetched"] == 1
        assert result["new_imported"] == 1
        assert result["skipped_duplicate"] == 0
        assert result["detail_fetched"] == 1

    @pytest.mark.asyncio
    async def test_sync_skips_duplicates(self):
        """測試重複發票會被跳過"""
        from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService

        db = AsyncMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()

        # 模擬 existing_inv_nums 已包含 CD87654321
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("CD87654321",)]
        db.execute = AsyncMock(return_value=mock_result)

        client = AsyncMock()
        client.is_configured = True
        client.company_ban = "12345678"
        client.query_buyer_invoices = AsyncMock(return_value=[
            {
                "inv_num": "CD87654321",
                "date": date(2026, 3, 20),
                "amount": Decimal("1500"),
                "seller_ban": "11111111",
                "buyer_ban": "12345678",
                "seller_name": "重複店家",
                "inv_period": "11503",
            },
        ])
        client.close = AsyncMock()

        service = EInvoiceSyncService(db=db, client=client)
        result = await service.sync_invoices()

        assert result["total_fetched"] == 1
        assert result["new_imported"] == 0
        assert result["skipped_duplicate"] == 1

    @pytest.mark.asyncio
    async def test_attach_receipt_success(self):
        """測試收據上傳關聯成功"""
        from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService
        from unittest.mock import PropertyMock

        invoice = MagicMock()
        invoice.status = "pending_receipt"
        invoice.id = 1

        db = AsyncMock()
        db.get = AsyncMock(return_value=invoice)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        service = EInvoiceSyncService(db=db, client=MagicMock())
        result = await service.attach_receipt(
            invoice_id=1,
            receipt_path="/uploads/receipts/test.jpg",
            case_code="A-115-001",
            category="文具及印刷",
            user_id=5,
        )

        assert result is not None
        assert invoice.receipt_image_path == "/uploads/receipts/test.jpg"
        assert invoice.status == "pending"
        assert invoice.case_code == "A-115-001"
        assert invoice.category == "文具及印刷"
        assert invoice.user_id == 5

    @pytest.mark.asyncio
    async def test_attach_receipt_wrong_status(self):
        """非 pending_receipt 狀態不可上傳收據"""
        from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService

        invoice = MagicMock()
        invoice.status = "verified"

        db = AsyncMock()
        db.get = AsyncMock(return_value=invoice)

        service = EInvoiceSyncService(db=db, client=MagicMock())

        with pytest.raises(ValueError, match="僅 pending_receipt 可上傳收據"):
            await service.attach_receipt(
                invoice_id=1,
                receipt_path="/uploads/test.jpg",
            )

    @pytest.mark.asyncio
    async def test_attach_receipt_not_found(self):
        """發票不存在時回傳 None"""
        from app.services.einvoice.einvoice_sync_service import EInvoiceSyncService

        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        service = EInvoiceSyncService(db=db, client=MagicMock())
        result = await service.attach_receipt(
            invoice_id=999,
            receipt_path="/uploads/test.jpg",
        )
        assert result is None


# ============================================================
# Schema Tests
# ============================================================

class TestEInvoiceSyncSchemas:
    """電子發票同步 Schema 測試"""

    def test_sync_request_defaults(self):
        from app.schemas.erp.einvoice_sync import EInvoiceSyncRequest
        req = EInvoiceSyncRequest()
        assert req.start_date is None
        assert req.end_date is None

    def test_sync_request_with_dates(self):
        from app.schemas.erp.einvoice_sync import EInvoiceSyncRequest
        req = EInvoiceSyncRequest(
            start_date=date(2026, 3, 1),
            end_date=date(2026, 3, 21),
        )
        assert req.start_date == date(2026, 3, 1)
        assert req.end_date == date(2026, 3, 21)

    def test_pending_receipt_query_defaults(self):
        from app.schemas.erp.einvoice_sync import PendingReceiptQuery
        q = PendingReceiptQuery()
        assert q.skip == 0
        assert q.limit == 20

    def test_receipt_upload_request(self):
        from app.schemas.erp.einvoice_sync import ReceiptUploadRequest
        req = ReceiptUploadRequest(
            invoice_id=42,
            case_code="A-115-001",
            category="交通費",
        )
        assert req.invoice_id == 42
        assert req.case_code == "A-115-001"

    def test_expense_source_includes_mof_sync(self):
        """確認 expense schema source 欄位包含 mof_sync"""
        from app.schemas.erp.expense import ExpenseInvoiceBase
        # 建立 source=mof_sync 的實例不應拋出驗證錯誤
        data = ExpenseInvoiceBase(
            inv_num="AB12345678",
            date=date(2026, 3, 21),
            amount=Decimal("2500"),
            source="mof_sync",
        )
        assert data.source == "mof_sync"
