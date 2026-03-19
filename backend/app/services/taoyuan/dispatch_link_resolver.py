"""
Resolve the correct dispatch for a document based on ck_note field.

Used during batch import to prevent over-linking.

@version 1.0.0
@date 2026-03-16
"""

import re
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import TaoyuanDispatchOrder

logger = logging.getLogger(__name__)

# Dispatch number patterns from ck_note
DISPATCH_PATTERNS = [
    re.compile(r'派工單[號]?\s*[（(]?\s*0*(\d{1,4})\s*[）)]?'),
    re.compile(r'派工\s*0*(\d{1,4})'),
    re.compile(r'查估[案]?[_\s]*派工單?\s*0*(\d{1,4})'),
    re.compile(r'查估[_\s]*0*(\d{1,4})(?:\s*[（(]|$|\s)'),
]

# Keywords identifying generic admin docs (not specific to any dispatch)
GENERIC_KEYWORDS = [
    '契約書', '雇主意外責任險', '專業責任保險', '教育訓練',
    '系統建置', '道路專案系統', '議約作業', '標案案號', '採購',
]


def extract_dispatch_number(ck_note: str) -> Optional[str]:
    """Extract dispatch number from ck_note. Returns number string or None.

    Tries each pattern in priority order and returns the first match.
    Leading zeros are stripped.

    Examples:
        "派工單號001" -> "1"
        "派工 023" -> "23"
        "查估案 派工單 5" -> "5"
        "一般行政公文" -> None
    """
    if not ck_note:
        return None

    for pattern in DISPATCH_PATTERNS:
        m = pattern.search(ck_note)
        if m:
            return str(int(m.group(1)))  # strip leading zeros
    return None


def extract_year(text: str) -> str:
    """Extract ROC year (e.g., '115') from text.

    Looks for patterns like '115年', '114年度'.
    Falls back to empty string if not found.
    """
    if not text:
        return ""
    m = re.search(r'(\d{2,3})(?:[-~～至]\d{2,3})?年', text)
    return m.group(1) if m else ""


def is_generic_admin_doc(subject: str, ck_note: str) -> bool:
    """Check if document is a generic admin doc that shouldn't be linked to specific dispatches.

    Returns True if subject or ck_note contains generic admin keywords
    AND no specific dispatch number is found in ck_note.
    """
    combined = (subject or '') + (ck_note or '')
    if not combined:
        return False

    # If there's a dispatch number, it's NOT generic
    if extract_dispatch_number(ck_note or ''):
        return False

    return any(kw in combined for kw in GENERIC_KEYWORDS)


async def resolve_dispatch_id(
    ck_note: str,
    subject: str,
    db_session: AsyncSession,
) -> Optional[int]:
    """Resolve the correct dispatch_order_id for a document.

    Logic:
    1. If generic admin doc (contract-level), return None (should not link to specific dispatch).
    2. Extract dispatch number from ck_note.
    3. Look up TaoyuanDispatchOrder by dispatch_no suffix match.
    4. Return dispatch ID or None if unresolvable.

    Args:
        ck_note: The document's ck_note (乾坤備註) field.
        subject: The document's subject field.
        db_session: SQLAlchemy async session.

    Returns:
        dispatch_order_id or None if generic/unresolvable.
    """
    # Step 1: Filter out generic admin docs
    if is_generic_admin_doc(subject, ck_note):
        logger.debug("Generic admin doc, skipping dispatch resolution: %s", subject[:60])
        return None

    # Step 2: Extract dispatch number
    dispatch_num = extract_dispatch_number(ck_note or '')
    if not dispatch_num:
        return None

    # Step 3: Look up dispatch by dispatch_no suffix
    # dispatch_no format is typically like "115年_派工單號001" or just a number
    # We search for dispatch_no ending with the number portion
    year = extract_year(ck_note or '') or extract_year(subject or '')

    # Try exact suffix match: dispatch_no LIKE '%{number}' with optional zero-padding
    padded = dispatch_num.zfill(3)  # "1" -> "001"

    # Build candidates for LIKE matching
    like_patterns = [
        f"%{padded}",          # e.g., %001
        f"%{dispatch_num}",    # e.g., %1 (without padding)
    ]

    for pattern in like_patterns:
        query = select(TaoyuanDispatchOrder.id, TaoyuanDispatchOrder.dispatch_no).where(
            TaoyuanDispatchOrder.dispatch_no.ilike(pattern),
        )
        if year:
            query = query.where(TaoyuanDispatchOrder.dispatch_no.ilike(f"{year}%"))

        result = await db_session.execute(query)
        rows = result.all()

        if len(rows) == 1:
            logger.info(
                "Resolved dispatch %s (id=%d) from ck_note number %s",
                rows[0].dispatch_no, rows[0].id, dispatch_num,
            )
            return rows[0].id
        if len(rows) > 1:
            # Multiple matches — try stricter match with zero-padded suffix
            continue

    # If no year filter was applied or year-filtered didn't work, try without year
    if year:
        for pattern in like_patterns:
            query = select(TaoyuanDispatchOrder.id, TaoyuanDispatchOrder.dispatch_no).where(
                TaoyuanDispatchOrder.dispatch_no.ilike(pattern),
            )
            result = await db_session.execute(query)
            rows = result.all()

            if len(rows) == 1:
                logger.info(
                    "Resolved dispatch %s (id=%d) from ck_note number %s (no year filter)",
                    rows[0].dispatch_no, rows[0].id, dispatch_num,
                )
                return rows[0].id

    logger.debug("Could not resolve dispatch for number %s from ck_note", dispatch_num)
    return None
