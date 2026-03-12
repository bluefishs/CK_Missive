/**
 * useCodeWikiGraph - 圖譜資料載入 Hook
 *
 * 共用於 CodeGraphManagementPage。
 * 封裝 React Query 資料載入、篩選條件 state、以及 client-side edge filter。
 *
 * @version 2.0.0 - React Query 遷移
 */
import { useState, useCallback, useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { aiApi } from '../api/aiApi';
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';
import { filterGraphByRelationTypes } from '../utils/graphFiltering';

export interface UseCodeWikiGraphOptions {
  /** 預設實體類型，預設 ['py_module'] */
  initialEntityTypes?: string[];
  /** 預設關聯類型篩選，預設 [] (不篩選) */
  initialRelTypes?: string[];
}

export interface UseCodeWikiGraphReturn {
  /** 原始圖譜資料 */
  codeWikiData: ExternalGraphData | null;
  /** 篩選後的圖譜資料（edge type filter 已套用） */
  filteredData: ExternalGraphData | null;
  /** 載入中 */
  loading: boolean;
  /** 選中的實體類型 */
  entityTypes: string[];
  setEntityTypes: (types: string[]) => void;
  /** 模組前綴 */
  modulePrefix: string;
  setModulePrefix: (prefix: string) => void;
  /** 選中的關聯類型篩選 */
  relTypes: string[];
  setRelTypes: (types: string[]) => void;
  /** 觸發重新載入 */
  loadCodeWiki: () => void;
}

export function useCodeWikiGraph(
  options: UseCodeWikiGraphOptions = {},
): UseCodeWikiGraphReturn {
  const {
    initialEntityTypes = ['py_module'],
    initialRelTypes = [],
  } = options;

  const queryClient = useQueryClient();

  const [entityTypes, setEntityTypes] = useState<string[]>(initialEntityTypes);
  const [modulePrefix, setModulePrefix] = useState('');
  const [relTypes, setRelTypes] = useState<string[]>(initialRelTypes);

  const trimmedPrefix = (typeof modulePrefix === 'string' ? modulePrefix.trim() : '') || null;

  const { data: codeWikiData = null, isLoading: loading } = useQuery({
    queryKey: ['code-wiki-graph', entityTypes, trimmedPrefix],
    queryFn: async () => {
      const result = await aiApi.getCodeWikiGraph({
        entity_types: entityTypes,
        module_prefix: trimmedPrefix,
        limit: 500,
      });
      if (result?.success) {
        return { nodes: result.nodes, edges: result.edges } as ExternalGraphData;
      }
      return { nodes: [], edges: [] } as ExternalGraphData;
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const filteredData = useMemo(
    () => filterGraphByRelationTypes(codeWikiData, relTypes),
    [codeWikiData, relTypes],
  );

  const loadCodeWiki = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['code-wiki-graph'] });
  }, [queryClient]);

  return {
    codeWikiData,
    filteredData,
    loading,
    entityTypes,
    setEntityTypes,
    modulePrefix,
    setModulePrefix,
    relTypes,
    setRelTypes,
    loadCodeWiki,
  };
}
