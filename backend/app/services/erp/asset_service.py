"""資產管理業務服務層"""
import logging
from typing import Optional, Tuple, List, Dict, Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models.asset import Asset, AssetLog
from app.repositories.erp.asset_repository import AssetRepository, AssetLogRepository
from app.schemas.erp.asset import (
    AssetCreateRequest,
    AssetUpdateRequest,
    AssetListRequest,
    AssetLogCreateRequest,
    AssetLogListRequest,
)
from app.services.audit_mixin import AuditableServiceMixin

logger = logging.getLogger(__name__)


class AssetService(AuditableServiceMixin):
    """資產管理業務服務"""

    AUDIT_TABLE = "assets"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AssetRepository(db)
        self.log_repo = AssetLogRepository(db)

    async def list_assets(self, params: AssetListRequest) -> Tuple[List[Asset], int]:
        """資產列表"""
        return await self.repo.list_assets(
            category=params.category,
            status=params.status,
            keyword=params.keyword,
            case_code=params.case_code,
            skip=params.skip,
            limit=params.limit,
        )

    async def get_asset(self, asset_id: int) -> Optional[Asset]:
        """取得資產詳情"""
        return await self.repo.get_asset(asset_id)

    async def create_asset(
        self, data: AssetCreateRequest, user_id: Optional[int] = None
    ) -> Asset:
        """建立資產"""
        # Check duplicate code
        if await self.repo.check_code_exists(data.asset_code):
            raise ValueError(f"資產編號 {data.asset_code} 已存在")

        asset_data = data.model_dump()
        # Map schema field to ORM column
        if "asset_model" in asset_data:
            asset_data["model"] = asset_data.pop("asset_model")
        if data.current_value is None:
            asset_data["current_value"] = data.purchase_amount
        asset_data["created_by"] = user_id

        asset = await self.repo.create_asset(asset_data)
        await self.db.commit()

        await self.audit_create(asset.id, asset_data, user_id=user_id)

        return asset

    async def update_asset(
        self, params: AssetUpdateRequest, user_id: Optional[int] = None
    ) -> Optional[Asset]:
        """更新資產"""
        update_data = params.model_dump(exclude={"id"}, exclude_none=True)
        if "asset_model" in update_data:
            update_data["model"] = update_data.pop("asset_model")
        if not update_data:
            return await self.repo.get_asset(params.id)

        asset = await self.repo.update_asset(params.id, update_data)
        if asset:
            await self.db.commit()
            await self.audit_update(params.id, update_data, user_id=user_id)
        return asset

    async def delete_asset(self, asset_id: int, user_id: Optional[int] = None) -> bool:
        """刪除資產"""
        success = await self.repo.delete_asset(asset_id)
        if success:
            await self.db.commit()
            await self.audit_delete(asset_id, user_id=user_id)
        return success

    async def get_assets_by_invoice(self, expense_invoice_id: int) -> List[Asset]:
        """取得關聯到指定發票的所有資產"""
        return await self.repo.get_assets_by_invoice(expense_invoice_id)

    async def get_asset_with_relations(self, asset_id: int) -> Optional[Dict[str, Any]]:
        """取得資產完整詳情 (含關聯發票+案件)"""
        return await self.repo.get_asset_with_invoice(asset_id)

    async def get_stats(self) -> Dict[str, Any]:
        """取得資產統計"""
        return await self.repo.get_asset_stats()

    async def export_assets_excel(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bytes:
        """匯出資產清單 Excel"""
        import io
        from openpyxl import Workbook

        items, _ = await self.repo.list_assets(
            category=category, status=status, skip=0, limit=10000
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "資產清單"

        headers = [
            "資產編號", "名稱", "類別", "品牌", "型號", "序號",
            "購入日期", "購入金額", "目前價值", "狀態", "存放位置",
            "保管人", "案件代碼", "備註",
        ]
        ws.append(headers)

        for item in items:
            ws.append([
                item.asset_code,
                item.name,
                item.category,
                item.brand,
                getattr(item, "model", None),
                item.serial_number,
                str(item.purchase_date) if item.purchase_date else "",
                float(item.purchase_amount or 0),
                float(item.current_value or 0),
                item.status,
                item.location,
                item.custodian,
                item.case_code,
                item.notes,
            ])

        # Auto-width
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    async def import_assets_excel(self, file_bytes: bytes, user_id: Optional[int] = None) -> dict:
        """匯入資產清單 Excel — 用 asset_code 做 upsert"""
        from openpyxl import load_workbook
        import io

        wb = load_workbook(io.BytesIO(file_bytes), read_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(min_row=2, values_only=True))  # Skip header

        created = 0
        updated = 0
        errors: List[Dict[str, Any]] = []

        # Expected columns: 資產編號, 名稱, 類別, 品牌, 型號, 序號, 購入日期, 購入金額, 目前價值, 狀態, 存放位置, 保管人, 案件代碼, 備註
        CATEGORY_MAP = {
            "設備": "equipment", "車輛": "vehicle", "儀器": "instrument",
            "家具": "furniture", "其他": "other",
        }
        STATUS_MAP = {
            "使用中": "in_use", "維修中": "maintenance", "閒置": "idle",
            "已報廢": "disposed", "遺失": "lost",
        }

        for idx, row in enumerate(rows, start=2):
            try:
                if not row[0] or not row[1]:  # asset_code and name required
                    continue

                asset_code = str(row[0]).strip()
                data: Dict[str, Any] = {
                    "asset_code": asset_code,
                    "name": str(row[1]).strip(),
                    "category": CATEGORY_MAP.get(str(row[2]).strip(), str(row[2]).strip()) if row[2] else "equipment",
                    "brand": str(row[3]).strip() if row[3] else None,
                    "model": str(row[4]).strip() if row[4] else None,
                    "serial_number": str(row[5]).strip() if row[5] else None,
                    "purchase_amount": float(row[7]) if row[7] else 0,
                    "current_value": float(row[8]) if row[8] else None,
                    "status": STATUS_MAP.get(str(row[9]).strip(), str(row[9]).strip()) if row[9] else "in_use",
                    "location": str(row[10]).strip() if row[10] else None,
                    "custodian": str(row[11]).strip() if row[11] else None,
                    "case_code": str(row[12]).strip() if row[12] else None,
                    "notes": str(row[13]).strip() if row[13] else None,
                }

                # Handle purchase_date
                if row[6]:
                    from datetime import date as date_type, datetime as datetime_type
                    if isinstance(row[6], (date_type, datetime_type)):
                        data["purchase_date"] = row[6] if isinstance(row[6], date_type) else row[6].date()
                    else:
                        try:
                            data["purchase_date"] = datetime_type.strptime(str(row[6]).strip(), "%Y-%m-%d").date()
                        except ValueError:
                            pass

                # Upsert by asset_code
                existing = await self.repo.get_by_code(asset_code)
                if existing:
                    update_data = {k: v for k, v in data.items() if k != "asset_code" and v is not None}
                    await self.repo.update_asset(existing.id, update_data)
                    updated += 1
                else:
                    data["created_by"] = user_id
                    if data.get("current_value") is None:
                        data["current_value"] = data.get("purchase_amount", 0)
                    await self.repo.create_asset(data)
                    created += 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e)})

        await self.db.commit()
        wb.close()

        return {
            "total_rows": len(rows),
            "created": created,
            "updated": updated,
            "errors": errors,
        }

    async def batch_inventory(
        self,
        asset_ids: List[int],
        operator: str,
        notes: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> dict:
        """批次盤點 — 為多個資產建立 inspect 行為紀錄"""
        from datetime import date as date_type

        today = date_type.today()
        created = 0
        not_found: List[int] = []

        for asset_id in asset_ids:
            asset = await self.repo.get_asset(asset_id)
            if not asset:
                not_found.append(asset_id)
                continue

            log_data = {
                "asset_id": asset_id,
                "action": "inspect",
                "action_date": today,
                "description": f"盤點確認 — {asset.name}",
                "operator": operator,
                "notes": notes,
                "created_by": user_id,
            }
            await self.log_repo.create_asset_log(log_data)
            created += 1

        await self.db.commit()
        return {
            "total": len(asset_ids),
            "inspected": created,
            "not_found": not_found,
            "date": str(today),
            "operator": operator,
        }

    async def export_inventory_report(self) -> bytes:
        """匯出盤點報表 Excel — 所有資產 + 最近盤點日期"""
        import io
        from openpyxl import Workbook
        from sqlalchemy import select, func

        # Get all assets
        items, _ = await self.repo.list_assets(skip=0, limit=10000)

        # Get latest inspect log per asset
        latest_inspect = (
            select(
                AssetLog.asset_id,
                func.max(AssetLog.action_date).label("last_inspect"),
            )
            .where(AssetLog.action == "inspect")
            .group_by(AssetLog.asset_id)
        ).subquery()

        result = await self.db.execute(
            select(latest_inspect.c.asset_id, latest_inspect.c.last_inspect)
        )
        inspect_map = {r.asset_id: r.last_inspect for r in result.all()}

        wb = Workbook()
        ws = wb.active
        ws.title = "盤點報表"

        headers = [
            "資產編號", "名稱", "類別", "品牌", "型號",
            "狀態", "存放位置", "保管人", "購入金額", "最近盤點日",
        ]
        ws.append(headers)

        for item in items:
            last = inspect_map.get(item.id)
            ws.append([
                item.asset_code,
                item.name,
                item.category,
                item.brand,
                getattr(item, "model", None),
                item.status,
                item.location,
                item.custodian,
                float(item.purchase_amount or 0),
                str(last) if last else "未盤點",
            ])

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.read()

    def generate_import_template(self) -> bytes:
        """產生資產匯入範本 Excel"""
        import io
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "資產匯入範本"

        headers = [
            "資產編號", "名稱", "類別", "品牌", "型號", "序號",
            "購入日期", "購入金額", "目前價值", "狀態", "存放位置",
            "保管人", "案件代碼", "備註",
        ]

        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = header_font

        # Example rows
        examples = [
            ["AST-2026-001", "全測站 ES-105", "儀器", "Topcon", "ES-105", "SN20250001",
             "2025-06-15", 280000, 280000, "使用中", "公司倉庫", "王技師", "", ""],
            ["AST-2026-002", "GPS RTK", "儀器", "Trimble", "R12i", "SN20250002",
             "2025-01-10", 450000, 400000, "使用中", "工地A", "李技師", "B114-B001", ""],
        ]
        for row_data in examples:
            ws.append(row_data)

        # Notes sheet
        ws2 = wb.create_sheet("說明")
        ws2.append(["欄位", "說明", "必填", "可選值"])
        notes = [
            ["資產編號", "唯一識別碼", "是", "自訂格式"],
            ["名稱", "資產名稱", "是", ""],
            ["類別", "設備類型", "否", "設備/車輛/儀器/家具/其他"],
            ["狀態", "使用狀態", "否", "使用中/維修中/閒置/已報廢/遺失"],
            ["購入日期", "格式 YYYY-MM-DD", "否", ""],
            ["購入金額", "數字", "否", ""],
        ]
        for n in notes:
            ws2.append(n)

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

        buffer = io.BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    async def list_logs(self, params: AssetLogListRequest) -> Tuple[List[AssetLog], int]:
        """取得資產行為紀錄列表"""
        return await self.log_repo.list_asset_logs(
            asset_id=params.asset_id,
            action=params.action,
            skip=params.skip,
            limit=params.limit,
        )

    async def create_log(
        self, data: AssetLogCreateRequest, user_id: Optional[int] = None
    ) -> AssetLog:
        """建立行為紀錄"""
        # Verify asset exists
        asset = await self.repo.get_asset(data.asset_id)
        if not asset:
            raise ValueError(f"資產 ID {data.asset_id} 不存在")

        log_data = data.model_dump()
        log_data["created_by"] = user_id

        # Side effects based on action
        if data.action == "transfer" and data.to_location:
            await self.repo.update_asset(data.asset_id, {"location": data.to_location})
        elif data.action == "dispose":
            await self.repo.update_asset(data.asset_id, {"status": "disposed"})
        elif data.action == "repair":
            # Only set maintenance if currently in_use
            if asset.status == "in_use":
                await self.repo.update_asset(data.asset_id, {"status": "maintenance"})

        log_entry = await self.log_repo.create_asset_log(log_data)
        await self.db.commit()
        return log_entry
