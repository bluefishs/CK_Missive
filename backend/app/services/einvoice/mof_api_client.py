"""
財政部電子發票大平台 API 客戶端

串接財政部「電子發票應用 API」，使用 HMAC-SHA256 簽章驗證。
主要 API:
  - QryBuyerInvTitle: 查詢買方發票表頭 (依統編+期間)
  - QryInvDetail: 查詢發票明細 (依發票號碼+日期)

環境變數:
  MOF_APP_ID:  財政部核發之 AppID
  MOF_API_KEY: 財政部核發之 API Key (HMAC 密鑰)
  COMPANY_BAN: 公司統編 (8 碼)

Version: 1.0.0
Created: 2026-03-21
"""
import hashlib
import hmac
import logging
import os
import time
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# 財政部 API 基底 URL
MOF_API_BASE = "https://api.einvoice.nat.gov.tw/PB2CAPIVAN/invapp/InvApp"


class MofApiError(Exception):
    """財政部 API 錯誤"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"MOF API Error [{code}]: {message}")


class MofApiClient:
    """財政部電子發票 API 客戶端

    使用 HMAC-SHA256 簽章驗證，每次請求自動產生簽章。
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
        company_ban: Optional[str] = None,
    ):
        self.app_id = app_id or os.getenv("MOF_APP_ID", "")
        self.api_key = api_key or os.getenv("MOF_API_KEY", "")
        self.company_ban = company_ban or os.getenv("COMPANY_BAN", "")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        """檢查 API 憑證是否已設定"""
        return bool(self.app_id and self.api_key and self.company_ban)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _generate_signature(self, params: dict) -> str:
        """產生 HMAC-SHA256 簽章

        財政部規格: 將所有參數依 key 排序後串接，以 API Key 作為 HMAC 密鑰。
        """
        sorted_params = sorted(params.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params)
        signature = hmac.new(
            self.api_key.encode("utf-8"),
            param_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _date_to_roc(self, d: date) -> str:
        """西元日期轉民國年字串 (YYYY/MM/DD → YYY/MM/DD)"""
        roc_year = d.year - 1911
        return f"{roc_year}/{d.month:02d}/{d.day:02d}"

    def _roc_to_date(self, roc_str: str) -> date:
        """民國年字串轉西元日期 (YYY/MM/DD 或 YYYMMDD)"""
        cleaned = roc_str.replace("/", "")
        if len(cleaned) == 7:
            roc_year = int(cleaned[0:3])
            month = int(cleaned[3:5])
            day = int(cleaned[5:7])
            return date(roc_year + 1911, month, day)
        raise ValueError(f"無法解析民國日期: {roc_str}")

    def _build_period(self, d: date) -> str:
        """計算發票期別 (民國年+月份雙月制: 01-02, 03-04, ...)

        台灣電子發票以雙月為期: 1-2月=01-02, 3-4月=03-04, etc.
        """
        roc_year = d.year - 1911
        # 雙月制: 奇數月與其下一個偶數月為一期
        period_month = d.month if d.month % 2 == 1 else d.month - 1
        return f"{roc_year}{period_month:02d}"

    async def query_buyer_invoices(
        self,
        start_date: date,
        end_date: date,
        buyer_ban: Optional[str] = None,
    ) -> list[dict]:
        """查詢買方發票表頭 (QryBuyerInvTitle 或類似端點)

        Args:
            start_date: 查詢起始日期
            end_date: 查詢結束日期
            buyer_ban: 買方統編 (預設使用 COMPANY_BAN)

        Returns:
            發票表頭清單 [{inv_num, date, amount, seller_ban, ...}, ...]
        """
        ban = buyer_ban or self.company_ban
        if not ban:
            raise MofApiError("CONFIG", "未設定公司統編 (COMPANY_BAN)")

        timestamp = int(time.time())
        uuid_str = str(uuid.uuid4())

        params = {
            "version": "0.5",
            "type": "Barcode",
            "invTerm": self._build_period(start_date),
            "action": "qryInvHeader",
            "generation": "V2",
            "appID": self.app_id,
            "buyerBan": ban,
            "startDate": self._date_to_roc(start_date),
            "endDate": self._date_to_roc(end_date),
            "UUID": uuid_str,
            "timeStamp": str(timestamp),
        }
        params["signature"] = self._generate_signature(params)

        client = await self._get_client()
        try:
            response = await client.post(MOF_API_BASE, data=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            raise MofApiError("HTTP", f"API 請求失敗: {e}") from e

        if data.get("code") != "200":
            raise MofApiError(
                data.get("code", "UNKNOWN"),
                data.get("msg", "未知錯誤"),
            )

        invoices = []
        for item in data.get("details", []):
            try:
                invoices.append(self._parse_invoice_header(item))
            except Exception as e:
                logger.warning(f"解析發票表頭失敗: {e}, raw={item}")

        return invoices

    def _parse_invoice_header(self, raw: dict) -> dict:
        """解析 API 回傳的發票表頭"""
        inv_num = raw.get("invNum", "")
        inv_date_raw = raw.get("invDate")

        # 嘗試多種日期格式
        if isinstance(inv_date_raw, str):
            inv_date = self._roc_to_date(inv_date_raw)
        elif isinstance(inv_date_raw, dict):
            inv_date_str = (
                inv_date_raw.get("year", "")
                + inv_date_raw.get("month", "").zfill(2)
                + inv_date_raw.get("day", "").zfill(2)
            )
            inv_date = self._roc_to_date(inv_date_str) if len(inv_date_str) >= 7 else date.today()
        else:
            inv_date = date.today()

        return {
            "inv_num": inv_num,
            "date": inv_date,
            "seller_ban": raw.get("sellerBan", ""),
            "buyer_ban": raw.get("buyerBan", self.company_ban),
            "amount": Decimal(str(raw.get("invAmount", raw.get("amount", 0)))),
            "tax_amount": Decimal(str(raw.get("taxAmount", 0))) if raw.get("taxAmount") else None,
            "seller_name": raw.get("sellerName", ""),
            "inv_status": raw.get("invStatus", ""),
            "inv_period": raw.get("invPeriod", ""),
        }

    async def query_invoice_detail(
        self,
        inv_num: str,
        inv_date: date,
    ) -> list[dict]:
        """查詢發票明細 (品名/數量/單價)

        Args:
            inv_num: 發票號碼
            inv_date: 發票日期

        Returns:
            品名明細清單 [{item_name, qty, unit_price, amount}, ...]
        """
        timestamp = int(time.time())
        uuid_str = str(uuid.uuid4())

        params = {
            "version": "0.5",
            "type": "Barcode",
            "invNum": inv_num,
            "action": "qryInvDetail",
            "generation": "V2",
            "invTerm": self._build_period(inv_date),
            "invDate": self._date_to_roc(inv_date),
            "appID": self.app_id,
            "UUID": uuid_str,
            "timeStamp": str(timestamp),
        }
        params["signature"] = self._generate_signature(params)

        client = await self._get_client()
        try:
            response = await client.post(MOF_API_BASE, data=params)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            raise MofApiError("HTTP", f"明細查詢失敗: {e}") from e

        if data.get("code") != "200":
            logger.warning(
                f"發票明細查詢失敗: inv_num={inv_num}, "
                f"code={data.get('code')}, msg={data.get('msg')}"
            )
            return []

        items = []
        for item in data.get("details", []):
            try:
                items.append({
                    "item_name": item.get("description", "未知品名"),
                    "qty": Decimal(str(item.get("quantity", 1))),
                    "unit_price": Decimal(str(item.get("unitPrice", 0))),
                    "amount": Decimal(str(item.get("amount", 0))),
                })
            except Exception as e:
                logger.warning(f"解析發票明細失敗: {e}, raw={item}")

        return items
