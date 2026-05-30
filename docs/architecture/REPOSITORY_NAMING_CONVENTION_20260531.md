# Repository ↔ db_table 命名規約 SOP（A+C 智能 audit + 規範）

> **觸發**：v6.12 step 70 揭發 covered 13% → smart match 後仍 58% RED
> **設計**：Owner 選 A+C — audit 智能匹配 + 命名規約規範雙做
> **建立**：2026-05-31

---

## 規約 — 命名對應 SSOT

### Rule 1 — 1 model class : 1 repository .py

```
backend/app/extended/models/document.py
  class Document(Base):
    __tablename__ = "documents"

→ 必有 backend/app/repositories/document_repository.py
  class DocumentRepository(BaseRepository[Document]):
    ...
```

### Rule 2 — model 名 → repository 名公式

```
Document       → document_repository.py / DocumentRepository
DocumentAttachment → attachment_repository.py / AttachmentRepository
ContractProject → project_repository.py / ProjectRepository
```

**單複數**：repository 名用**單數**對應 model class 名。

### Rule 3 — 一個 repository 可服務多 model（同 bounded context）

```python
# attachment_repository.py
class AttachmentRepository(BaseRepository[Attachment]):
    # 可同時管 Attachment + AttachmentMetadata（同 bounded context）
    pass
```

但每個 model 必有 import 路徑（from .models import Attachment）讓 smart match 抓到。

### Rule 4 — 子目錄分流（bounded context）

```
backend/app/repositories/
├── document_repository.py
├── taoyuan/
│   ├── dispatch_repository.py
│   ├── work_record_repository.py
│   └── payment_repository.py
└── erp/
    ├── quotation_repository.py
    └── ...
```

子目錄按 bounded context 分流，audit 自動 rglob 抓。

---

## 智能 audit 邏輯（A）

`scripts/checks/repository_coverage_audit.py` 升級：

```python
def list_repo_to_tables() -> dict[str, set[str]]:
    # 1. 抓 models 的 class → __tablename__ 映射
    # 2. 抓 repository 內 `from .models import XxxModel`
    # 3. 抓 repository 內 `self.model = XxxModel`
    # 4. Fallback filename match (向後相容)
```

**升級效果**：
- 修前：filename match only → covered 13%
- 修後：smart match → covered 58% (+45%)

---

## 規範執行（C）

### 4.1 Pre-commit hook（待 v6.13 加）

```bash
# 攔截新增 *_repository.py 不含 model import
if git diff --cached --name-only | grep -qE "_repository\.py$"; then
    bash scripts/checks/repository_naming_check.sh
fi
```

### 4.2 Weekly fitness step 71 候選

`run_fitness_weekly.sh` 加 step 19:
```bash
run_step "19" "repository naming convention" \
    "PYTHONIOENCODING=utf-8 python scripts/checks/repository_coverage_audit.py"
```

連 2 週 RED → LINE 推 owner。

### 4.3 新 model 必走 SOP

加新 model 時 checklist：
- [ ] 寫 `class XxxModel(Base)` + `__tablename__`
- [ ] 寫對應 `xxx_repository.py` + `XxxRepository(BaseRepository[XxxModel])`
- [ ] repository 內 `from .models import XxxModel`
- [ ] 跑 `python scripts/checks/repository_coverage_audit.py` 驗 covered

---

## 修法資產

| 檔案 | 用途 |
|---|---|
| `scripts/checks/repository_coverage_audit.py` | smart match audit (A) |
| `docs/architecture/REPOSITORY_NAMING_CONVENTION_20260531.md` | 本文件 (C) |
| `.claude/rules/cross-file-ssot-governance.md` | §1+§2 加 entry |

---

## 元洞察 — A+C 雙做

| 單做 | 弊端 |
|---|---|
| 只 A（智能 audit）| 規範模糊，新人不知如何寫 |
| 只 C（規範文件）| 沒 audit 強制，規範漂移 |
| **A+C** | **規範 + 智能驗證 = 真正落地** ✓ |

對齊 v6.12 第 2 句「觀測不是奢侈，自治理就是」+ 第 3 句「整合 SSOT 是責任」。

---

> **核心精神**：規範定義邊界 + audit 強制執行 = SSOT 真活。
> A+C 雙做避免「只寫規範沒人遵守」+「只 audit 不知怎麼修」雙缺口。
