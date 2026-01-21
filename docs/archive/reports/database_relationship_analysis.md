# 資料庫關聯結構分析與建議

## 目前狀況
- ContractProject 與 User 之間**沒有直接關聯**
- 公文系統中的"業務同仁"欄位無法正確對應到資料庫

## 建議的資料庫結構改進

### 方案一：簡單外鍵關聯
```sql
-- 在 contract_projects 表中增加欄位
ALTER TABLE contract_projects
ADD COLUMN assigned_user_id INTEGER REFERENCES users(id);
ADD COLUMN project_manager_id INTEGER REFERENCES users(id);
```

### 方案二：多對多關聯表 (推薦)
```sql
-- 建立專案成員關聯表
CREATE TABLE project_user_assignments (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES contract_projects(id),
    user_id INTEGER REFERENCES users(id),
    role VARCHAR(50) NOT NULL, -- '專案經理', '業務承辦', '技術負責人'
    assignment_date DATE DEFAULT CURRENT_DATE,
    is_primary BOOLEAN DEFAULT FALSE, -- 是否為主要負責人
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, user_id, role)
);
```

### 方案三：擴充 User 模型
```python
# 在 User 模型中增加欄位
class User(Base):
    # ... 現有欄位 ...
    department = Column(String(100), comment="所屬部門")
    job_title = Column(String(100), comment="職稱")
    employee_id = Column(String(50), unique=True, comment="員工編號")

    # 關聯到專案
    assigned_projects = relationship(
        "ContractProject",
        secondary="project_user_assignments",
        back_populates="assigned_users"
    )
```

## 公文系統整合建議

### DocumentOperations.tsx 中的業務同仁欄位應該：
1. 從 `/api/users?role=business` 獲取業務人員清單
2. 或從 `/api/project-members/{project_id}` 獲取專案成員
3. 儲存 `user_id` 而非 `full_name` 字串

### API 端點建議：
- `GET /api/users/business-staff` - 獲取業務人員清單
- `GET /api/projects/{id}/members` - 獲取專案成員
- `POST /api/projects/{id}/assign-member` - 指派成員到專案