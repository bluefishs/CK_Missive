-- =====================================================================
-- 清除 contract_projects 同名同年度重複記錄 + 加 UNIQUE constraint
-- =====================================================================
-- 產生：2026-04-15
-- 背景：承攬案件下拉 bug — 同一 project_name + year 存在多筆（如 id=140, 182）
-- 影響：dropdown 顯示重複項；React key 衝突致 Select 渲染錯亂
-- =====================================================================

-- ===== Step 1：盤點重複（先跑看看，勿修改）=====
SELECT project_name, year, COUNT(*) AS dup_count,
       ARRAY_AGG(id ORDER BY id) AS ids,
       ARRAY_AGG(project_code ORDER BY id) AS codes
FROM contract_projects
GROUP BY project_name, year
HAVING COUNT(*) > 1
ORDER BY dup_count DESC, project_name;

-- ===== Step 2：對每組重複，找出哪筆有關聯（documents FK）=====
SELECT cp.id, cp.project_name, cp.year, cp.project_code,
       COUNT(d.id) AS linked_documents
FROM contract_projects cp
LEFT JOIN documents d ON d.contract_project_id = cp.id
WHERE (cp.project_name, cp.year) IN (
    SELECT project_name, year
    FROM contract_projects
    GROUP BY project_name, year
    HAVING COUNT(*) > 1
)
GROUP BY cp.id
ORDER BY cp.project_name, cp.year, linked_documents DESC, cp.id;

-- ===== Step 3（危險操作，須先備份 + 人工確認）=====
-- 策略：保留 linked_documents 最多的那筆；若 tie，保留 id 最大者
-- 刪除無關聯（0 documents）的重複者

BEGIN;

-- 3a. 備份將被刪除的記錄
CREATE TABLE IF NOT EXISTS contract_projects__backup_20260415 AS
SELECT * FROM contract_projects WHERE 1=0;

WITH ranked AS (
    SELECT cp.id,
           cp.project_name,
           cp.year,
           COUNT(d.id) AS doc_count,
           ROW_NUMBER() OVER (
               PARTITION BY cp.project_name, cp.year
               ORDER BY COUNT(d.id) DESC, cp.id DESC
           ) AS rn
    FROM contract_projects cp
    LEFT JOIN documents d ON d.contract_project_id = cp.id
    GROUP BY cp.id
)
-- 先備份
INSERT INTO contract_projects__backup_20260415
SELECT cp.* FROM contract_projects cp
JOIN ranked r ON r.id = cp.id
WHERE r.rn > 1 AND r.doc_count = 0;

-- 3b. 實際刪除（rn>1 且無關聯）
WITH ranked AS (
    SELECT cp.id,
           COUNT(d.id) AS doc_count,
           ROW_NUMBER() OVER (
               PARTITION BY cp.project_name, cp.year
               ORDER BY COUNT(d.id) DESC, cp.id DESC
           ) AS rn
    FROM contract_projects cp
    LEFT JOIN documents d ON d.contract_project_id = cp.id
    GROUP BY cp.id
)
DELETE FROM contract_projects
WHERE id IN (
    SELECT id FROM ranked WHERE rn > 1 AND doc_count = 0
);

-- 3c. 若仍有重複（表示多筆都各有關聯）→ 手動合併；本腳本不自動處理
SELECT project_name, year, COUNT(*)
FROM contract_projects
GROUP BY project_name, year
HAVING COUNT(*) > 1;
-- 若回傳非空，下面 COMMIT 前手動處理這些殘留

-- 3d. 驗證無誤 → COMMIT；若有疑慮 → ROLLBACK
-- COMMIT;
ROLLBACK;   -- 預設 ROLLBACK 防誤殺；人工確認後才改 COMMIT

-- ===== Step 4：加 UNIQUE constraint（根除）=====
-- 先確認所有重複已清除，否則這行會失敗
-- 若有允許同名不同年度 → 用 (project_name, year) 組合
-- 若業務上允許同名同年 → 改加 UNIQUE(project_code) 即可（已有）

-- ALTER TABLE contract_projects
-- ADD CONSTRAINT uq_contract_projects_name_year
-- UNIQUE (project_name, year);

-- 或更寬鬆：僅在 project_code 為 NULL 時檢查（允許部分複製）
-- CREATE UNIQUE INDEX uq_cp_name_year_when_no_code
-- ON contract_projects (project_name, year)
-- WHERE project_code IS NULL;

-- =====================================================================
-- 執行順序建議：
-- 1. pg_dump -t contract_projects -t documents > backup_before_dedupe.sql
-- 2. 執行 Step 1、2 檢視
-- 3. 確認 Step 3 策略正確後，將 ROLLBACK 改為 COMMIT
-- 4. 執行 Step 4 加 constraint
-- 5. 清除 backup: DROP TABLE contract_projects__backup_20260415; (觀察 1 週後)
-- =====================================================================
