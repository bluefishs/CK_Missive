# 專案編號規範

> 版本：1.1.0
> 建立日期：2026-01-06
> 最後更新：2026-01-08
> 原始檔案：`@PROJECT_CODE_SPEC.md` (已遷移)

---

## 一、編號格式

```
CK{年度4碼}_{類別2碼}_{性質2碼}_{流水號3碼}
```

### 範例解析

```
CK2025_03_01_002
│ │    │  │  └── 流水號: 002 (該組合的第2筆)
│ │    │  └───── 性質: 01 (測量案)
│ │    └──────── 類別: 03 (小額採購)
│ └───────────── 年度: 2025
└─────────────── 公司代碼: CK (乾坤)
```

---

## 二、代碼對照表

### 2.1 案件類別 (category)

| 代碼 | 說明 |
|------|------|
| 01 | 委辦案件 |
| 02 | 協力計畫 |
| 03 | 小額採購 |
| 04 | 其他類別 |

### 2.2 案件性質 (case_nature)

| 代碼 | 說明 |
|------|------|
| 01 | 測量案 |
| 02 | 資訊案 |
| 03 | 複合案 |

---

## 三、產生邏輯

```python
# project_service.py

async def _generate_project_code(
    self,
    db: AsyncSession,
    year: int,           # 年度 (如 2025)
    category: str,       # 類別代碼 (如 "01")
    case_nature: str     # 性質代碼 (如 "01")
) -> str:
    # 1. 組合前綴
    year_str = str(year)
    category_code = category[:2] if category else "00"
    nature_code = case_nature[:2] if case_nature else "00"
    prefix = f"CK{year_str}_{category_code}_{nature_code}_"
    # 例: CK2025_01_01_

    # 2. 查詢同組合的最大流水號
    query = select(ContractProject.project_code).where(
        ContractProject.project_code.like(f"{prefix}%")
    ).order_by(ContractProject.project_code.desc())

    # 3. 計算新流水號
    if existing_codes:
        last_serial = int(existing_codes[0].split("_")[-1])
        new_serial = last_serial + 1
    else:
        new_serial = 1

    # 4. 回傳完整編號
    return f"{prefix}{str(new_serial).zfill(3)}"
```

---

## 四、資料庫欄位

```python
# models.py
class ContractProject(Base):
    project_code = Column(
        String(100),
        unique=True,  # 唯一索引
        comment="專案編號: CK{年度}_{類別}_{性質}_{流水號}"
    )
    category = Column(String(50), comment="案件類別")
    case_nature = Column(String(50), comment="案件性質")
```

---

## 五、常見編號範例

| 編號 | 解讀 |
|------|------|
| `CK2025_01_01_001` | 2025年 委辦案件 測量案 第1筆 |
| `CK2025_01_02_003` | 2025年 委辦案件 資訊案 第3筆 |
| `CK2025_02_03_001` | 2025年 協力計畫 複合案 第1筆 |
| `CK2025_03_01_002` | 2025年 小額採購 測量案 第2筆 |
| `CK2024_04_01_015` | 2024年 其他類別 測量案 第15筆 |

---

## 六、注意事項

1. **唯一性**：`project_code` 有 unique 約束，不可重複
2. **自動產生**：若建立專案時未提供編號，系統會自動產生
3. **流水號**：同一年度、類別、性質組合下依序遞增
4. **最大容量**：每組合最多 999 筆 (001-999)

---

## 七、相關文件

| 文件 | 說明 |
|------|------|
| `docs/DEVELOPMENT_STANDARDS.md` | 統一開發規範總綱 |
| `docs/specifications/TYPE_CONSISTENCY.md` | 型別一致性規範 |
| `backend/app/services/project_service.py` | 專案服務模組 |

---

## 八、版本歷史

| 版本 | 日期 | 變更內容 |
|------|------|----------|
| 1.1.0 | 2026-01-08 | 遷移至 docs/specifications/ 目錄 |
| 1.0.0 | 2026-01-06 | 初版建立 |

---

*文件維護: Claude Code Assistant*
