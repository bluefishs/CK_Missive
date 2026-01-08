# CK_Missive 專案整體架構優化建議書

## 1. 總覽與目標

本文件旨在對 CK_Missive 專案目前的架構進行全面性檢視，並根據現代化的軟體工程實踐，提出一系列優化建議。目標是提升系統的 **模組化程度**、**可維護性**、**可擴展性** 與 **開發效率**。

**目前技術堆疊總結：**
- **後端:** Python (FastAPI), SQLAlchemy (ORM), PostgreSQL (資料庫), Celery (非同步任務)
- **前端:** React, TypeScript, Vite (建置工具), Ant Design (UI 框架), Zustand (狀態管理)

此技術選型非常出色，為高效能、高效率的開發奠定了堅實基礎。以下建議將基於現有技術堆疊進行深化與標準化。

---

## 2. 系統模組化與服務層 (後端)

目前的後端結構雖然遵循了 FastAPI 的基本實踐，但可以透過引入更明確的 **分層架構 (Layered Architecture)** 來進一步提升模組化程度。

**建議架構分層：**

```
backend/app/
├── api/            # API 層 (Routers) - 處理 HTTP 請求與回應
│   └── v1/
│       ├── endpoints/
│       │   ├── users.py
│       │   └── documents.py
│       └── deps.py       # API 依賴注入 (例如：取得目前使用者)
├── services/       # 服務層 - 核心業務邏輯
│   ├── user_service.py
│   └── document_service.py
├── crud/           # CRUD 層 (或稱 Repositories) - 專職與資料庫互動
│   ├── crud_user.py
│   └── crud_document.py
├── models/         # 模型層 - SQLAlchemy 的資料庫模型
│   ├── user.py
│   └── document.py
├── schemas/        # 結構層 - Pydantic 的資料驗證模型
│   ├── user_schema.py
│   └── document_schema.py
├── core/           # 核心配置層
│   ├── config.py
│   └── security.py
└── db/             # 資料庫連線管理
    └── session.py
```

**核心優勢：**

1.  **關注點分離 (SoC):**
    - `api` 層只負責處理 Web 相關事務（解析請求、回傳 JSON）。
    - `services` 層封裝所有業務規則，不直接接觸資料庫。
    - `crud` 層提供原子化的資料庫操作，讓 `services` 層可以重複使用。
2.  **可測試性:** 可以針對 `services` 層撰寫單元測試，並 Mock `crud` 層的行為，而無需實際的資料庫連線。
3.  **可維護性:** 當業務邏輯變更時，只需修改對應的 `service`。當資料庫查詢需要優化時，只需修改 `crud` 層。

**實作範例 (建立使用者):**

1.  **`api/v1/endpoints/users.py`:**
    ```python
    @router.post("/")
    def create_user(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
        return user_service.create_user(db=db, user_in=user_in)
    ```
2.  **`services/user_service.py`:**
    ```python
    from app import crud, schemas

    def create_user(db: Session, user_in: schemas.UserCreate):
        # 業務邏輯：檢查 email 是否已存在、密碼加密等
        if crud.user.get_by_email(db, email=user_in.email):
            raise HTTPException(status_code=400, detail="Email already registered.")
        
        # ... 其他業務邏輯 ...

        return crud.user.create(db=db, obj_in=user_in)
    ```
3.  **`crud/crud_user.py`:**
    ```python
    def create(db: Session, obj_in: schemas.UserCreate) -> models.User:
        # 僅包含資料庫操作
        hashed_password = security.get_password_hash(obj_in.password)
        db_obj = models.User(email=obj_in.email, hashed_password=hashed_password)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    ```

---

## 3. 資料庫 (Database)

專案已正確使用 SQLAlchemy 和 Alembic，這是最佳實踐。

**建議事項：**

1.  **索引優化:** 發現 `database_indexes_optimization.sql` 檔案。建議將這些索引的建立直接整合到 Alembic 的遷移腳本中，以確保每次部署都能自動應用，而不是手動執行。
2.  **連線池管理:** 確保 FastAPI 的資料庫 `Session` 是透過依賴注入 (`Depends`) 方式在每個請求中建立與關閉，以有效利用 SQLAlchemy 的連線池。
3.  **異步驅動:** 目前使用 `psycopg2-binary` (同步)。為了完全發揮 FastAPI 的非同步優勢，長遠來看，應考慮遷移至 `asyncpg` (非同步)。這需要將所有資料庫操作 `def` 改為 `async def`，並使用 `await`。
    - **注意:** 這是一個較大的重構，建議在未來的主要版本升級中規劃。

