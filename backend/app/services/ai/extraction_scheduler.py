"""
NER 實體提取排程器

定期掃描未提取實體的公文，自動執行 NER 提取與知識圖譜入圖。
首次啟動時將結構化實體（機關、專案、廠商）註冊為 CanonicalEntity。

流程:
1. 首次啟動 → 註冊結構化實體 (GovernmentAgency, ContractProject, PartnerVendor)
2. 每次 tick → 掃描待提取公文 → NER 提取 → 入圖

Version: 1.0.0
Created: 2026-02-25
"""

import asyncio
import logging
import os
from typing import Optional

import httpx
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.extended.models import (
    GovernmentAgency,
    ContractProject,
    PartnerVendor,
    OfficialDocument,
    CanonicalEntity,
)

logger = logging.getLogger(__name__)

# 配置常數
DEFAULT_INTERVAL_MINUTES = 60
BATCH_LIMIT = 50
COMMIT_EVERY = 10
INTER_DOC_SLEEP_OLLAMA = 0.5   # Ollama 可用：本地模型，快速處理
INTER_DOC_SLEEP_GROQ = 2.5     # Ollama 不可用：透過 Groq 限速保護
MAX_CONSECUTIVE_FAILURES = 30   # 斷路器閾值


class ExtractionScheduler:
    """NER 實體提取排程器"""

    def __init__(self):
        self.is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self.interval_seconds: int = (
            int(os.getenv("NER_SCHEDULER_INTERVAL_MINUTES", str(DEFAULT_INTERVAL_MINUTES))) * 60
        )
        self._structured_registered: bool = False
        self._last_run_stats: Optional[dict] = None

    async def start(self):
        """啟動排程器"""
        if self.is_running:
            logger.warning("NER 實體提取排程器已經在運行中")
            return

        self.is_running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"NER 實體提取排程器已啟動，間隔: {self.interval_seconds // 60} 分鐘"
        )

    async def stop(self):
        """停止排程器"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("NER 實體提取排程器已停止")

    async def _run_loop(self):
        """排程器主迴圈"""
        logger.info("NER 實體提取排程器開始運行")

        # 首次啟動：註冊結構化實體
        await self._safe_register_structured_entities()

        while self.is_running and not self._stop_event.is_set():
            try:
                await self._process_batch()
            except asyncio.CancelledError:
                logger.info("NER 實體提取排程器收到取消信號")
                break
            except Exception as e:
                logger.error(f"NER 實體提取排程器運行錯誤: {e}", exc_info=True)

            # 等待下次執行，支持提前取消
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.interval_seconds,
                )
                # stop_event 被設定 → 退出迴圈
                break
            except asyncio.TimeoutError:
                # 正常超時 → 繼續下一輪
                pass
            except asyncio.CancelledError:
                break

        logger.info("NER 實體提取排程器停止運行")

    async def _safe_register_structured_entities(self):
        """安全地執行結構化實體註冊（不會因失敗而中斷排程器）"""
        if self._structured_registered:
            return

        try:
            await self._register_structured_entities()
            self._structured_registered = True
        except Exception as e:
            logger.warning(
                f"結構化實體註冊失敗（將在下次啟動時重試）: {e}",
                exc_info=True,
            )

    async def _register_structured_entities(self):
        """
        將系統中的結構化實體（機關、專案、廠商）註冊為 CanonicalEntity。

        使用 CanonicalEntityService.resolve_entity() 進行去重處理，
        已存在的實體不會重複建立。僅在首次啟動時執行。
        """
        from app.services.ai.canonical_entity_service import CanonicalEntityService

        db: Optional[AsyncSession] = None
        try:
            db = AsyncSessionLocal()
            entity_service = CanonicalEntityService(db)

            # 檢查是否已有正規化實體（若已有則跳過，避免重複工作）
            existing_count = await db.scalar(
                select(sa_func.count()).select_from(CanonicalEntity)
            ) or 0

            if existing_count > 0:
                logger.info(
                    f"已存在 {existing_count} 個正規化實體，跳過結構化實體註冊"
                )
                self._structured_registered = True
                return

            # 批次收集所有結構化實體（v1.1.0: 使用 resolve_entities_batch）
            all_entities: list[tuple[str, str]] = []

            # 1. GovernmentAgency → org
            try:
                agency_result = await db.execute(
                    select(GovernmentAgency.agency_name)
                    .where(GovernmentAgency.agency_name.isnot(None))
                    .where(GovernmentAgency.agency_name != "")
                )
                agency_names = [row[0] for row in agency_result.all()]
                all_entities.extend((name, "org") for name in agency_names)
                logger.info(f"載入 {len(agency_names)} 個機關待註冊")
            except Exception as e:
                logger.warning(f"查詢機關表失敗: {e}")

            # 2. ContractProject → project
            try:
                project_result = await db.execute(
                    select(ContractProject.project_name)
                    .where(ContractProject.project_name.isnot(None))
                    .where(ContractProject.project_name != "")
                )
                project_names = [row[0] for row in project_result.all()]
                all_entities.extend((name, "project") for name in project_names)
                logger.info(f"載入 {len(project_names)} 個專案待註冊")
            except Exception as e:
                logger.warning(f"查詢專案表失敗: {e}")

            # 3. PartnerVendor → org
            try:
                vendor_result = await db.execute(
                    select(PartnerVendor.vendor_name)
                    .where(PartnerVendor.vendor_name.isnot(None))
                    .where(PartnerVendor.vendor_name != "")
                )
                vendor_names = [row[0] for row in vendor_result.all()]
                all_entities.extend((name, "org") for name in vendor_names)
                logger.info(f"載入 {len(vendor_names)} 個廠商待註冊")
            except Exception as e:
                logger.warning(f"查詢廠商表失敗: {e}")

            # 批次解析（1 次精確匹配 + 最少 flush）
            if all_entities:
                resolved = await entity_service.resolve_entities_batch(
                    all_entities, source="structured",
                )
                registered = len(resolved)
            else:
                registered = 0

            await db.commit()
            logger.info(f"結構化實體註冊完成，共處理 {registered} 筆")

        except Exception as e:
            logger.error(f"結構化實體註冊過程發生錯誤: {e}", exc_info=True)
            if db:
                await db.rollback()
            raise
        finally:
            if db:
                await db.close()

    async def _check_ollama_available(self) -> bool:
        """檢查 Ollama 是否可用（用於決定批次處理間隔）"""
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def _process_batch(self):
        """
        處理一批待提取的公文。

        流程:
        0. 檢查 Ollama 可用性，決定文檔間休眠時間
        1. 取得已提取 ID 集合（排除用）
        2. 查詢待提取公文（limit BATCH_LIMIT）
        3. 逐筆 NER 提取 + 入圖
        4. 每 COMMIT_EVERY 筆 commit
        5. 斷路器：連續失敗達閾值時停止
        """
        from app.services.ai.entity_extraction_service import (
            extract_entities_for_document,
            get_extracted_document_ids,
        )
        from app.services.ai.graph_ingestion_pipeline import GraphIngestionPipeline

        # Ollama 可用性檢查 → 決定文檔間休眠時間
        ollama_available = await self._check_ollama_available()
        if ollama_available:
            inter_doc_sleep = INTER_DOC_SLEEP_OLLAMA
            logger.info(
                "NER 排程器: Ollama 可用，使用快速間隔 (%.1fs)", inter_doc_sleep
            )
        else:
            inter_doc_sleep = INTER_DOC_SLEEP_GROQ
            logger.warning(
                "NER 排程器: Ollama 不可用，降級至 Groq 限速保護間隔 (%.1fs)",
                inter_doc_sleep,
            )

        db: Optional[AsyncSession] = None
        try:
            db = AsyncSessionLocal()

            # 取得已提取的公文 ID 集合
            extracted_ids = await get_extracted_document_ids(db)

            # 查詢待提取公文 ID
            all_doc_result = await db.execute(
                select(OfficialDocument.id)
                .where(OfficialDocument.id.notin_(extracted_ids) if extracted_ids else True)
                .order_by(OfficialDocument.id.desc())
                .limit(BATCH_LIMIT)
            )
            pending_ids = [row[0] for row in all_doc_result.all()]

            if not pending_ids:
                logger.debug("無待提取公文，本次跳過")
                return

            logger.info(f"發現 {len(pending_ids)} 筆待提取公文，開始處理...")

            success_count = 0
            skip_count = 0
            error_count = 0
            consecutive_failures = 0

            for i, doc_id in enumerate(pending_ids):
                # 斷路器：連續失敗達閾值時停止
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    logger.error(
                        f"連續失敗 {consecutive_failures} 次，觸發斷路器，停止本批次"
                    )
                    break

                # 檢查排程器是否仍在運行
                if not self.is_running or self._stop_event.is_set():
                    logger.info("排程器已停止，中斷批次處理")
                    break

                try:
                    # NER 提取
                    result = await extract_entities_for_document(
                        db, doc_id, commit=False
                    )

                    if result.get("skipped"):
                        skip_count += 1
                        consecutive_failures = 0
                    elif result.get("error"):
                        error_count += 1
                        consecutive_failures += 1
                        logger.warning(
                            f"公文 #{doc_id} 提取失敗: {result.get('error')}"
                        )
                    else:
                        # 提取成功 → 入圖
                        try:
                            pipeline = GraphIngestionPipeline(db)
                            await pipeline.ingest_document(doc_id)
                        except Exception as ingest_err:
                            logger.warning(
                                f"公文 #{doc_id} 入圖失敗（提取已完成）: {ingest_err}"
                            )

                        success_count += 1
                        consecutive_failures = 0

                except Exception as e:
                    error_count += 1
                    consecutive_failures += 1
                    logger.error(
                        f"公文 #{doc_id} 處理失敗: {e}", exc_info=True
                    )

                # 每 COMMIT_EVERY 筆 commit
                if (i + 1) % COMMIT_EVERY == 0:
                    try:
                        await db.commit()
                    except Exception as commit_err:
                        logger.error(f"批次 commit 失敗: {commit_err}")
                        try:
                            await db.rollback()
                        except Exception:
                            pass

                # 文檔間休眠（避免過度佔用資源）
                if i < len(pending_ids) - 1:
                    await asyncio.sleep(inter_doc_sleep)

            # 最終 commit
            try:
                await db.commit()
            except Exception as commit_err:
                logger.error(f"最終 commit 失敗: {commit_err}")
                try:
                    await db.rollback()
                except Exception:
                    pass

            self._last_run_stats = {
                "total": len(pending_ids),
                "success": success_count,
                "skipped": skip_count,
                "errors": error_count,
            }

            logger.info(
                f"NER 批次處理完成: "
                f"{success_count} 成功, {skip_count} 跳過, {error_count} 錯誤 "
                f"(共 {len(pending_ids)} 筆)"
            )

        except Exception as e:
            logger.error(f"NER 批次處理發生錯誤: {e}", exc_info=True)
            if db:
                try:
                    await db.rollback()
                except Exception:
                    pass
        finally:
            if db:
                await db.close()

    def get_status(self) -> dict:
        """取得排程器狀態"""
        return {
            "is_running": self.is_running,
            "interval_minutes": self.interval_seconds // 60,
            "structured_registered": self._structured_registered,
            "last_run_stats": self._last_run_stats,
            "task_active": (
                self._task is not None and not self._task.done()
                if self._task
                else False
            ),
        }


# 全域排程器實例
_scheduler: Optional[ExtractionScheduler] = None


async def start_extraction_scheduler():
    """啟動 NER 實體提取排程器"""
    global _scheduler
    _scheduler = ExtractionScheduler()
    await _scheduler.start()


async def stop_extraction_scheduler():
    """停止 NER 實體提取排程器"""
    global _scheduler
    if _scheduler is not None:
        await _scheduler.stop()


def get_extraction_scheduler() -> Optional[ExtractionScheduler]:
    """取得 NER 實體提取排程器實例"""
    return _scheduler
