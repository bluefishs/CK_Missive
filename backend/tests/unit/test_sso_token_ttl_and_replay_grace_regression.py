# -*- coding: utf-8 -*-
"""
SSO 止血 regression（2026-07-21）
鎖定兩項「先止血」行為，防未來回歸（L74/L78 SSO 家族）：
  1. SSO access token / session TTL 可經 access_token_ttl_minutes 拉長為 8h（local login 不受影響）
  2. refresh token rotation 併發寬限期：近 N 秒內剛被 rotation 撤銷的 token 二次使用
     判為併發誤觸、不撤銷該用戶全部 session（避免雙 axios/多請求併發 → 401 風暴踢掉在編輯的 owner）

執行方式:
    pytest tests/unit/test_sso_token_ttl_and_replay_grace_regression.py -v

註：generate_login_response / verify_refresh_token 的完整 DB e2e 由 owner 實體瀏覽器
（帶真實 ck_employee cookie）驗證；此處以 mock 鎖定核心機制不回歸。
"""
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core.auth_service import AuthService
from app.core.config import settings


class TestSsoTokenTtlConfig:
    """止血①：SSO TTL 設定與 access token 機制"""

    def test_sso_ttl_default_is_8h(self):
        """SSO access token TTL 預設 480 分鐘（8h）— 可經 env 覆蓋回滾"""
        assert settings.SSO_ACCESS_TOKEN_EXPIRE_MINUTES == 480

    def test_local_login_ttl_unchanged(self):
        """local login TTL 維持 60min，不因 SSO 止血弱化"""
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60

    def test_access_token_honors_8h_expiry(self):
        """create_access_token 以 8h expires_delta 產出的 token，exp 反映 ~8h（SSO 路徑依賴此機制）"""
        token = AuthService.create_access_token(
            data={"sub": "13", "email": "jujuiacc@gmail.com"},
            expires_delta=timedelta(minutes=480),
        )
        payload = AuthService.verify_token(token)
        assert payload is not None
        # 用 time.time() 取正確 UTC Unix 時間（避免 naive datetime.utcnow().timestamp() 在 UTC+8 機器的時區偏移）
        remaining = payload["exp"] - time.time()
        # 允許數秒執行誤差；核心是遠大於 60min(3600s)、接近 8h(28800s)
        assert remaining > 60 * 60 * 7  # > 7h
        assert remaining <= 60 * 60 * 8 + 60  # <= 8h + 誤差


class TestRefreshReplayGrace:
    """止血②：refresh rotation 併發寬限期"""

    def test_grace_default_is_5s(self):
        assert settings.REFRESH_REPLAY_GRACE_SECONDS == 5

    @pytest.mark.asyncio
    async def test_concurrent_reuse_within_grace_does_not_revoke_all(self):
        """近寬限期內剛撤銷的 token 二次使用 → 回 None 但不撤銷全 session（db.execute 僅 2 次）"""
        no_active = Mock()
        no_active.scalar_one_or_none = Mock(return_value=None)
        replay = Mock()
        replay_session = Mock(
            user_id=13, token_jti="jti-x",
            revoked_at=datetime.utcnow() - timedelta(seconds=2),  # 2s 前剛 rotation 撤銷
        )
        replay.scalar_one_or_none = Mock(return_value=replay_session)

        db = Mock()
        db.execute = AsyncMock(side_effect=[no_active, replay])
        db.commit = AsyncMock()

        user = await AuthService.verify_refresh_token(db, "tok-concurrent")

        assert user is None
        # 關鍵：不得走到「撤銷全 session」的第 3 次 execute
        assert db.execute.call_count == 2, "併發寬限期內不應撤銷全部 session"

    @pytest.mark.asyncio
    async def test_true_replay_after_grace_revokes_all(self):
        """逾寬限期的已撤銷 token 二次使用 → 判 replay 攻擊，撤銷全 session（db.execute 3 次）"""
        no_active = Mock()
        no_active.scalar_one_or_none = Mock(return_value=None)
        replay = Mock()
        replay_session = Mock(
            user_id=13, token_jti="jti-y",
            revoked_at=datetime.utcnow() - timedelta(seconds=60),  # 60s 前（遠逾寬限）
        )
        replay.scalar_one_or_none = Mock(return_value=replay_session)

        db = Mock()
        db.execute = AsyncMock(side_effect=[no_active, replay, Mock()])
        db.commit = AsyncMock()

        user = await AuthService.verify_refresh_token(db, "tok-stolen")

        assert user is None
        assert db.execute.call_count == 3, "真 replay 應撤銷全部 session（第 3 次 execute）"
        db.commit.assert_awaited()
