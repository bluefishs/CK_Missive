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
}

export function useGraphSearch({ rawNodes }: UseGraphSearchOptions): UseGraphSearchReturn {
  const { message } = App.useApp();

  const [searchText, setSearchText] = useState('');
  const [apiSearchMatchIds, setApiSearchMatchIds] = useState<Set<string> | null>(null);
  const [apiSearching, setApiSearching] = useState(false);

  // Local search matching (instant, as user types)
  const localSearchMatchIds = useMemo(() => {
    if (!searchText.trim()) return null;
    const lower = searchText.toLowerCase();
    const ids = new Set<string>();
    for (const node of rawNodes) {
      if (
        node.label.toLowerCase().includes(lower) ||
        (node.doc_number && node.doc_number.toLowerCase().includes(lower))
      ) {
        ids.add(node.id);
      }
    }
    return ids;
  }, [searchText, rawNodes]);

  // API search (Enter-triggered, includes synonym expansion)
  const handleSearchSubmit = useCallback(async () => {
    const q = searchText.trim();
    if (!q) {
      setApiSearchMatchIds(null);
      return;
    }
    setApiSearching(true);
    try {
      const result = await aiApi.searchGraphEntities({ query: q, limit: 30 });
      if (result?.results?.length > 0) {
        // Map API-returned entity names to existing graph nodes
        const matchedNames = new Set(result.results.map((r: { canonical_name: string }) => r.canonical_name.toLowerCase()));
        const ids = new Set<string>();
        for (const node of rawNodes) {
          if (matchedNames.has(node.label.toLowerCase())) {
            ids.add(node.id);
          }
        }
        setApiSearchMatchIds(ids.size > 0 ? ids : null);
        if (ids.size === 0) {
          message.info(`找到 ${result.results.length} 個正規化實體，但不在目前圖譜中`);
        }
      } else {
        setApiSearchMatchIds(null);
        message.info('未找到匹配的正規化實體');
      }
    } catch {
      // Silently fall back to local search on API failure
      setApiSearchMatchIds(null);
    } finally {
      setApiSearching(false);
    }
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
  };
}
