"""
資產管理模組 (Asset Management)

- Asset: 資產主檔
- AssetLog: 資產行為紀錄 (採購/維修/保養/調撥/報廢)
"""
from ._base import *


class Asset(Base):
    """資產主檔"""
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_code = Column(String(50), unique=True, nullable=False, index=True, comment="資產編號")
    name = Column(String(200), nullable=False, comment="資產名稱")
    category = Column(String(50), nullable=False, index=True,
                      comment="類別: equipment/vehicle/instrument/furniture/other")
    brand = Column(String(100), comment="品牌")
    model = Column(String(100), comment="型號")
    serial_number = Column(String(100), comment="序號")

    # 財務
    purchase_date = Column(Date, comment="購入日期")
    purchase_amount = Column(Numeric(15, 2), default=0, comment="購入金額")
    current_value = Column(Numeric(15, 2), default=0, comment="目前價值")
    depreciation_rate = Column(Numeric(5, 2), default=0, comment="年折舊率 (%)")

    # 關聯
    expense_invoice_id = Column(Integer, ForeignKey("expense_invoices.id", ondelete="SET NULL"),
                                nullable=True, index=True, comment="關聯發票")
    case_code = Column(String(50), nullable=True, index=True, comment="所屬案件")

    # 狀態
    status = Column(String(30), default="in_use", index=True,
                    comment="狀態: in_use/maintenance/idle/disposed/lost")
    location = Column(String(200), comment="存放位置")
    custodian = Column(String(100), comment="保管人")
    photo_path = Column(String(500), nullable=True, comment="資產照片路徑")
    notes = Column(Text, comment="備註")

    # 時間戳
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    logs = relationship("AssetLog", back_populates="asset", cascade="all, delete-orphan",
                        order_by="AssetLog.action_date.desc()")


class AssetLog(Base):
    """資產行為紀錄"""
    __tablename__ = "asset_logs"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"),
                      nullable=False, index=True, comment="資產 ID")

    action = Column(String(30), nullable=False, index=True,
                    comment="行為: purchase/repair/maintain/transfer/dispose/inspect/other")
    action_date = Column(Date, nullable=False, comment="行為日期")
    description = Column(Text, comment="描述")
    cost = Column(Numeric(15, 2), default=0, comment="費用")

    # 關聯發票
    expense_invoice_id = Column(Integer, ForeignKey("expense_invoices.id", ondelete="SET NULL"),
                                nullable=True, index=True, comment="關聯發票")

    # 調撥資訊
    from_location = Column(String(200), comment="原位置 (調撥用)")
    to_location = Column(String(200), comment="新位置 (調撥用)")

    operator = Column(String(100), comment="操作人")
    notes = Column(Text, comment="備註")

    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    asset = relationship("Asset", back_populates="logs")
