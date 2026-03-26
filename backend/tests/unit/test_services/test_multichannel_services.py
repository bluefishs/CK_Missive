"""
Multichannel Services 單元測試

覆蓋模組:
- DiscordBotService (discord_bot_service.py)
- ChannelAdapter (channel_adapter.py)
- NotificationDispatcher (notification_dispatcher.py)

Version: 1.0.0
Created: 2026-03-26
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.channel_adapter import (
    ChannelAdapter,
    ChannelMessage,
    RichCard,
    get_adapter,
    list_adapters,
    register_adapter,
    _adapters,
)
from app.services.notification_dispatcher import (
    NotificationChannel,
    NotificationDispatcher,
    NotificationTarget,
    Severity,
)


# ── Helper: mock AsyncSessionLocal for lazy imports ──

_db_patch = None
_original_session_local = None

def _ensure_core_database_mock():
    """
    discord_bot_service / channel_adapter import app.db.database.AsyncSessionLocal lazily.
    Returns a MagicMock session factory that works as async context manager.
    """
    global _db_patch, _original_session_local
    import app.db.database as db_mod
    if _original_session_local is None:
        _original_session_local = db_mod.AsyncSessionLocal
    # Create a proper async context manager mock
    mock_session = AsyncMock()
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)
    db_mod.AsyncSessionLocal = mock_factory
    return mock_factory

def _restore_database_mock():
    """Restore original AsyncSessionLocal after tests."""
    global _original_session_local
    if _original_session_local is not None:
        import app.db.database as db_mod
        db_mod.AsyncSessionLocal = _original_session_local
        _original_session_local = None


@pytest.fixture(autouse=True)
def _auto_restore_db():
    """Auto-restore AsyncSessionLocal after each test."""
    yield
    _restore_database_mock()


# ============================================================
# Discord Bot Service
# ============================================================


class TestDiscordBotServiceInit:
    """DiscordBotService 初始化與 feature flag"""

    def _create_service(self, env_overrides=None):
        env = {
            "DISCORD_BOT_ENABLED": "true",
            "DISCORD_PUBLIC_KEY": "aabbccdd",
            "DISCORD_BOT_TOKEN": "test_token",
            "DISCORD_APPLICATION_ID": "12345",
        }
        if env_overrides:
            env.update(env_overrides)
        with patch.dict("os.environ", env, clear=False):
            from app.services.discord_bot_service import DiscordBotService
            return DiscordBotService()

    def test_enabled_when_flag_true(self):
        svc = self._create_service()
        assert svc.enabled is True

    def test_disabled_when_flag_false(self):
        svc = self._create_service({"DISCORD_BOT_ENABLED": "false"})
        assert svc.enabled is False

    def test_disabled_when_flag_missing(self):
        svc = self._create_service({"DISCORD_BOT_ENABLED": ""})
        assert svc.enabled is False

    def test_public_key_stored(self):
        svc = self._create_service({"DISCORD_PUBLIC_KEY": "deadbeef"})
        assert svc.public_key == "deadbeef"

    def test_bot_token_stored(self):
        svc = self._create_service({"DISCORD_BOT_TOKEN": "tok123"})
        assert svc.bot_token == "tok123"


class TestDiscordSignatureVerification:
    """Ed25519 簽名驗證"""

    def _create_service(self, public_key=""):
        with patch.dict("os.environ", {
            "DISCORD_BOT_ENABLED": "true",
            "DISCORD_PUBLIC_KEY": public_key,
            "DISCORD_BOT_TOKEN": "",
            "DISCORD_APPLICATION_ID": "",
        }, clear=False):
            from app.services.discord_bot_service import DiscordBotService
            return DiscordBotService()

    def test_no_public_key_returns_false(self):
        svc = self._create_service("")
        assert svc.verify_signature(b"body", "sig", "ts") is False

    def test_valid_ed25519_signature(self):
        """使用真實 Ed25519 金鑰對驗證"""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        pub_bytes = public_key.public_bytes_raw()
        pub_hex = pub_bytes.hex()

        timestamp = "1616161616"
        body = b'{"type":1}'
        message = timestamp.encode() + body
        signature = private_key.sign(message).hex()

        svc = self._create_service(pub_hex)
        assert svc.verify_signature(body, signature, timestamp) is True

    def test_invalid_signature_returns_false(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        pub_hex = private_key.public_key().public_bytes_raw().hex()

        svc = self._create_service(pub_hex)
        assert svc.verify_signature(b"body", "ab" * 32, "12345") is False

    def test_malformed_hex_returns_false(self):
        svc = self._create_service("not_valid_hex")
        assert svc.verify_signature(b"body", "sig", "ts") is False

    def test_tampered_body_fails(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        pub_hex = private_key.public_key().public_bytes_raw().hex()

        timestamp = "123456"
        body = b'{"type":1}'
        message = timestamp.encode() + body
        signature = private_key.sign(message).hex()

        svc = self._create_service(pub_hex)
        assert svc.verify_signature(b'{"type":2}', signature, timestamp) is False

    def test_import_error_returns_false(self):
        svc = self._create_service("aabb")
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if "cryptography" in name:
                raise ImportError("no cryptography")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            assert svc.verify_signature(b"body", "aabb", "ts") is False


class TestDiscordSlashCommands:
    """Slash Command 處理"""

    def _create_service(self):
        with patch.dict("os.environ", {
            "DISCORD_BOT_ENABLED": "true",
            "DISCORD_PUBLIC_KEY": "",
            "DISCORD_BOT_TOKEN": "",
            "DISCORD_APPLICATION_ID": "",
        }, clear=False):
            from app.services.discord_bot_service import DiscordBotService
            return DiscordBotService()

    @pytest.mark.asyncio
    async def test_unknown_command_returns_warning(self):
        svc = self._create_service()
        result = await svc.handle_slash_command("unknown-cmd", {}, "user1")
        assert result["type"] == 4
        embed = result["data"]["embeds"][0]
        assert "未知指令" in embed["title"]
        assert "unknown-cmd" in embed["description"]

    @pytest.mark.asyncio
    async def test_ck_ask_empty_question(self):
        svc = self._create_service()
        result = await svc.handle_slash_command("ck-ask", {"question": ""}, "user1")
        embed = result["data"]["embeds"][0]
        assert "請輸入問題" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_ask_whitespace_question(self):
        svc = self._create_service()
        result = await svc.handle_slash_command("ck-ask", {"question": "   "}, "user1")
        embed = result["data"]["embeds"][0]
        assert "請輸入問題" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_ask_dispatches_to_handler(self):
        svc = self._create_service()
        svc._handle_agent_query = AsyncMock(return_value={"type": 4, "data": {"embeds": []}})
        await svc.handle_slash_command("ck-ask", {"question": "hi"}, "user1")
        svc._handle_agent_query.assert_awaited_once_with("hi", "user1")

    @pytest.mark.asyncio
    async def test_ck_doc_dispatches_to_handler(self):
        svc = self._create_service()
        svc._handle_doc_query = AsyncMock(return_value={"type": 4, "data": {"embeds": []}})
        await svc.handle_slash_command("ck-doc", {"doc_number": "ABC-001"}, "user1")
        svc._handle_doc_query.assert_awaited_once_with("ABC-001")

    @pytest.mark.asyncio
    async def test_ck_case_dispatches_to_handler(self):
        svc = self._create_service()
        svc._handle_case_query = AsyncMock(return_value={"type": 4, "data": {"embeds": []}})
        await svc.handle_slash_command("ck-case", {"case_code": "C-001"}, "user1")
        svc._handle_case_query.assert_awaited_once_with("C-001")

    @pytest.mark.asyncio
    async def test_ck_ask_success(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()

        mock_events = [
            'data: {"type":"token","token":"Hello"}',
            'data: {"type":"token","token":" World"}',
            'data: {"type":"done"}',
        ]

        async def mock_stream(*args, **kwargs):
            for e in mock_events:
                yield e

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.agent_orchestrator.AgentOrchestrator",
                    return_value=mock_orch):
            result = await svc._handle_agent_query("test question", "user1")

        assert result["type"] == 4
        embed = result["data"]["embeds"][0]
        assert "Hello World" in embed["description"]

    @pytest.mark.asyncio
    async def test_ck_ask_agent_error(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("DB down"))
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await svc._handle_agent_query("test", "user1")
        embed = result["data"]["embeds"][0]
        assert "查詢失敗" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_ask_empty_agent_response(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()

        async def mock_stream(*args, **kwargs):
            yield 'data: {"type":"done"}'

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.agent_orchestrator.AgentOrchestrator",
                    return_value=mock_orch):
            result = await svc._handle_agent_query("question", "user1")

        embed = result["data"]["embeds"][0]
        assert "無法回答" in embed["description"]

    @pytest.mark.asyncio
    async def test_ck_doc_empty_doc_number(self):
        svc = self._create_service()
        result = await svc.handle_slash_command("ck-doc", {"doc_number": ""}, "user1")
        embed = result["data"]["embeds"][0]
        assert "請輸入文號" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_doc_found(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()

        mock_doc = MagicMock()
        mock_doc.doc_number = "ABC-001"
        mock_doc.doc_type = "收文"
        mock_doc.sender = "測試機關"
        mock_doc.receiver = "乾坤"
        mock_doc.doc_date = "2026-03-01"
        mock_doc.subject = "測試公文"

        mock_repo = MagicMock()
        mock_repo.get_by_doc_number = AsyncMock(return_value=mock_doc)

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.repositories.document_repository.DocumentRepository",
                    return_value=mock_repo):
            result = await svc._handle_doc_query("ABC-001")

        assert result["type"] == 4
        embed = result["data"]["embeds"][0]
        assert "測試公文" in embed["title"]
        field_names = [f["name"] for f in embed["fields"]]
        assert "文號" in field_names
        assert "類型" in field_names
        assert "發文機關" in field_names

    @pytest.mark.asyncio
    async def test_ck_doc_not_found(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()

        mock_repo = MagicMock()
        mock_repo.get_by_doc_number = AsyncMock(return_value=None)

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.repositories.document_repository.DocumentRepository",
                    return_value=mock_repo):
            result = await svc._handle_doc_query("NONEXIST")

        embed = result["data"]["embeds"][0]
        assert "查無公文" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_doc_db_error(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        # Also patch DocumentRepository to raise, covering the case where
        # the real async_session_factory resolves instead of our mock
        with patch("app.repositories.document_repository.DocumentRepository",
                    side_effect=RuntimeError("DB error")):
            result = await svc._handle_doc_query("ABC-001")

        embed = result["data"]["embeds"][0]
        assert "查詢失敗" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_case_empty(self):
        svc = self._create_service()
        result = await svc.handle_slash_command("ck-case", {"case_code": " "}, "user1")
        embed = result["data"]["embeds"][0]
        assert "請輸入案號" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_case_found(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()

        mock_project = MagicMock()
        mock_project.project_code = "P-2026-001"
        mock_project.case_code = "C-001"
        mock_project.status = "執行中"
        mock_project.project_name = "測試專案"
        mock_project.client_name = "委託單位A"

        mock_repo = MagicMock()
        mock_repo.get_by_project_code = AsyncMock(return_value=mock_project)

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.repositories.project_repository.ProjectRepository",
                    return_value=mock_repo):
            result = await svc._handle_case_query("P-2026-001")

        embed = result["data"]["embeds"][0]
        assert "測試專案" in embed["title"]
        field_names = [f["name"] for f in embed["fields"]]
        assert "案號" in field_names
        assert "狀態" in field_names

    @pytest.mark.asyncio
    async def test_ck_case_not_found(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()

        mock_repo = MagicMock()
        mock_repo.get_by_project_code = AsyncMock(return_value=None)

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.repositories.project_repository.ProjectRepository",
                    return_value=mock_repo):
            result = await svc._handle_case_query("NONEXIST")

        embed = result["data"]["embeds"][0]
        assert "查無案件" in embed["title"]

    @pytest.mark.asyncio
    async def test_ck_case_db_error(self):
        svc = self._create_service()
        mock_factory = _ensure_core_database_mock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.repositories.project_repository.ProjectRepository",
                    side_effect=RuntimeError("DB error")):
            result = await svc._handle_case_query("C-001")

        embed = result["data"]["embeds"][0]
        assert "查詢失敗" in embed["title"]


class TestDiscordSendChannelMessage:
    """Discord push 訊息"""

    def _create_service(self, token="test_token"):
        with patch.dict("os.environ", {
            "DISCORD_BOT_ENABLED": "true",
            "DISCORD_PUBLIC_KEY": "",
            "DISCORD_BOT_TOKEN": token,
            "DISCORD_APPLICATION_ID": "",
        }, clear=False):
            from app.services.discord_bot_service import DiscordBotService
            return DiscordBotService()

    @pytest.mark.asyncio
    async def test_no_token_returns_false(self):
        svc = self._create_service(token="")
        result = await svc.send_channel_message("ch1", "hello")
        assert result is False

    @pytest.mark.asyncio
    async def test_send_success(self):
        svc = self._create_service()

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await svc.send_channel_message("ch123", "test message")

        assert result is True
        call_kwargs = mock_client.post.call_args
        assert "ch123" in call_kwargs[0][0]
        assert call_kwargs[1]["json"]["content"] == "test message"
        assert "Bot test_token" in call_kwargs[1]["headers"]["Authorization"]

    @pytest.mark.asyncio
    async def test_send_failure_status(self):
        svc = self._create_service()

        mock_resp = MagicMock()
        mock_resp.status_code = 403

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await svc.send_channel_message("ch123", "test")

        assert result is False

    @pytest.mark.asyncio
    async def test_send_network_error(self):
        svc = self._create_service()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await svc.send_channel_message("ch123", "test")

        assert result is False

    @pytest.mark.asyncio
    async def test_content_truncated_to_limit(self):
        svc = self._create_service()

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        long_content = "A" * 3000

        with patch("httpx.AsyncClient", return_value=mock_client):
            await svc.send_channel_message("ch1", long_content)

        sent_content = mock_client.post.call_args[1]["json"]["content"]
        assert len(sent_content) <= 2000


class TestDiscordHelpers:
    """Helper 函數測試"""

    def test_make_embed_response_structure(self):
        from app.services.discord_bot_service import _make_embed_response
        result = _make_embed_response("Title", "Desc", 0xFF0000)
        assert result["type"] == 4
        embed = result["data"]["embeds"][0]
        assert embed["title"] == "Title"
        assert embed["description"] == "Desc"
        assert embed["color"] == 0xFF0000
        assert embed["footer"]["text"] == "CK Missive Agent"

    def test_make_embed_response_default_color(self):
        from app.services.discord_bot_service import _make_embed_response, _COLOR_INFO
        result = _make_embed_response("T", "D")
        assert result["data"]["embeds"][0]["color"] == _COLOR_INFO

    def test_make_fields_embed_structure(self):
        from app.services.discord_bot_service import _make_fields_embed
        fields = [
            {"name": "F1", "value": "V1", "inline": True},
            {"name": "F2", "value": "V2"},
        ]
        result = _make_fields_embed("Title", fields, 0x00FF00)
        embed = result["data"]["embeds"][0]
        assert embed["title"] == "Title"
        assert len(embed["fields"]) == 2
        assert embed["fields"][0]["inline"] is True
        assert embed["fields"][1]["inline"] is False

    def test_make_fields_embed_empty_fields(self):
        from app.services.discord_bot_service import _make_fields_embed
        result = _make_fields_embed("Empty", [], 0x000000)
        assert result["data"]["embeds"][0]["fields"] == []


class TestDiscordSingleton:
    """Singleton 測試"""

    def test_get_discord_bot_service_returns_same_instance(self):
        import app.services.discord_bot_service as mod
        mod._instance = None  # Reset
        with patch.dict("os.environ", {
            "DISCORD_BOT_ENABLED": "false",
            "DISCORD_PUBLIC_KEY": "",
            "DISCORD_BOT_TOKEN": "",
            "DISCORD_APPLICATION_ID": "",
        }, clear=False):
            svc1 = mod.get_discord_bot_service()
            svc2 = mod.get_discord_bot_service()
            assert svc1 is svc2
        mod._instance = None  # Cleanup


# ============================================================
# Channel Adapter
# ============================================================


class TestChannelMessageDataclass:
    """ChannelMessage 資料類別"""

    def test_default_values(self):
        msg = ChannelMessage(
            platform="line", message_id="m1", user_id="u1",
            channel_id="c1", content="hello",
        )
        assert msg.message_type == "text"
        assert msg.reply_token == ""
        assert msg.metadata == {}

    def test_all_fields(self):
        msg = ChannelMessage(
            platform="discord", message_id="m2", user_id="u2",
            channel_id="c2", content="world", message_type="command",
            reply_token="tok", metadata={"key": "val"},
        )
        assert msg.platform == "discord"
        assert msg.message_type == "command"
        assert msg.metadata["key"] == "val"

    def test_metadata_isolation(self):
        """Each instance should get its own metadata dict"""
        msg1 = ChannelMessage("a", "1", "u", "", "c")
        msg2 = ChannelMessage("b", "2", "u", "", "c")
        msg1.metadata["x"] = 1
        assert "x" not in msg2.metadata


class TestRichCardDataclass:
    """RichCard 資料類別"""

    def test_defaults(self):
        card = RichCard(title="T", description="D")
        assert card.color == "#1890FF"
        assert card.fields == []
        assert card.footer == "CK Missive Agent"

    def test_custom_fields(self):
        card = RichCard(
            title="T", description="D",
            color="#FF0000",
            fields=[{"name": "F", "value": "V"}],
            footer="Custom",
        )
        assert card.color == "#FF0000"
        assert len(card.fields) == 1


class ConcreteAdapter(ChannelAdapter):
    """測試用具體 Adapter 實作"""

    @property
    def platform_name(self) -> str:
        return "test_platform"

    def verify_request(self, body, headers):
        return headers.get("x-valid") == "true"

    def parse_messages(self, payload):
        return [
            ChannelMessage(
                platform="test_platform",
                message_id=payload.get("id", ""),
                user_id=payload.get("user", ""),
                channel_id="",
                content=payload.get("text", ""),
            )
        ]

    async def send_reply(self, message, text):
        return True

    async def send_rich(self, message, card):
        return True

    async def push_message(self, target_id, text):
        return True


class TestChannelAdapterAbstract:
    """ChannelAdapter 抽象基類"""

    def test_concrete_adapter_platform_name(self):
        adapter = ConcreteAdapter()
        assert adapter.platform_name == "test_platform"

    def test_verify_request_valid(self):
        adapter = ConcreteAdapter()
        assert adapter.verify_request(b"body", {"x-valid": "true"}) is True

    def test_verify_request_invalid(self):
        adapter = ConcreteAdapter()
        assert adapter.verify_request(b"body", {"x-valid": "false"}) is False

    def test_parse_messages(self):
        adapter = ConcreteAdapter()
        msgs = adapter.parse_messages({"id": "m1", "user": "u1", "text": "hi"})
        assert len(msgs) == 1
        assert msgs[0].content == "hi"
        assert msgs[0].platform == "test_platform"

    @pytest.mark.asyncio
    async def test_send_reply(self):
        adapter = ConcreteAdapter()
        msg = ChannelMessage("test", "m1", "u1", "", "hello")
        assert await adapter.send_reply(msg, "reply") is True

    @pytest.mark.asyncio
    async def test_send_rich(self):
        adapter = ConcreteAdapter()
        msg = ChannelMessage("test", "m1", "u1", "", "hello")
        card = RichCard(title="T", description="D")
        assert await adapter.send_rich(msg, card) is True

    @pytest.mark.asyncio
    async def test_push_message(self):
        adapter = ConcreteAdapter()
        assert await adapter.push_message("target1", "text") is True

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            ChannelAdapter()


class TestChannelAdapterAgentQuery:
    """handle_agent_query 統一 Agent 問答"""

    @pytest.mark.asyncio
    async def test_agent_query_success(self):
        adapter = ConcreteAdapter()
        msg = ChannelMessage("test_platform", "m1", "u1", "", "query text")

        mock_factory = _ensure_core_database_mock()

        mock_events = [
            'data: {"type":"token","token":"Answer"}',
            'data: {"type":"token","token":" here"}',
            'data: {"type":"done"}',
        ]

        async def mock_stream(*args, **kwargs):
            for e in mock_events:
                yield e

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.agent_orchestrator.AgentOrchestrator",
                    return_value=mock_orch):
            result = await adapter.handle_agent_query(msg)

        assert result == "Answer here"

    @pytest.mark.asyncio
    async def test_agent_query_empty_response(self):
        adapter = ConcreteAdapter()
        msg = ChannelMessage("test_platform", "m1", "u1", "", "query")

        mock_factory = _ensure_core_database_mock()

        async def mock_stream(*args, **kwargs):
            yield 'data: {"type":"done"}'

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.agent_orchestrator.AgentOrchestrator",
                    return_value=mock_orch):
            result = await adapter.handle_agent_query(msg)

        assert "無法回答" in result

    @pytest.mark.asyncio
    async def test_agent_query_exception(self):
        adapter = ConcreteAdapter()
        msg = ChannelMessage("test_platform", "m1", "u1", "", "query")

        mock_factory = _ensure_core_database_mock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("DB error"))
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.agent_orchestrator.AgentOrchestrator",
                    side_effect=RuntimeError("DB error")):
            result = await adapter.handle_agent_query(msg)

        assert "錯誤" in result

    @pytest.mark.asyncio
    async def test_agent_query_malformed_events(self):
        """Non-JSON events should be silently skipped"""
        adapter = ConcreteAdapter()
        msg = ChannelMessage("test_platform", "m1", "u1", "", "query")

        mock_factory = _ensure_core_database_mock()

        async def mock_stream(*args, **kwargs):
            yield "not-json"
            yield 'data: {"type":"token","token":"OK"}'

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.agent_orchestrator.AgentOrchestrator",
                    return_value=mock_orch):
            result = await adapter.handle_agent_query(msg)

        assert result == "OK"

    @pytest.mark.asyncio
    async def test_agent_query_truncates_input(self):
        """Content over 2000 chars should be truncated"""
        adapter = ConcreteAdapter()
        long_content = "A" * 3000
        msg = ChannelMessage("test_platform", "m1", "u1", "", long_content)

        mock_factory = _ensure_core_database_mock()

        captured_question = None

        async def mock_stream(question, session_id, **kwargs):
            nonlocal captured_question
            captured_question = question
            yield 'data: {"type":"token","token":"ok"}'

        mock_orch = MagicMock()
        mock_orch.stream_agent_query = mock_stream

        mock_db = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.ai.agent_orchestrator.AgentOrchestrator",
                    return_value=mock_orch):
            await adapter.handle_agent_query(msg)

        assert captured_question is not None
        assert len(captured_question) <= 2000


class TestAdapterRegistry:
    """Adapter 註冊與查詢"""

    def setup_method(self):
        _adapters.clear()

    def teardown_method(self):
        _adapters.clear()

    def test_register_and_get(self):
        adapter = ConcreteAdapter()
        register_adapter(adapter)
        assert get_adapter("test_platform") is adapter

    def test_get_nonexistent(self):
        assert get_adapter("nonexistent") is None

    def test_list_adapters(self):
        register_adapter(ConcreteAdapter())
        assert "test_platform" in list_adapters()

    def test_list_empty(self):
        assert list_adapters() == []

    def test_register_overwrites(self):
        a1 = ConcreteAdapter()
        a2 = ConcreteAdapter()
        register_adapter(a1)
        register_adapter(a2)
        assert get_adapter("test_platform") is a2


# ============================================================
# Notification Dispatcher
# ============================================================


class TestNotificationEnums:
    """列舉測試"""

    def test_channel_values(self):
        assert NotificationChannel.LINE == "line"
        assert NotificationChannel.DISCORD == "discord"
        assert NotificationChannel.ALL == "all"

    def test_severity_values(self):
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.CRITICAL == "critical"

    def test_channel_is_str(self):
        assert isinstance(NotificationChannel.LINE, str)

    def test_severity_is_str(self):
        assert isinstance(Severity.INFO, str)


class TestNotificationTarget:
    """通知對象"""

    def test_defaults(self):
        t = NotificationTarget(user_id=1)
        assert t.line_user_id is None
        assert t.discord_channel_id is None
        assert t.preferred_channel == NotificationChannel.ALL

    def test_full_target(self):
        t = NotificationTarget(
            user_id=42,
            line_user_id="U123",
            discord_channel_id="ch456",
            preferred_channel=NotificationChannel.LINE,
        )
        assert t.user_id == 42
        assert t.preferred_channel == NotificationChannel.LINE


class TestDeadlineAlert:
    """公文截止提醒"""

    @pytest.mark.asyncio
    async def test_deadline_line_only(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U111",
            preferred_channel=NotificationChannel.LINE,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_deadline_reminder = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc):
            results = await dispatcher.send_deadline_alert(target, "重要公文", "2026-04-01")

        assert results["line"] is True
        assert "discord" not in results
        mock_line_svc.push_deadline_reminder.assert_awaited_once_with(
            "U111", "重要公文", "2026-04-01",
        )

    @pytest.mark.asyncio
    async def test_deadline_discord_only(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, discord_channel_id="ch1",
            preferred_channel=NotificationChannel.DISCORD,
        )

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.discord_bot_service.get_discord_bot_service",
                    return_value=mock_discord_svc):
            results = await dispatcher.send_deadline_alert(target, "截止公文", "2026-05-01")

        assert results["discord"] is True
        assert "line" not in results
        sent_msg = mock_discord_svc.send_channel_message.call_args[0][1]
        assert "截止公文" in sent_msg
        assert "2026-05-01" in sent_msg

    @pytest.mark.asyncio
    async def test_deadline_all_channels(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U111", discord_channel_id="ch1",
            preferred_channel=NotificationChannel.ALL,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_deadline_reminder = AsyncMock(return_value=True)

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc), \
             patch("app.services.discord_bot_service.get_discord_bot_service",
                   return_value=mock_discord_svc):
            results = await dispatcher.send_deadline_alert(target, "公文", "2026-06-01")

        assert results["line"] is True
        assert results["discord"] is True

    @pytest.mark.asyncio
    async def test_deadline_no_ids_skips(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(user_id=1, preferred_channel=NotificationChannel.ALL)
        results = await dispatcher.send_deadline_alert(target, "公文", "2026-01-01")
        assert results == {}

    @pytest.mark.asyncio
    async def test_deadline_line_error_returns_false(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U111",
            preferred_channel=NotificationChannel.LINE,
        )

        with patch("app.services.line_bot_service.get_line_bot_service",
                    side_effect=RuntimeError("import error")):
            results = await dispatcher.send_deadline_alert(target, "公文", "2026-01-01")

        assert results["line"] is False

    @pytest.mark.asyncio
    async def test_deadline_discord_error_returns_false(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, discord_channel_id="ch1",
            preferred_channel=NotificationChannel.DISCORD,
        )

        with patch("app.services.discord_bot_service.get_discord_bot_service",
                    side_effect=RuntimeError("import error")):
            results = await dispatcher.send_deadline_alert(target, "公文", "2026-01-01")

        assert results["discord"] is False

    @pytest.mark.asyncio
    async def test_deadline_preferred_discord_skips_line(self):
        """When preferred=DISCORD, line_user_id should be ignored"""
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U111", discord_channel_id="ch1",
            preferred_channel=NotificationChannel.DISCORD,
        )

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.discord_bot_service.get_discord_bot_service",
                    return_value=mock_discord_svc):
            results = await dispatcher.send_deadline_alert(target, "公文", "2026-01-01")

        assert "line" not in results
        assert results["discord"] is True


class TestBudgetAlert:
    """預算警報"""

    @pytest.mark.asyncio
    async def test_budget_alert_message_format(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U111",
            preferred_channel=NotificationChannel.LINE,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc):
            results = await dispatcher.send_budget_alert(
                target, "大專案", 85.5, 1234567,
            )

        assert results["line"] is True
        sent_msg = mock_line_svc.push_message.call_args[0][1]
        assert "大專案" in sent_msg
        assert "85.5%" in sent_msg
        assert "1,234,567" in sent_msg
        assert "預算警報" in sent_msg

    @pytest.mark.asyncio
    async def test_budget_alert_both_channels(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U1", discord_channel_id="ch1",
            preferred_channel=NotificationChannel.ALL,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(return_value=True)

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc), \
             patch("app.services.discord_bot_service.get_discord_bot_service",
                   return_value=mock_discord_svc):
            results = await dispatcher.send_budget_alert(target, "P1", 90.0, 500000)

        assert results["line"] is True
        assert results["discord"] is True


class TestSystemAlert:
    """系統警報"""

    @pytest.mark.asyncio
    async def test_system_alert_info_prefix(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, discord_channel_id="ch1",
            preferred_channel=NotificationChannel.DISCORD,
        )

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.discord_bot_service.get_discord_bot_service",
                    return_value=mock_discord_svc):
            await dispatcher.send_system_alert(target, "System OK", Severity.INFO)

        sent_msg = mock_discord_svc.send_channel_message.call_args[0][1]
        assert "\u2139\ufe0f" in sent_msg  # info emoji

    @pytest.mark.asyncio
    async def test_system_alert_critical_prefix(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U1",
            preferred_channel=NotificationChannel.LINE,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc):
            await dispatcher.send_system_alert(target, "DB Down", Severity.CRITICAL)

        sent_msg = mock_line_svc.push_message.call_args[0][1]
        assert "\U0001f6a8" in sent_msg  # siren emoji
        assert "DB Down" in sent_msg

    @pytest.mark.asyncio
    async def test_system_alert_warning_prefix(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U1",
            preferred_channel=NotificationChannel.LINE,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc):
            await dispatcher.send_system_alert(target, "Disk 90%", Severity.WARNING)

        sent_msg = mock_line_svc.push_message.call_args[0][1]
        assert "\u26a0\ufe0f" in sent_msg


class TestBroadcastToAll:
    """廣播到所有通道"""

    @pytest.mark.asyncio
    async def test_broadcast_line_and_discord(self):
        dispatcher = NotificationDispatcher()

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(return_value=True)

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc), \
             patch("app.services.discord_bot_service.get_discord_bot_service",
                   return_value=mock_discord_svc):
            results = await dispatcher.broadcast_to_all(
                "System maintenance",
                line_user_ids=["U1", "U2", "U3"],
                discord_channel_ids=["ch1", "ch2"],
            )

        assert results["line"] == 3
        assert results["discord"] == 2

    @pytest.mark.asyncio
    async def test_broadcast_partial_failure(self):
        dispatcher = NotificationDispatcher()

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(side_effect=[True, False, True])

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc):
            results = await dispatcher.broadcast_to_all(
                "msg",
                line_user_ids=["U1", "U2", "U3"],
            )

        assert results["line"] == 2
        assert results["discord"] == 0

    @pytest.mark.asyncio
    async def test_broadcast_no_targets(self):
        dispatcher = NotificationDispatcher()
        results = await dispatcher.broadcast_to_all("msg")
        assert results == {"line": 0, "discord": 0}

    @pytest.mark.asyncio
    async def test_broadcast_empty_lists(self):
        dispatcher = NotificationDispatcher()
        results = await dispatcher.broadcast_to_all(
            "msg", line_user_ids=[], discord_channel_ids=[],
        )
        assert results == {"line": 0, "discord": 0}

    @pytest.mark.asyncio
    async def test_broadcast_discord_partial_failure(self):
        dispatcher = NotificationDispatcher()

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(side_effect=[True, False])

        with patch("app.services.discord_bot_service.get_discord_bot_service",
                    return_value=mock_discord_svc):
            results = await dispatcher.broadcast_to_all(
                "msg",
                discord_channel_ids=["ch1", "ch2"],
            )

        assert results["discord"] == 1
        assert results["line"] == 0


class TestBroadcastPrivateMethod:
    """_broadcast 私有方法邊界情況"""

    @pytest.mark.asyncio
    async def test_broadcast_channel_filter_line_only(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U1", discord_channel_id="ch1",
            preferred_channel=NotificationChannel.LINE,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc):
            results = await dispatcher._broadcast(target, "msg", Severity.INFO)

        assert "line" in results
        assert "discord" not in results

    @pytest.mark.asyncio
    async def test_broadcast_channel_filter_discord_only(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U1", discord_channel_id="ch1",
            preferred_channel=NotificationChannel.DISCORD,
        )

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.discord_bot_service.get_discord_bot_service",
                    return_value=mock_discord_svc):
            results = await dispatcher._broadcast(target, "msg", Severity.INFO)

        assert "discord" in results
        assert "line" not in results

    @pytest.mark.asyncio
    async def test_broadcast_line_exception_caught(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U1",
            preferred_channel=NotificationChannel.ALL,
        )

        with patch("app.services.line_bot_service.get_line_bot_service",
                    side_effect=RuntimeError("boom")):
            results = await dispatcher._broadcast(target, "msg", Severity.INFO)

        assert results["line"] is False

    @pytest.mark.asyncio
    async def test_broadcast_discord_exception_caught(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, discord_channel_id="ch1",
            preferred_channel=NotificationChannel.ALL,
        )

        with patch("app.services.discord_bot_service.get_discord_bot_service",
                    side_effect=RuntimeError("boom")):
            results = await dispatcher._broadcast(target, "msg", Severity.INFO)

        assert results["discord"] is False

    @pytest.mark.asyncio
    async def test_broadcast_both_channels_all(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(
            user_id=1, line_user_id="U1", discord_channel_id="ch1",
            preferred_channel=NotificationChannel.ALL,
        )

        mock_line_svc = MagicMock()
        mock_line_svc.push_message = AsyncMock(return_value=True)

        mock_discord_svc = MagicMock()
        mock_discord_svc.send_channel_message = AsyncMock(return_value=True)

        with patch("app.services.line_bot_service.get_line_bot_service",
                    return_value=mock_line_svc), \
             patch("app.services.discord_bot_service.get_discord_bot_service",
                   return_value=mock_discord_svc):
            results = await dispatcher._broadcast(target, "msg", Severity.INFO)

        assert results["line"] is True
        assert results["discord"] is True

    @pytest.mark.asyncio
    async def test_broadcast_no_channels_configured(self):
        dispatcher = NotificationDispatcher()
        target = NotificationTarget(user_id=1, preferred_channel=NotificationChannel.ALL)

        results = await dispatcher._broadcast(target, "msg", Severity.INFO)
        assert results == {}
