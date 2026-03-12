/**
 * 圖譜資料過濾工具 — KnowledgeGraphPage / CodeGraphManagementPage 共用
 */
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';

/**
 * 依關聯類型篩選圖譜邊，並移除未參與的節點。
 * @param data 原始圖譜資料
 * @param allowedRelTypes 允許的關聯類型（空陣列 = 不篩選）
 */
export function filterGraphByRelationTypes(
  data: ExternalGraphData | null,
  allowedRelTypes: string[],
): ExternalGraphData | null {
  if (!data) return null;
  if (allowedRelTypes.length === 0) return data;

  const allowed = new Set(allowedRelTypes);
  const filteredEdges = data.edges.filter((e) => allowed.has(e.type));

  const nodeIds = new Set<string>();
  for (const e of filteredEdges) {
    nodeIds.add(e.source);
    nodeIds.add(e.target);
  }

  const filteredNodes = data.nodes.filter((n) => nodeIds.has(n.id));
  return { nodes: filteredNodes, edges: filteredEdges };
}
