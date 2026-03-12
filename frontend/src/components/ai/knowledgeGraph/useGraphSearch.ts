/**
 * useGraphSearch - Knowledge Graph search logic hook
 *
 * Extracts local search (instant matching) and API search (Enter-triggered,
 * with synonym expansion) from KnowledgeGraph.tsx.
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

import { useState, useMemo, useCallback } from 'react';
import { App } from 'antd';
import { aiApi } from '../../../api/aiApi';
import type { GraphNode } from '../../../types/ai';

export interface UseGraphSearchOptions {
  rawNodes: GraphNode[];
}

export interface UseGraphSearchReturn {
  searchText: string;
  setSearchText: React.Dispatch<React.SetStateAction<string>>;
  localSearchMatchIds: Set<string> | null;
  apiSearchMatchIds: Set<string> | null;
  setApiSearchMatchIds: React.Dispatch<React.SetStateAction<Set<string> | null>>;
  apiSearching: boolean;
  handleSearchSubmit: () => Promise<void>;
  /** Merged result: API results take priority, falls back to local */
  searchMatchIds: Set<string> | null;
  /** 別名命中提示（當搜尋結果的 canonical_name 與查詢顯著不同時） */
  aliasHint: string | null;
}

export function useGraphSearch({ rawNodes }: UseGraphSearchOptions): UseGraphSearchReturn {
  const { message } = App.useApp();

  const [searchText, setSearchText] = useState('');
  const [apiSearchMatchIds, setApiSearchMatchIds] = useState<Set<string> | null>(null);
  const [apiSearching, setApiSearching] = useState(false);
  const [aliasHint, setAliasHint] = useState<string | null>(null);

  // Local search matching (instant, as user types)
  const localSearchMatchIds = useMemo(() => {
    if (!searchText.trim()) return null;
    const lower = searchText.toLowerCase();
    const ids = new Set<string>();

    // 提取派工單號數字（如 "派工單007" → "007"）
    const dispatchNoMatch = searchText.match(/派工[單]?\s*[號]?\s*(\d+)/);
    const dispatchNum = dispatchNoMatch?.[1];

    for (const node of rawNodes) {
      const labelLower = node.label.toLowerCase();
      if (
        labelLower.includes(lower) ||
        (node.doc_number && node.doc_number.toLowerCase().includes(lower))
      ) {
        ids.add(node.id);
      }
      // 派工單號智慧匹配：搜尋 "派工單007" 能命中 label "派工 115年_派工單號007"
      else if (dispatchNum && node.type === 'dispatch' && labelLower.includes(dispatchNum)) {
        ids.add(node.id);
      }
    }
    return ids;
  }, [searchText, rawNodes]);

  // API search (Enter-triggered, includes synonym expansion)
  // 合併 API 結果 + 本地節點匹配（派工單/公文等非 canonical_entity 節點只能本地命中）
  const handleSearchSubmit = useCallback(async () => {
    const q = searchText.trim();
    if (!q) {
      setApiSearchMatchIds(null);
      setAliasHint(null);
      return;
    }
    setApiSearching(true);
    setAliasHint(null);

    // 1. 本地節點搜尋（涵蓋派工單、公文、桃園工程等非 canonical 節點）
    const qLower = q.toLowerCase();
    const dispatchMatch = q.match(/派工[單]?\s*[號]?\s*(\d+)/);
    const dNum = dispatchMatch?.[1];
    const localIds = new Set<string>();
    for (const node of rawNodes) {
      const labelLower = node.label.toLowerCase();
      if (
        labelLower.includes(qLower) ||
        (node.doc_number && node.doc_number.toLowerCase().includes(qLower))
      ) {
        localIds.add(node.id);
      } else if (dNum && node.type === 'dispatch' && labelLower.includes(dNum)) {
        localIds.add(node.id);
      }
    }

    try {
      const result = await aiApi.searchGraphEntities({ query: q, limit: 30 });
      const apiIds = new Set<string>();
      if (result?.results?.length > 0) {
        // Map API-returned entity names to existing graph nodes
        const matchedNames = new Set(result.results.map((r: { canonical_name: string }) => r.canonical_name.toLowerCase()));
        for (const node of rawNodes) {
          if (matchedNames.has(node.label.toLowerCase())) {
            apiIds.add(node.id);
          }
        }

        // 別名命中提示：僅當 API 有命中且 canonical_name 與查詢明顯不同
        // 短查詢（≤3字）且結果差異大時不顯示（避免 "007" → 無關實體的誤導提示）
        if (apiIds.size > 0) {
          const aliasMatch = result.results.find(
            (r: { canonical_name: string }) =>
              !r.canonical_name.toLowerCase().includes(qLower) &&
              !qLower.includes(r.canonical_name.toLowerCase()),
          );
          if (aliasMatch && q.length > 3) {
            setAliasHint(`別名命中：${q} → ${aliasMatch.canonical_name}`);
          }
        }
      }

      // 2. 合併：API 命中 + 本地命中
      const merged = new Set([...apiIds, ...localIds]);
      if (merged.size > 0) {
        setApiSearchMatchIds(merged);
      } else {
        setApiSearchMatchIds(null);
        message.info('未找到匹配的節點');
      }
    } catch {
      // API 失敗時使用本地結果
      setApiSearchMatchIds(localIds.size > 0 ? localIds : null);
    } finally {
      setApiSearching(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchText, rawNodes]);

  // Merged: API results take priority; fall back to local
  const searchMatchIds = apiSearchMatchIds ?? localSearchMatchIds;

  return {
    searchText,
    setSearchText,
    localSearchMatchIds,
    apiSearchMatchIds,
    setApiSearchMatchIds,
    apiSearching,
    handleSearchSubmit,
    searchMatchIds,
    aliasHint,
  };
}
