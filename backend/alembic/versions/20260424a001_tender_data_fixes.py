"""Tender data fixes (2026-04-24):
  (A) Backfill ezbid unit_id from ezbid_id (9567 rows of pollution)
  (B) tender_bookmarks per-user unique: drop (unit_id, job_number), add (user_id, unit_id, job_number)

Revision ID: 20260424a001
Revises: 20260421a002
Create Date: 2026-04-24

Root cause: ezbid records were inserted with empty unit_id/job_number,
causing (a) React rowKey dup warnings, (b) /tender//... 404, (c) detail
endpoint unable to resolve via unit_id.isdigit() path.
"""
from alembic import op


revision = "20260424a001"
down_revision = "20260421a002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # (A) Backfill ezbid unit_id = ezbid_id where blank.
    op.execute("""
        UPDATE tender_records
        SET unit_id = ezbid_id
        WHERE source = 'ezbid'
          AND (unit_id IS NULL OR unit_id = '')
          AND ezbid_id IS NOT NULL
          AND ezbid_id <> '';
    """)

    # (B) tender_bookmarks: per-user unique.
    # Drop old global unique; add composite with user_id.
    # NULLs are treated as distinct in Postgres btree, so legacy rows with
    # user_id IS NULL can coexist.
    op.execute("""
        ALTER TABLE tender_bookmarks
        DROP CONSTRAINT IF EXISTS ix_tender_bookmark_unit_job;
    """)
    op.execute("DROP INDEX IF EXISTS ix_tender_bookmark_unit_job;")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_tender_bookmark_user_unit_job
        ON tender_bookmarks (user_id, unit_id, job_number);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_tender_bookmark_user_unit_job;")
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_tender_bookmark_unit_job
        ON tender_bookmarks (unit_id, job_number);
    """)
    # Note: unit_id backfill is NOT reverted (data fix is not reversible
    # without losing the original blank state which was a bug).
