-- KG 實體合併率監測（connector 治本 commit 7101ee3c 後行為觀察）
--
-- 背景：2026-07-10 修 KG embedding connector=None，啟用 canonical_entity_resolver /
--       cross_domain_matcher 的「語意匹配/去重」（ingest 時實體解析）。此前該路徑空轉，
--       故現在起 ingest 可能把語意相近的名稱合併到既有 canonical entity（記為 auto 別名，
--       confidence < 1.0）。若語意閾值過寬 → 把「真正不同的實體」誤合併（over-merge）。
--
-- 用法（從 repo 根目錄）：
--   docker exec -i ck_missive_postgres psql -U ck_user -d ck_documents < scripts/checks/kg_merge_rate_monitor.sql
--
-- 基線（2026-07-15 治本部署當日）：
--   entities_total 48551 / new_entities_24h 422 / aliases_total 21583
--   new_aliases_24h 403（幾乎全 federation）/ new_semantic_aliases_24h 0
--   alias_per_entity 0.4445 / embedding_coverage 95.8%
--   歷史 auto 語意別名（confidence<0.90）累計僅 40 筆、日建立 1-9 筆
--
-- 觀察重點（over-merge 預警）：
--   * new_semantic_aliases_24h 若連日 >> 個位數（例如 >50/日）＝語意匹配開始大量合併，需抽樣人工核實
--   * alias_per_entity 明顯上升 + new_entities_24h 明顯下滑＝distinct 實體被吸收（合併過度）
--   * 抽樣核實見底部 query B
--   * 回退：git revert 7101ee3c + rebuild backend（L76）

-- === Query A：每日快照（跑這支對照基線）===
SELECT
  NOW()::date AS snapshot_date,
  (SELECT COUNT(*) FROM canonical_entities) AS entities_total,
  (SELECT COUNT(*) FROM canonical_entities WHERE created_at >= NOW()-INTERVAL '24 hours') AS new_entities_24h,
  (SELECT COUNT(*) FROM entity_aliases) AS aliases_total,
  (SELECT COUNT(*) FROM entity_aliases WHERE created_at >= NOW()-INTERVAL '24 hours') AS new_aliases_24h,
  (SELECT COUNT(*) FROM entity_aliases
     WHERE source='auto' AND confidence < 1.0
       AND created_at >= NOW()-INTERVAL '24 hours') AS new_semantic_aliases_24h,
  ROUND((SELECT COUNT(*) FROM entity_aliases)::numeric
        / NULLIF((SELECT COUNT(*) FROM canonical_entities),0), 4) AS alias_per_entity,
  ROUND((SELECT COUNT(embedding)*100.0/COUNT(*) FROM canonical_entities)::numeric,1) AS embedding_coverage_pct;

-- === Query B：抽樣近 24h 語意合併的別名（人工核實「合併對不對」）===
-- 看 alias_name 與被合併到的 canonical_name 是否「真的是同一個實體」；
-- 若出現明顯不同實體被綁在一起（例如兩個不同機關/廠商）＝over-merge，考慮收緊 kg_semantic_distance 或回退。
SELECT a.confidence,
       a.alias_name,
       ce.canonical_name AS merged_into,
       ce.entity_type,
       ce.graph_domain,
       a.created_at
FROM entity_aliases a
JOIN canonical_entities ce ON ce.id = a.canonical_entity_id
WHERE a.source='auto' AND a.confidence < 1.0
  AND a.created_at >= NOW()-INTERVAL '24 hours'
ORDER BY a.confidence ASC, a.created_at DESC
LIMIT 50;
