"""
5. 系統模組 (System Module) + AI 模組

- SystemNotification: 系統通知
- UserSession: 使用者會話
- SiteNavigationItem: 導覽項目
- SiteConfiguration: 網站配置
- AIPromptVersion: AI Prompt 版本控制
- AISearchHistory: AI 搜尋歷史
- AISynonym: AI 同義詞
"""
from ._base import *


class SystemNotification(Base):
    """系統通知模型"""
    __tablename__ = "system_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True, index=True, comment="接收者ID")
    recipient_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=True, index=True, comment="接收者ID (別名)")
    title = Column(String(200), nullable=False, comment="通知標題")
    message = Column(Text, nullable=False, comment="通知內容")
    notification_type = Column(String(50), default="info", comment="通知類型")
    is_read = Column(Boolean, default=False, index=True, comment="是否已讀")
    created_at = Column(DateTime, server_default=func.now(), index=True, comment="建立時間")
    read_at = Column(DateTime, nullable=True, comment="已讀時間")
    data = Column(JSONB, nullable=True, comment="附加資料")


class UserSession(Base):
    """使用者會話模型"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), nullable=True)
    ip_address = Column(String(255), nullable=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime, nullable=True)


class SiteNavigationItem(Base):
    """網站導航項目模型"""
    __tablename__ = "site_navigation_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False, comment="導航標題")
    key = Column(String(100), unique=True, nullable=False, comment="導航鍵值")
    path = Column(String(200), comment="路徑")
    icon = Column(String(50), comment="圖標")
    sort_order = Column(Integer, default=0, comment="排序")
    parent_id = Column(Integer, ForeignKey('site_navigation_items.id'), nullable=True, comment="父級ID")
    is_enabled = Column(Boolean, default=True, comment="是否啟用")
    is_visible = Column(Boolean, default=True, comment="是否顯示")
    level = Column(Integer, default=1, comment="層級")
    description = Column(String(500), comment="描述")
    target = Column(String(50), default="_self", comment="打開方式")
    permission_required = Column(Text, comment="所需權限(JSON格式)")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")


class SiteConfiguration(Base):
    """網站配置模型"""
    __tablename__ = "site_configurations"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置鍵")
    value = Column(Text, comment="配置值")
    description = Column(String(200), comment="描述")
    category = Column(String(50), default="general", comment="分類")
    is_active = Column(Boolean, default=True, comment="是否啟用")
    created_at = Column(DateTime, server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime, server_default=func.now(), comment="更新時間")


class AIPromptVersion(Base):
    """AI Prompt 版本控制"""
    __tablename__ = "ai_prompt_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    feature = Column(String(50), nullable=False, comment="功能名稱")
    version = Column(Integer, nullable=False, default=1, comment="版本號")
    system_prompt = Column(Text, nullable=False, comment="系統提示詞")
    user_template = Column(Text, nullable=True, comment="使用者提示詞模板")
    is_active = Column(Boolean, default=False, nullable=False, comment="是否為啟用版本")
    description = Column(String(500), nullable=True, comment="版本說明")
    created_by = Column(String(100), nullable=True, comment="建立者")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="建立時間")

    __table_args__ = (
        Index('ix_prompt_feature_active', 'feature', 'is_active'),
        Index('ix_prompt_feature_version', 'feature', 'version'),
    )


class AISearchHistory(Base):
    """AI 搜尋歷史記錄"""
    __tablename__ = "ai_search_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="使用者 ID")
    query = Column(Text, nullable=False, comment="原始查詢文字")
    parsed_intent = Column(JSON, nullable=True, comment="解析後的意圖 JSON")
    results_count = Column(Integer, default=0, comment="搜尋結果數量")
    search_strategy = Column(String(50), nullable=True, comment="搜尋策略")
    source = Column(String(50), nullable=True, comment="來源")
    synonym_expanded = Column(Boolean, default=False, comment="是否同義詞擴展")
    related_entity = Column(String(50), nullable=True, comment="關聯實體")
    latency_ms = Column(Integer, nullable=True, comment="回應時間 ms")
    confidence = Column(Float, nullable=True, comment="意圖信心度")
    feedback_score = Column(Integer, nullable=True, comment="使用者回饋 (1=有用, -1=無用, NULL=未評)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="建立時間")

    if Vector is not None:
        query_embedding = deferred(Column(
            Vector(384),
            nullable=True,
            comment="查詢向量嵌入 (nomic-embed-text, 384 維)",
        ))

    __table_args__ = (
        Index("ix_search_history_user_date", "user_id", "created_at"),
        Index("ix_search_history_created", "created_at"),
    )


class AISynonym(Base):
    """AI 同義詞群組"""
    __tablename__ = "ai_synonyms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False, index=True, comment="分類")
    words = Column(Text, nullable=False, comment="同義詞列表，逗號分隔")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否啟用")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="建立時間")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新時間")
