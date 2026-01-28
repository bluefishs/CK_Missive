"""
安全網站管理模組 - 配置管理端點

包含: /config/action
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_async_db
from app.extended.models import SiteConfiguration
from app.schemas.site_management import SiteConfigCreate, SiteConfigResponse
from app.schemas.secure import SecureRequest, SecureResponse

from .common import validate_csrf_token, generate_csrf_token

router = APIRouter()


@router.post("/config/action", response_model=SecureResponse)
async def config_action(
    request: SecureRequest,
    session: AsyncSession = Depends(get_async_db)
):
    """統一的配置操作接口"""

    if not validate_csrf_token(request.csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or expired CSRF token")

    try:
        action = request.action.lower()
        data = request.data or {}

        if action == "list":
            filters = []

            search = data.get("search")
            if search:
                filters.append(
                    or_(
                        SiteConfiguration.key.ilike(f"%{search}%"),
                        SiteConfiguration.description.ilike(f"%{search}%")
                    )
                )

            category = data.get("category")
            if category:
                filters.append(SiteConfiguration.category == category)

            query = select(SiteConfiguration)
            if filters:
                query = query.filter(and_(*filters))

            query = query.order_by(SiteConfiguration.category, SiteConfiguration.key)

            result = await session.execute(query)
            configs = result.scalars().all()

            config_list = [SiteConfigResponse.model_validate(config).model_dump() for config in configs]

            return SecureResponse(
                success=True,
                message="Configurations retrieved successfully",
                data={
                    "configs": config_list,
                    "total": len(config_list),
                    "skip": 0,
                    "limit": 100
                },
                csrf_token=generate_csrf_token()
            )

        elif action == "create":
            config_data = SiteConfigCreate(**data)

            existing_result = await session.execute(
                select(SiteConfiguration).filter(
                    SiteConfiguration.key == config_data.key
                )
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Configuration key already exists")

            new_config = SiteConfiguration(**config_data.model_dump())
            session.add(new_config)
            await session.commit()
            await session.refresh(new_config)

            return SecureResponse(
                success=True,
                message="Configuration created successfully",
                data={"config": SiteConfigResponse.model_validate(new_config).model_dump()},
                csrf_token=generate_csrf_token()
            )

        elif action == "update":
            key = data.get("key")
            if not key:
                raise HTTPException(status_code=400, detail="Configuration key is required")

            result = await session.execute(
                select(SiteConfiguration).filter(SiteConfiguration.key == key)
            )
            config = result.scalar_one_or_none()
            if not config:
                raise HTTPException(status_code=404, detail="Configuration not found")

            if config.is_system and "key" in data:
                raise HTTPException(status_code=403, detail="Cannot modify system configuration key")

            update_data = {k: v for k, v in data.items() if k != "key" and v is not None}
            for key, value in update_data.items():
                setattr(config, key, value)

            config.updated_at = datetime.utcnow()
            await session.commit()
            await session.refresh(config)

            return SecureResponse(
                success=True,
                message="Configuration updated successfully",
                data={"config": SiteConfigResponse.model_validate(config).model_dump()},
                csrf_token=generate_csrf_token()
            )

        elif action == "delete":
            key = data.get("key")
            if not key:
                raise HTTPException(status_code=400, detail="Configuration key is required")

            result = await session.execute(
                select(SiteConfiguration).filter(SiteConfiguration.key == key)
            )
            config = result.scalar_one_or_none()
            if not config:
                raise HTTPException(status_code=404, detail="Configuration not found")

            if config.is_system:
                raise HTTPException(status_code=403, detail="Cannot delete system configuration")

            await session.delete(config)
            await session.commit()

            return SecureResponse(
                success=True,
                message="Configuration deleted successfully",
                csrf_token=generate_csrf_token()
            )

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