---

## 4. Google Calendar 整合

專案中已包含 Google API 相關套件，這是一個很好的開始。

**建議實作策略：**

1.  **專門模組:** 在後端建立一個專門處理 Google Calendar 整合的服務模組：
    - `backend/app/services/google_calendar_service.py`
2.  **安全配置:**
    - **絕對不要** 將 `client_secret.json` 或任何 API 金鑰直接寫在程式碼中。
    - 應將金鑰儲存在環境變數 (`.env`) 中，並透過 Pydantic 的 `Settings` 模型來載入。
3.  **認證流程 (OAuth 2.0):**
    - 建立 API 端點來處理 OAuth 2.0 的流程，例如：
        - `GET /api/v1/calendar/auth/start`: 將使用者重導向到 Google 的授權頁面。
        - `GET /api/v1/calendar/auth/callback`: 接收 Google 的回調，用授權碼換取 `access_token` 和 `refresh_token`。
    - 將 `access_token` 和 `refresh_token` 安全地儲存在資料庫中，與使用者關聯。
4.  **API 封裝:** 在 `google_calendar_service.py` 中，建立函式來封裝對 Google Calendar API 的呼叫，例如：
    - `get_events(user_id: int, start_time: datetime, end_time: datetime)`
    - `create_event(user_id: int, event_data: dict)`
    - 服務內部會自動處理 `access_token` 的取得與刷新。
5.  **前端整合:**
    - 前端頁面提供一個「連結 Google 日曆」的按鈕，點擊後呼叫後端的 `/auth/start` 端點。
    - 成功授權後，前端即可呼叫後端封裝好的 API (`/api/v1/calendar/events`) 來顯示或操作日曆事件。

---

## 5. 響應式網頁設計 (RWD)

前端使用 Ant Design，這為 RWD 提供了強大的內建支援。

**建議實作策略：**

1.  **善用 Grid 系統:** Ant Design 的 `<Grid>` 元件是 RWD 的基礎。使用其 `xs`, `sm`, `md`, `lg`, `xl`, `xxl` 屬性來定義在不同螢幕尺寸下的欄位佔比。
    ```jsx
    import { Row, Col } from 'antd';

    <Row>
      <Col xs={24} md={12} lg={8}>區塊一</Col>
      <Col xs={24} md={12} lg={8}>區塊二</Col>
      <Col xs={24} md={24} lg={8}>區塊三</Col>
    </Row>
    ```
2.  **使用 `useBreakpoint` Hook:** 在需要根據螢幕尺寸動態調整元件行為或樣式時，`useBreakpoint` 是一個非常有用的工具。
    ```jsx
    import { Grid } from 'antd';
    const { useBreakpoint } = Grid;

    function MyComponent() {
      const screens = useBreakpoint();
      const isMobile = !screens.md; // 當螢幕寬度小於 md (768px)

      return (
        <Button size={isMobile ? 'small' : 'large'}>
          {isMobile ? 'Mobile View' : 'Desktop View'}
        </Button>
      );
    }
    ```
3.  **行動裝置優先:** 在設計新頁面或元件時，優先考慮它在小螢幕上的外觀和行為，然後再擴展到大螢幕。
4.  **圖片與媒體:** 確保所有圖片和媒體都設定了 `max-width: 100%`，以避免在小螢幕上溢出。
5.  **導覽列:** 對於主導覽列，在行動裝置上應自動收合為漢堡選單 (Hamburger Menu)。Ant Design 的 `<Menu>` 元件支援此功能。

---

## 6. 總結與後續步驟

本建議書提出了一個更清晰、更穩健的專案架構。

**建議的實施順序：**

1.  **第一階段 (後端重構):**
    - 建立 `services` 和 `crud` 目錄結構。
    - 選擇一個較小的功能模組 (例如：使用者管理)，將其業務邏輯從 API 層遷移到 `user_service.py`，資料庫操作遷移到 `crud_user.py`。
    - 確保測試通過，驗證新架構的可行性。
2.  **第二階段 (Google Calendar):**
    - 遵循建議的策略，在後端建立安全的認證流程與服務封裝。
    - 在前端建立對應的授權觸發與資料顯示頁面。
3.  **第三階段 (RWD 優化):**
    - 全面檢視現有頁面，特別是資料表格、表單和儀表板。
    - 使用 Ant Design 的 Grid 系統和 `useBreakpoint` Hook 來優化它們在行動裝置上的顯示效果。

透過分階段實施這些建議，可以在不中斷現有開發的情況下，逐步提升專案的整體品質與生命週期。
