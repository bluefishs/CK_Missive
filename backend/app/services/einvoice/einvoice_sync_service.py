"""
電子發票自動同步服務

每晚排程從財政部大平台下載公司統編對應的所有電子發票，
自動匯入系統並標記為「待核銷」狀態，供報帳員在手機端處理。

核心流程:
1. 查詢財政部 API 取得發票表頭
2. 比對現有 inv_num 過濾重複
3. 新發票寫入 ExpenseInvoice (source=mof_sync, status=pending_receipt)
4. 抓取每筆發票明細寫入 ExpenseInvoiceItem
5. 記錄同步批次至 EInvoiceSyncLog

Version: 1.0.0
Created: 2026-03-21
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.invoice import ExpenseInvoice, ExpenseInvoiceItem
from app.extended.models.einvoice_sync import EInvoiceSyncLog
from app.services.einvoice.mof_api_client import MofApiClient, MofApiError

logger = logging.getLogger(__name__)


class EInvoiceSyncService:
    """電子發票自動同步服務"""

    def __init__(self, db: AsyncSession, client: Optional[MofApiClient] = None):
        self.db = db
        self.client = client or MofApiClient()

    async def sync_invoices(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """執行發票同步

        Args:
            start_date: 查詢起始日期 (預設: 前 3 天)
            end_date: 查詢結束日期 (預設: 今天)

        Returns:
            同步結果統計 {total_fetched, new_imported, skipped_duplicate, ...}
        """
        if not self.client.is_configured:
            logger.warning("財政部 API 未設定 (MOF_APP_ID / MOF_API_KEY / COMPANY_BAN)")
            return {"status": "skipped", "reason": "API 未設定"}

        today = date.today()
        if end_date is None:
            end_date = today
        if start_date is None:
            start_date = today - timedelta(days=3)

        # 建立同步記錄
        sync_log = EInvoiceSyncLog(
            buyer_ban=self.client.company_ban,
            query_start=start_date,
            query_end=end_date,
            status="running",
        )
        self.db.add(sync_log)
        await self.db.flush()

        stats = {
            "sync_log_id": sync_log.id,
            "total_fetched": 0,
            "new_imported": 0,
            "skipped_duplicate": 0,
            "detail_fetched": 0,
            "errors": [],
        }

        try:
            # 1. 查詢買方發票表頭
            invoices = await self.client.query_buyer_invoices(start_date, end_date)
            stats["total_fetched"] = len(invoices)
            logger.info(f"財政部 API 回傳 {len(invoices)} 筆發票 ({start_date} ~ {end_date})")

            # 2. 過濾已存在的發票
            existing_nums = await self._get_existing_inv_nums(
                [inv["inv_num"] for inv in invoices]
            )

            for inv_data in invoices:
                inv_num = inv_data["inv_num"]

                if inv_num in existing_nums:
                    stats["skipped_duplicate"] += 1
                    continue

                try:
                    # 3. 建立 ExpenseInvoice
                    invoice = await self._create_invoice(inv_data)

                    # 4. 嘗試抓取明細
                    detail_ok = await self._fetch_and_save_details(
                        invoice, inv_data["date"]
                    )
                    if detail_ok:
                        stats["detail_fetched"] += 1

                    stats["new_imported"] += 1
                except Exception as e:
                    error_msg = f"發票 {inv_num} 匯入失敗: {e}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)

            # 更新同步記錄
            sync_log.status = "success" if not stats["errors"] else "partial"
            sync_log.total_fetched = stats["total_fetched"]
            sync_log.new_imported = stats["new_imported"]
            sync_log.skipped_duplicate = stats["skipped_duplicate"]
            sync_log.detail_fetched = stats["detail_fetched"]
            sync_log.completed_at = datetime.now()
            if stats["errors"]:
                sync_log.error_message = "\n".join(stats["errors"][:10])

            await self.db.commit()

        except MofApiError as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.now()
            await self.db.commit()
            logger.error(f"財政部 API 同步失敗: {e}")
            stats["status"] = "failed"
            stats["error"] = str(e)

        except Exception as e:
            sync_log.status = "failed"
            sync_log.error_message = str(e)
            sync_log.completed_at = datetime.now()
            await self.db.commit()
            logger.error(f"發票同步異常: {e}", exc_info=True)
            stats["status"] = "failed"
            stats["error"] = str(e)

        finally:
            await self.client.close()

        logger.info(
            f"發票同步完成: 取得={stats['total_fetched']}, "
            f"新增={stats['new_imported']}, 重複={stats['skipped_duplicate']}"
        )
        return stats

    async def _get_existing_inv_nums(self, inv_nums: list[str]) -> set[str]:
        """批量查詢已存在的發票號碼"""
        if not inv_nums:
            return set()
        result = await self.db.execute(
            select(ExpenseInvoice.inv_num).where(
                ExpenseInvoice.inv_num.in_(inv_nums)
            )
        )
        return {row[0] for row in result.fetchall()}

    async def _create_invoice(self, inv_data: dict) -> ExpenseInvoice:
        """從 API 資料建立 ExpenseInvoice"""
        invoice = ExpenseInvoice(
            inv_num=inv_data["inv_num"],
            date=inv_data["date"],
            amount=inv_data["amount"],
            tax_amount=inv_data.get("tax_amount"),
            buyer_ban=inv_data.get("buyer_ban"),
            seller_ban=inv_data.get("seller_ban"),
            source="mof_sync",
            status="pending_receipt",
            notes=f"財政部自動同步 | 賣方: {inv_data.get('seller_name', '')}",
            mof_invoice_track=inv_data["inv_num"][:2] if inv_data["inv_num"] else None,
            mof_period=inv_data.get("inv_period"),
            synced_at=datetime.now(),
        )
        self.db.add(invoice)
        await self.db.flush()
        return invoice

    async def _fetch_and_save_details(
        self, invoice: ExpenseInvoice, inv_date: date
    ) -> bool:
        """抓取發票明細並儲存"""
        try:
            items = await self.client.query_invoice_detail(
                invoice.inv_num, inv_date
            )
            for item_data in items:
                item = ExpenseInvoiceItem(
                    invoice_id=invoice.id,
                    item_name=item_data["item_name"],
                    qty=item_data["qty"],
                    unit_price=item_data["unit_price"],
                    amount=item_data["amount"],
                )
                self.db.add(item)
            return bool(items)
        except MofApiError as e:
            logger.warning(f"發票 {invoice.inv_num} 明細查詢失敗: {e}")
            return False

    async def get_pending_receipt_list(
        self,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ExpenseInvoice], int]:
        """取得待核銷清單 (status=pending_receipt)

        給報帳員手機端使用，列出所有從財政部同步但尚未上傳收據的發票。
        """
        from sqlalchemy import func as sa_func

        count_q = select(sa_func.count()).select_from(ExpenseInvoice).where(
            ExpenseInvoice.status == "pending_receipt"
        )
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            select(ExpenseInvoice)
            .where(ExpenseInvoice.status == "pending_receipt")
            .order_by(ExpenseInvoice.date.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def attach_receipt(
        self,
        invoice_id: int,
        receipt_path: str,
        case_code: Optional[str] = None,
        category: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Optional[ExpenseInvoice]:
        """上傳收據並關聯 — 報帳員完成核銷動作

        Args:
            invoice_id: 發票 ID
            receipt_path: 收據影像儲存路徑
            case_code: 案號 (可選)
            category: 費用分類 (可選)
            user_id: 經辦人 ID

        Returns:
            更新後的 ExpenseInvoice
        """
        invoice = await self.db.get(ExpenseInvoice, invoice_id)
        if not invoice:
            return None

        if invoice.status != "pending_receipt":
            raise ValueError(
                f"發票狀態為 {invoice.status}，僅 pending_receipt 可上傳收據"
            )

        invoice.receipt_image_path = receipt_path
        invoice.status = "pending"  # 轉為待審核
        invoice.user_id = user_id
        if case_code is not None:
            invoice.case_code = case_code
        if category is not None:
            invoice.category = category

        await self.db.flush()
        await self.db.refresh(invoice)
        return invoice

    async def get_sync_logs(
        self, skip: int = 0, limit: int = 10
    ) -> tuple[list[EInvoiceSyncLog], int]:
        """取得同步歷史記錄"""
        from sqlalchemy import func as sa_func

        count_q = select(sa_func.count()).select_from(EInvoiceSyncLog)
        total = (await self.db.execute(count_q)).scalar() or 0

        query = (
            select(EInvoiceSyncLog)
            .order_by(EInvoiceSyncLog.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total
