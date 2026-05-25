# 專案架構、服務層、模組化與系統規範 (SKILLs) 整體建議

## 摘要

本文件旨在對 `CK_Missive` 專案的現有架構進行全面性檢視，並針對**服務層抽象**、**後端模組化**、**系統核心規範 (SKILLs) 的彈性**以及**整體開發維運效率**提出具體優化建議。

當前專案是一個結構複雜但功能強大的混合系統，結合了高效能的 C++ 核心（用於遊戲/AI 邏輯）與靈活的 Python Web 後端。主要挑戰在於如何降低各模組間的耦合度、提升系統的可維護性與擴展性。

**核心建議方向：**
1.  在 Python 後端導入明確的**服務層 (Service Layer)**，將業務邏輯與 API 端點分離。
2.  深化後端**模組化**，建立更清晰的職責劃分，例如將 AI 邏輯互動、資料庫操作等封裝為獨立模組。
3.  將 C++ 中硬編碼的**遊戲規範 (SKILLs) 數據化/外部化**，從而實現不需重新編譯核心程式碼即可調整遊戲平衡與內容。
4.  統一與簡化**設定檔管理**和**啟動流程**，降低開發與部署的複雜性。

## 1. 現有架構分析

### 1.1. 技術棧與組件
- **前端 (Frontend)**: 一個獨立的 JavaScript 應用程式，負責使用者介面。
- **後端 (Backend)**: 一個 Python 應用程式 (可能為 FastAPI/Flask)，負責處理 API 請求、業務邏輯與用戶管理。
- **核心邏輯 (Core Logic/SDK)**: 一個 C++ 函式庫 (`src` 目錄)，定義了遊戲的核心機制 (魚、技能、戰鬥規則)，並透過 `pybind11` 暴露介面給 Python。
- **資料庫 (Database)**: 一個 SQL 資料庫 (從 `alembic.ini` 和 `*.sql` 文件推斷)，用於持久化儲存。
- **部署 (Deployment)**: 使用 Docker 和 Docker Compose 進行容器化部署，並由 Nginx 作為反向代理。

### 1.2. 專案結構
專案採用 Monorepo 結構，將前端、後端及核心 SDK 置於同一倉儲中，便於統一管理。目錄結構清晰，但後端 `app` 目錄內部可以進一步優化職責劃分。

### 1.3. 數據流與互動
1.  **使用者操作**: `Frontend` -> `Backend (API)`
2.  **業務/遊戲邏輯處理**: `Backend (API)` -> `C++ SDK (via pybind11)`
3.  **數據持久化**: `Backend` -> `Database`
4.  **AI 決策**: `C++ SDK` 可能會呼叫 Python 端實現的 AI 策略 (如 `PyAIClient` 所示)。

## 2. 核心領域建議

### 2.1. 服務層 (Service Layer) 導入

**現狀**: 業務邏輯可能散落在 API 視圖函式中，導致邏輯重複、測試困難。

**建議**:
在 Python 後端 `app` 目錄下建立一個 `services` 子目錄。將相關的業務邏輯封裝成服務類別 (Service Class)。

**範例**:
```python
# app/services/game_service.py
from ..core import cpp_sdk  # 假設這是 pybind11 模組

class GameService:
    def get_fish_details(self, fish_id: int):
        # ... 處理從資料庫或 SDK 獲取魚的詳細資訊 ...
        pass

    def perform_action(self, user_id: int, action_info: dict):
        # ... 驗證使用者權限 ...
        # ... 呼叫 C++ SDK 執行動作 ...
        result = cpp_sdk.execute_action(...)
        # ... 更新資料庫狀態 ...
        return result

# app/api/endpoints/game.py
# 路由層只負責接收請求、調用服務並返回響應
@router.post("/action")
def take_action(action: ActionModel, game_service: GameService = Depends()):
    result = game_service.perform_action(current_user.id, action.dict())
    return {"status": "success", "data": result}
```

**優點**:
- **職責分離 (SoC)**: API 層只管 HTTP 協議，服務層只管業務邏輯。
- **可重用性**: 多個 API 端點可以共用同一個服務。
- **易於測試**: 可以獨立測試服務層，無需啟動 Web 伺服器。

### 2.2. 後端模組化深化

**現狀**: `backend/app` 的內部結構可以更具體化，以應對日益複雜的系統。

**建議**:
將 `backend/app` 目錄結構調整為更符合現代 Python 應用程式的實踐。

