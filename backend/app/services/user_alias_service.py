# -*- coding: utf-8 -*-
"""User Alias Service — Identity Unification (ADR-0025)

v5.8.0 坤哥意識體 Phase Identity。

核心 helper：
- expand_user_alias(user_id) → Set[int]
  傳入任一分身 id，回傳所有等價 id（含 canonical + 所有其他 alias）
- list_canonical_only() → List[User]
  承辦同仁下拉等 UI 用 — 只取 canonical（canonical_user_id IS NULL）
- merge_alias(canonical_id, alias_id, actor_id, harmonize_role=False)
  合併操作；規則 B 預設不動 role，僅 Identity 層合併。

無 LRU 快取（避免合併後資料不一致；Session 層已夠快）。
"""
from __future__ import annotations

import logging
from typing import List, Optional, Set

from sqlalchemy import and_, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.extended.models import User

logger = logging.getLogger(__name__)


async def expand_user_alias(db: AsyncSession, user_id: int) -> Set[int]:
    """展開 identity alias group。

    傳入任一 id，回傳整組等價 id（canonical + 所有 aliases）。
    若該 user 無分身，回傳 {user_id} 自己。

    邊界：
    - 不存在的 id → 回 {user_id}（容錯）
    - 循環設定（理論上不該發生，但仍 guard）→ 只展一層
    """
    try:
        # 1) 找 canonical_id：若自己 canonical_user_id 是 NULL → canonical_id = user_id
        #    否則 canonical_id = canonical_user_id
        row = (await db.execute(
            select(User.id, User.canonical_user_id).where(User.id == user_id)
        )).one_or_none()
        if not row:
            return {user_id}
        _, canonical_fk = row
        canonical_id = canonical_fk if canonical_fk is not None else user_id

        # 2) 取所有 aliases of canonical（含 canonical 自己）
        result = await db.execute(
            select(User.id).where(
                or_(
                    User.id == canonical_id,
                    User.canonical_user_id == canonical_id,
                )
            )
        )
        ids = {r[0] for r in result.all()}
        if not ids:
            ids = {user_id}
        return ids
    except Exception as e:
        logger.warning("expand_user_alias(%s) failed: %s", user_id, e)
        return {user_id}


async def list_canonical_only(
    db: AsyncSession,
    *,
    is_active: bool = True,
    include_alias_count: bool = False,
) -> List[User]:
    """回傳所有 canonical user（承辦同仁下拉等 UI 用）。

    一個真實人員只會出現一次。
    """
    stmt = select(User).where(User.canonical_user_id.is_(None))
    if is_active:
        stmt = stmt.where(User.is_active == True)  # noqa: E712
    stmt = stmt.order_by(User.full_name, User.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def detect_potential_aliases(db: AsyncSession) -> List[dict]:
    """偵測可能的分身 — 同 full_name 多筆 user。

    回傳結構：
      [{"full_name": "李昭德", "users": [{"id": 11, "email": "...", "role": "..."}, ...]}]

    供 admin UI 主動提示。
    """
    # 1) full_name 重複的
    rows = (await db.execute(
        text("""
            SELECT full_name, COUNT(*) AS n
            FROM users
            WHERE full_name IS NOT NULL AND full_name != ''
            GROUP BY full_name
            HAVING COUNT(*) > 1
            ORDER BY full_name
        """)
    )).all()

    clusters = []
    for full_name, _count in rows:
        detail = (await db.execute(
            select(
                User.id, User.username, User.email, User.role,
                User.is_admin, User.is_superuser, User.auth_provider,
                User.canonical_user_id, User.is_active,
            ).where(User.full_name == full_name).order_by(User.id)
        )).all()
        users = [
            {
                "id": u[0],
                "username": u[1],
                "email": u[2],
                "role": u[3],
                "is_admin": u[4],
                "is_superuser": u[5],
                "auth_provider": u[6],
                "canonical_user_id": u[7],
                "is_active": u[8],
                "is_canonical": u[7] is None,
            }
            for u in detail
        ]
        # 是否已全部合併（僅一個 canonical，其他都指向它）
        canonicals = [u for u in users if u["is_canonical"]]
        already_merged = (
            len(canonicals) == 1
            and all(
                u["canonical_user_id"] == canonicals[0]["id"]
                for u in users
                if not u["is_canonical"]
            )
        )
        clusters.append({
            "full_name": full_name,
            "users": users,
            "already_merged": already_merged,
        })
    return clusters


async def merge_alias(
    db: AsyncSession,
    *,
    canonical_id: int,
    alias_id: int,
    actor_id: int,
    harmonize_role: bool = False,
    notes: Optional[str] = None,
) -> dict:
    """合併分身 — 將 alias 指向 canonical。

    規則 B（權限隔離）：預設 harmonize_role=False，不動 alias 自身 role。
    若 harmonize_role=True，alias.role 覆寫為 canonical.role（需人類確認）。

    Raises:
        ValueError: 合併目標不合法
    """
    if canonical_id == alias_id:
        raise ValueError("canonical_id 與 alias_id 不可相同")

    # 取兩端 user
    canonical = (await db.execute(
        select(User).where(User.id == canonical_id)
    )).scalar_one_or_none()
    alias = (await db.execute(
        select(User).where(User.id == alias_id)
    )).scalar_one_or_none()
    if not canonical or not alias:
        raise ValueError(f"canonical_id={canonical_id} or alias_id={alias_id} not found")

    # canonical 自己不能是 alias
    if canonical.canonical_user_id is not None:
        raise ValueError(
            f"canonical_id={canonical_id} 本身為 alias（指向 {canonical.canonical_user_id}），"
            "請先選擇真正的 canonical"
        )

    canonical_role = canonical.role
    alias_role = alias.role

    # 更新 alias
    alias.canonical_user_id = canonical_id
    if harmonize_role and alias_role != canonical_role:
        alias.role = canonical_role
        alias.is_admin = canonical.is_admin
        alias.is_superuser = canonical.is_superuser

    # 審計 log
    await db.execute(
        text("""
            INSERT INTO user_merge_log
              (canonical_id, alias_id, canonical_role, alias_role,
               role_harmonized, merged_by, notes)
            VALUES (:cid, :aid, :crole, :arole, :harm, :actor, :notes)
        """),
        {
            "cid": canonical_id,
            "aid": alias_id,
            "crole": canonical_role,
            "arole": alias_role,
            "harm": harmonize_role,
            "actor": actor_id,
            "notes": notes,
        },
    )

    await db.commit()
    logger.info(
        "User merge: alias=%d → canonical=%d by actor=%d "
        "(alias_role=%s, canonical_role=%s, harmonized=%s)",
        alias_id, canonical_id, actor_id, alias_role, canonical_role, harmonize_role,
    )
    return {
        "canonical_id": canonical_id,
        "alias_id": alias_id,
        "alias_role_before": alias_role,
        "alias_role_after": alias.role,
        "canonical_role": canonical_role,
        "harmonized": harmonize_role,
    }
