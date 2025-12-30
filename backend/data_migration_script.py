#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
資料遷移腳本 - 將現有資料對應到新的外鍵關聯
執行此腳本前請先執行 Alembic 遷移
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, text
from app.core.config import settings
from app.extended.models import OfficialDocument, ContractProject, GovernmentAgency

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 創建非同步引擎
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def migrate_contract_projects():
    """
    遷移承攬案件關聯
    根據 documents.contract_case 欄位匹配 contract_projects.project_name
    """
    async with AsyncSessionLocal() as session:
        logger.info("開始遷移承攬案件關聯...")

        # 查詢所有有 contract_case 但沒有 contract_project_id 的公文
        documents_query = select(OfficialDocument).where(
            OfficialDocument.contract_case.isnot(None),
            OfficialDocument.contract_case != '',
            OfficialDocument.contract_project_id.is_(None)
        )
        result = await session.execute(documents_query)
        documents = result.scalars().all()

        logger.info(f"找到 {len(documents)} 筆需要遷移的公文")

        updated_count = 0
        not_found_count = 0

        for document in documents:
            # 嘗試匹配專案名稱
            project_query = select(ContractProject).where(
                ContractProject.project_name.ilike(f"%{document.contract_case}%")
            ).limit(1)
            project_result = await session.execute(project_query)
            project = project_result.scalars().first()

            if project:
                document.contract_project_id = project.id
                updated_count += 1
                logger.debug(f"公文 {document.id} 關聯到專案 {project.id}: {project.project_name}")
            else:
                not_found_count += 1
                logger.warning(f"找不到匹配的專案: {document.contract_case}")

        await session.commit()
        logger.info(f"承攬案件關聯遷移完成: 更新 {updated_count} 筆, 未找到匹配 {not_found_count} 筆")

async def migrate_government_agencies():
    """
    遷移政府機關關聯
    根據 documents.sender 和 documents.receiver 欄位匹配 government_agencies.agency_name
    """
    async with AsyncSessionLocal() as session:
        logger.info("開始遷移政府機關關聯...")

        # 查詢所有公文
        documents_query = select(OfficialDocument)
        result = await session.execute(documents_query)
        documents = result.scalars().all()

        logger.info(f"開始處理 {len(documents)} 筆公文的機關關聯")

        sender_updated = 0
        receiver_updated = 0
        sender_not_found = 0
        receiver_not_found = 0

        for document in documents:
            # 處理發文機關
            if document.sender and not document.sender_agency_id:
                agency_query = select(GovernmentAgency).where(
                    GovernmentAgency.agency_name.ilike(f"%{document.sender}%")
                ).limit(1)
                agency_result = await session.execute(agency_query)
                agency = agency_result.scalars().first()

                if agency:
                    document.sender_agency_id = agency.id
                    sender_updated += 1
                    logger.debug(f"公文 {document.id} 發文機關關聯到 {agency.agency_name}")
                else:
                    sender_not_found += 1
                    logger.debug(f"找不到匹配的發文機關: {document.sender}")

            # 處理受文機關
            if document.receiver and not document.receiver_agency_id:
                agency_query = select(GovernmentAgency).where(
                    GovernmentAgency.agency_name.ilike(f"%{document.receiver}%")
                ).limit(1)
                agency_result = await session.execute(agency_query)
                agency = agency_result.scalars().first()

                if agency:
                    document.receiver_agency_id = agency.id
                    receiver_updated += 1
                    logger.debug(f"公文 {document.id} 受文機關關聯到 {agency.agency_name}")
                else:
                    receiver_not_found += 1
                    logger.debug(f"找不到匹配的受文機關: {document.receiver}")

        await session.commit()
        logger.info(f"政府機關關聯遷移完成:")
        logger.info(f"  發文機關: 更新 {sender_updated} 筆, 未找到 {sender_not_found} 筆")
        logger.info(f"  受文機關: 更新 {receiver_updated} 筆, 未找到 {receiver_not_found} 筆")