```
backend/app/
├── api/              # API 端點 (路由)
│   ├── dependencies.py
│   └── endpoints/
│       ├── users.py
│       └── game.py
├── core/             # 核心設定、資料庫連線、C++ SDK 綁定初始化
│   ├── config.py
│   └── cpp_sdk.py
├── models/           # SQLAlchemy 或其他 ORM 的資料庫模型
│   ├── user.py
│   └── fish.py
├── schemas/          # Pydantic 等數據驗證模型
│   ├── user.py
│   └── game.py
├── services/         # 業務邏輯服務 (如 2.1 所述)
│   ├── user_service.py
│   └── game_service.py
└── main.py           # 應用程式啟動入口
```

**優點**:
- **高內聚，低耦合**: 相關功能的程式碼被組織在一起。
- **可讀性與可維護性**: 新進開發者能更快地理解專案結構和程式碼位置。

### 2.3. 系統規範 (SKILLs) - 數據驅動設計

**現狀**: 魚的種類、技能 (`active_skill`, `passive_skill`, `FishBuff`) 等核心遊戲數值和規則直接在 C++ `enum` 和 `struct` 中硬編碼。

**建議**:
將這些遊戲實體和規則從程式碼中分離出來，採用**數據驅動 (Data-Driven)** 的設計模式。將它們定義在外部設定檔 (如 JSON, YAML) 或資料庫中。

**範例 (`skills.json`)**:
```json
{
  "fish_types": [
    { "id": 1, "name": "spray", "display_name": "射水魚" },
    { "id": 2, "name": "flame", "display_name": "噴火魚" }
  ],
  "active_skills": {
    "range_attack": {
      "id": 0,
      "name": "範圍攻擊",
      "description": "對多個目標造成傷害。",
      "requirements": ["spray", "eel"]
    },
    "critical_attack": {
      "id": 2,
      "name": "致命一擊",
      "description": "造成大量單體傷害。",
      "requirements": ["barracuda"]
    }
  },
  "fish_buffs": {
    "SWELL": { "id": 1, "description": "膨脹" },
    "HEAL": { "id": 2, "description": "生命低於10%時自動恢復15%血量 (1層)" }
  }
}
```

C++ 核心在啟動時讀取並載入這些設定。

**優點**:
- **靈活性與迭代速度**: 遊戲設計師或維運人員可以直接修改 JSON 檔案來調整遊戲平衡、新增魚種或技能，**無需重新編譯 C++ 核心**。
- **清晰性**: 遊戲規則與底層程式邏輯分離，使兩者都更清晰。
- **可擴展性**: 新增一個技能只需要在設定檔中增加一個條目，而不需要修改 `enum` 和相關的 `switch-case` 邏輯。

## 3. 整體性與其他建議

### 3.1. 統一設定檔與啟動腳本
專案根目錄下有多個 `docker-compose.*.yml` 檔案和啟動腳本 (`.sh`, `.ps1`, `.bat`)。這增加了理解和維護的複雜性。

**建議**:
- 參考 `UNIFIED_CONFIG_GUIDE.md` 的思路，盡可能合併 `docker-compose` 檔案。使用一個基礎的 `docker-compose.yml`，並為不同環境 (開發、測試、生產) 建立 `docker-compose.override.yml`。
- 簡化啟動腳本，提供一個主要的入口腳本 (如 `manage.py` 或 `task.py`) 來處理啟動、資料庫遷移、建立使用者等常見任務。

### 3.2. 強化 CI/CD 與整合測試
擁有 C++ 核心和 Python 後端的混合專案，整合測試至關重要。

**建議**:
- 建立一個 CI (持續整合) pipeline (例如使用 GitHub Actions)，在每次程式碼提交時自動執行以下操作：
    1.  編譯 C++ 核心。
    2.  執行 C++ 單元測試。
    3.  安裝 Python 依賴。
    4.  執行 Python 單元測試 (特別是 `services` 層)。
    5.  執行 **整合測試**，確保 Python 調用 C++ SDK 的行為符合預期。

### 3.3. 文件與程式碼同步
專案已有良好的文件傳統。當採納數據驅動設計後，設定檔本身即成為了 "活的文件"。

**建議**:
- 為數據設定檔 (如 `skills.json`) 建立 `README.md`，解釋每個欄位的意義和可選值。
- 自動化產生部分文件，例如，可以寫一個腳本，讀取 `skills.json` 並產生 MarkDown 格式的技能列表。

## 結論

本專案具備堅實的基礎，但隨著功能的擴展，引入更嚴格的軟體工程實踐將帶來長遠的效益。透過**服務層抽象**、**深度模組化**以及將**核心規則數據化**，可以顯著提升系統的靈活性、可維護性和開發效率，讓開發團隊能更專注於實現創新的功能，而非應付日益增長的技術債。