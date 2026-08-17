"""
安全網站管理模組 - 配置管理端點

包含: /config/action

使用 ConfigurationRepository 進行資料存取，遵循 Repository Pattern。
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.repositories.configuration_repository import ConfigurationRepository
from app.schemas.site_management import SiteConfigCreate, SiteConfigResponse
from app.schemas.secure import SecureRequest, SecureResponse

from .common import validate_csrf_token, generate_csrf_token

logger = logging.getLogger(__name__)

router = APIRouter()


def get_config_repository(
    db: AsyncSession = Depends(get_async_db),
) -> ConfigurationRepository:
    """依賴注入：取得 ConfigurationRepository 實例"""
    return ConfigurationRepository(db)


@router.post("/config/action", response_model=SecureResponse)
async def config_action(
    request: SecureRequest,
    config_repo: ConfigurationRepository = Depends(get_config_repository),
):
    """統一的配置操作接口"""

    if not await validate_csrf_token(request.csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")

    try:
        action = request.action.lower()
        data = request.data or {}

        if action == "list":
            configs = await config_repo.get_configs_filtered(
                search=data.get("search"),
                category=data.get("category"),
            )

            config_list = [
                SiteConfigResponse.model_validate(config).model_dump()
                for config in configs
            ]

            return SecureResponse(
                success=True,
                message="Configurations retrieved successfully",
                data={
                    "configs": config_list,
                    "total": len(config_list),
                    "skip": 0,
                    "limit": 100,
                },
                csrf_token=await generate_csrf_token(),
            )

        elif action == "create":
            config_data = SiteConfigCreate(**data)

            existing = await config_repo.get_by_key(config_data.key)
            if existing:
                raise HTTPException(
                    status_code=400, detail="Configuration key already exists"
                )

            new_config = await config_repo.create(config_data.model_dump())

            return SecureResponse(
                success=True,
                message="Configuration created successfully",
                data={
                    "config": SiteConfigResponse.model_validate(new_config).model_dump()
                },
                csrf_token=await generate_csrf_token(),
            )

        elif action == "update":
            key = data.get("key")
            if not key:
                raise HTTPException(
                    status_code=400, detail="Configuration key is required"
                )

            config = await config_repo.get_by_key(key)
            if not config:
                raise HTTPException(
                    status_code=404, detail="Configuration not found"
                )

            if getattr(config, "is_system", False) and "key" in data:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot modify system configuration key",
                )

            update_data = {
                k: v for k, v in data.items() if k != "key" and v is not None
            }
            for attr_name, value in update_data.items():
                setattr(config, attr_name, value)

            config.updated_at = datetime.utcnow()
            await config_repo.db.commit()
            await config_repo.db.refresh(config)

            # 2026-08-18：有行程內快取的設定值，更新後要讓它立即失效。
            # 不做的話 owner 改完比率會看到舊的毛利數字（TTL 60 秒），
            # 而「改了設定但畫面沒變」會讓人以為沒存成功而重複操作。
            #
            # 用明列而非「掃描所有有快取的設定」：目前只有這一個，
            # 而為一個項目建一套註冊機制是把簡單的事變複雜。
            # 未來多起來再抽 —— 屆時這個 if 會很明顯地不夠用。
            if key == "erp_company_profit_rate":
                from app.services.erp.company_profit import invalidate_cache
                invalidate_cache()

            return SecureResponse(
                success=True,
                message="Configuration updated successfully",
                data={
                    "config": SiteConfigResponse.model_validate(config).model_dump()
                },
                csrf_token=await generate_csrf_token(),
            )

        elif action == "delete":
            key = data.get("key")
            if not key:
                raise HTTPException(
                    status_code=400, detail="Configuration key is required"
                )

            config = await config_repo.get_by_key(key)
            if not config:
                raise HTTPException(
                    status_code=404, detail="Configuration not found"
                )

            if getattr(config, "is_system", False):
                raise HTTPException(
                    status_code=403,
                    detail="Cannot delete system configuration",
                )

            await config_repo.delete_by_key(key)

            return SecureResponse(
                success=True,
                message="Configuration deleted successfully",
                csrf_token=await generate_csrf_token(),
            )

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown action: {action}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"設定操作失敗: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="操作失敗，請稍後再試"
        )
