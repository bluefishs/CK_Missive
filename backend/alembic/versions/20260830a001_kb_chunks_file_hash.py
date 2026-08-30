"""kb_chunks 加 file_hash —— 讓向量庫可以增量同步而不是每次砍掉重建

Revision ID: 20260830a001
Revises: 20260829b002
Create Date: 2026-08-30

## 為什麼

`KBEmbeddingService.scan_and_embed()` 是**全庫重建**：
`delete(KBChunk)` 清空 → 重新分段 → 重新向量化 → 寫回。
現況 **289 個檔、2,343 段**，每次都整批重算。

而它**沒有任何排程在跑**（`scheduler.py` 的註解自己就寫著
「kb_chunks 由手動 /embed 維護」）⇒ docs/ 改了之後向量庫不會跟上，
RAG 檢索到的是舊內容，而畫面上看不出來。

要把它排程化，就不能是「每天砍掉重建」：
- 開銷：2,343 段全部重新向量化
- 風險：批次 embedding 的例外目前是被 `logger.warning` 吞掉的
  ⇒ 那批 chunk 以 `embedding=None` 寫入，**靜默降級到下次全重建才修**

⇒ 先有比對鍵才有增量。`file_hash` 存來源檔的 MD5：
雜湊相同就整檔跳過（連分段都不必做），不同才刪那一個 file_path 重建。

## 為什麼可以 nullable

既有 2,343 筆沒有值。**不需要資料遷移** —— NULL 在增量邏輯裡
一律視為「需要重建」，第一次同步時自然補上。
（刻意不預先算好寫入：那會讓這支 migration 需要讀檔案系統。）
"""
from alembic import op
import sqlalchemy as sa

revision = '20260830a001'
down_revision = '20260829b002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'kb_chunks',
        sa.Column('file_hash', sa.String(length=32), nullable=True,
                  comment='來源檔 MD5（增量同步比對用；NULL 代表尚未記錄，會被視為需重建）'),
    )
    op.create_index('ix_kb_chunks_file_hash', 'kb_chunks', ['file_hash'])


def downgrade() -> None:
    op.drop_index('ix_kb_chunks_file_hash', table_name='kb_chunks')
    op.drop_column('kb_chunks', 'file_hash')
