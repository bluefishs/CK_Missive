"""資產管理業務服務層"""
import logging
from typing import Optional, Tuple, List, Dict, Any

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
        """建立資產 (asset_code 為空時自動生成 + 併發 retry)"""
        from datetime import date as _date
        from app.services.case_code_service import CaseCodeService
        from app.services.coding_helpers import retry_on_code_conflict

        user_provided_code = bool(data.asset_code)

        # 使用者手動輸入代碼 → 維持原邏輯 (先檢查，避免覆寫使用者意圖)
        if user_provided_code:
            if await self.repo.check_code_exists(data.asset_code):
                raise ValueError(f"資產編號 {data.asset_code} 已存在")

        async def _create_op() -> Asset:
            if not user_provided_code:
                code_svc = CaseCodeService(self.db)
                data.asset_code = await code_svc.generate_asset_code(
                    year=_date.today().year,
                    category=data.category or "equipment",
                )

            asset_data = data.model_dump()
            if "asset_model" in asset_data:
                asset_data["model"] = asset_data.pop("asset_model")
            if data.current_value is None:
                asset_data["current_value"] = data.purchase_amount
            asset_data["created_by"] = user_id

            asset = await self.repo.create_asset(asset_data)
            await self.audit_create(asset.id, asset_data, user_id=user_id)
            return asset

        asset = await retry_on_code_conflict(
            self.db, _create_op, unique_field="asset_code"
        )
        await self.db.commit()
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

    # =========================================================================
    # IO 委派 (Excel 匯出入 — 委派至 asset_service_io.py)
    # =========================================================================

    async def export_assets_excel(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bytes:
        """匯出資產清單 Excel (委派至 AssetIOService)"""
        from app.services.erp.asset_service_io import AssetIOService
        return await AssetIOService(self.db).export_assets_excel(category, status)

    async def import_assets_excel(self, file_bytes: bytes, user_id: Optional[int] = None) -> dict:
        """匯入資產清單 Excel (委派至 AssetIOService)"""
        from app.services.erp.asset_service_io import AssetIOService
        return await AssetIOService(self.db).import_assets_excel(file_bytes, user_id)

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
        """匯出盤點報表 Excel (委派至 AssetIOService)"""
        from app.services.erp.asset_service_io import AssetIOService
        return await AssetIOService(self.db).export_inventory_report()

    def generate_import_template(self) -> bytes:
        """產生資產匯入範本 Excel (委派至 AssetIOService)"""
        from app.services.erp.asset_service_io import AssetIOService
        return AssetIOService.generate_import_template()

    async def assess_asset_condition(
        self, image_bytes: bytes, asset_name: str = ""
    ) -> dict:
        """Use Gemma 4 vision to assess asset condition from photo.

        Returns structured assessment with condition, description,
        maintenance flag, and estimated remaining life.
        Falls back to a generic result if vision is unavailable.
        """
        try:
            from app.core.ai_connector import get_ai_connector
            ai = get_ai_connector()
            prompt = (
                f"分析此資產照片{f' ({asset_name})' if asset_name else ''}。\n"
                "評估：1.外觀狀態 2.預估使用年限 3.是否需要維修\n"
                "以 JSON 回覆：\n"
                '{"condition": "良好/一般/需維修/報廢", '
                '"description": "描述", "maintenance_needed": true/false, '
                '"estimated_remaining_life": "年數"}'
            )
            result = await ai.vision_completion(prompt, image_bytes, max_tokens=256)
            from app.services.ai.core.agent_utils import parse_json_safe
            parsed = parse_json_safe(result)
            if parsed and parsed.get("condition"):
                return parsed
            return {"condition": "unknown", "description": result[:200]}
        except Exception as e:
            logger.debug("Gemma 4 vision asset assessment failed: %s", e)
            return {
                "condition": "unknown",
                "description": "無法透過 AI 視覺評估資產狀態",
                "maintenance_needed": False,
                "estimated_remaining_life": None,
            }

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