async def create_missing_agencies():
    """
    創建缺失的政府機關記錄
    從公文資料中提取獨特的發文/受文單位，創建對應的機關記錄
    """
    async with AsyncSessionLocal() as session:
        logger.info("開始創建缺失的政府機關記錄...")

        # 查詢所有獨特的發文單位
        sender_query = text("""
            SELECT DISTINCT sender
            FROM documents
            WHERE sender IS NOT NULL
                AND sender != ''
                AND sender_agency_id IS NULL
        """)
        sender_result = await session.execute(sender_query)
        senders = [row[0] for row in sender_result]

        # 查詢所有獨特的受文單位
        receiver_query = text("""
            SELECT DISTINCT receiver
            FROM documents
            WHERE receiver IS NOT NULL
                AND receiver != ''
                AND receiver_agency_id IS NULL
        """)
        receiver_result = await session.execute(receiver_query)
        receivers = [row[0] for row in receiver_result]

        # 合併並去重
        unique_agencies = list(set(senders + receivers))
        logger.info(f"找到 {len(unique_agencies)} 個獨特的機關名稱")

        created_count = 0
        for agency_name in unique_agencies:
            # 檢查是否已存在
            existing_query = select(GovernmentAgency).where(
                GovernmentAgency.agency_name == agency_name
            )
            existing_result = await session.execute(existing_query)
            existing = existing_result.scalars().first()

            if not existing:
                # 創建新的機關記錄
                new_agency = GovernmentAgency(
                    agency_name=agency_name,
                    agency_type="其他"  # 預設類型
                )
                session.add(new_agency)
                created_count += 1
                logger.debug(f"創建新機關: {agency_name}")

        await session.commit()
        logger.info(f"創建了 {created_count} 個新的政府機關記錄")

async def verify_migration():
    """
    驗證遷移結果
    """
    async with AsyncSessionLocal() as session:
        logger.info("開始驗證遷移結果...")

        # 統計關聯情況
        total_docs_query = select(OfficialDocument)
        total_result = await session.execute(total_docs_query)
        total_docs = len(total_result.scalars().all())

        # 有承攬案件關聯的公文數量
        contract_linked_query = select(OfficialDocument).where(
            OfficialDocument.contract_project_id.isnot(None)
        )
        contract_result = await session.execute(contract_linked_query)
        contract_linked = len(contract_result.scalars().all())

        # 有發文機關關聯的公文數量
        sender_linked_query = select(OfficialDocument).where(
            OfficialDocument.sender_agency_id.isnot(None)
        )
        sender_result = await session.execute(sender_linked_query)
        sender_linked = len(sender_result.scalars().all())

        # 有受文機關關聯的公文數量
        receiver_linked_query = select(OfficialDocument).where(
            OfficialDocument.receiver_agency_id.isnot(None)
        )
        receiver_result = await session.execute(receiver_linked_query)
        receiver_linked = len(receiver_result.scalars().all())

        logger.info("=== 遷移結果統計 ===")
        logger.info(f"總公文數量: {total_docs}")
        logger.info(f"有承攬案件關聯: {contract_linked} ({contract_linked/total_docs*100:.1f}%)")
        logger.info(f"有發文機關關聯: {sender_linked} ({sender_linked/total_docs*100:.1f}%)")
        logger.info(f"有受文機關關聯: {receiver_linked} ({receiver_linked/total_docs*100:.1f}%)")

async def main():
    """
    主要遷移函數
    """
    logger.info("=== 開始資料遷移 ===")

    try:
        # 1. 創建缺失的政府機關
        await create_missing_agencies()

        # 2. 遷移承攬案件關聯
        await migrate_contract_projects()

        # 3. 遷移政府機關關聯
        await migrate_government_agencies()

        # 4. 驗證遷移結果
        await verify_migration()

        logger.info("=== 資料遷移完成 ===")

    except Exception as e:
        logger.error(f"資料遷移失敗: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())