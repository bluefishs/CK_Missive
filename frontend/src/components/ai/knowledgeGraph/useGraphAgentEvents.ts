import { useEffect } from 'react';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import { useGraphAgentBridgeOptional } from './GraphAgentBridge';
import type { NavigateEvent, SummaryResultEvent, DrawResultEvent } from './GraphAgentBridge';
import type { ForceNode } from './types';

interface UseGraphAgentEventsParams {
  graphNodes: ForceNode[];
  nodeByLabel: Map<string, ForceNode>;
  dimension: '2d' | '3d';
  setApiSearchMatchIds: (ids: Set<string> | null) => void;
  setSelectedNodeId: (id: string | null) => void;
  fgRef: React.RefObject<ForceGraphMethods | undefined>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fg3dRef: React.RefObject<any>;
}

export function useGraphAgentEvents({
  graphNodes,
  nodeByLabel,
  dimension,
  setApiSearchMatchIds,
  setSelectedNodeId,
  fgRef,
  fg3dRef,
}: UseGraphAgentEventsParams) {
  const bridge = useGraphAgentBridgeOptional();

  // 三位一體：監聽 Agent navigate 事件 → 圖譜 fly-to + 高亮
  useEffect(() => {
    if (!bridge) return;
    const unsub = bridge.bus.on<NavigateEvent>('navigate', (event) => {
      const ids = new Set(event.highlightIds.map((id) => `entity_${id}`));
      setApiSearchMatchIds(ids);

      if (event.centerEntityName) {
        const targetNode = nodeByLabel.get(event.centerEntityName)
          ?? graphNodes.find((n) => ids.has(n.id));
        if (targetNode?.x != null && targetNode?.y != null) {
          if (dimension === '3d' && fg3dRef.current) {
            const d = 120;
            const r = 1 + d / Math.hypot(targetNode.x, targetNode.y, targetNode.z ?? 0);
            fg3dRef.current.cameraPosition(
              { x: targetNode.x * r, y: targetNode.y * r, z: (targetNode.z ?? 0) * r },
              { x: targetNode.x, y: targetNode.y, z: targetNode.z ?? 0 },
              1000,
            );
          } else if (fgRef.current) {
            fgRef.current.centerAt(targetNode.x, targetNode.y, 500);
            fgRef.current.zoom(2, 500);
          }
        }
      }
    });
    return unsub;
  }, [bridge, graphNodes, nodeByLabel, dimension, setApiSearchMatchIds, fgRef, fg3dRef]);

  // 三位一體：監聽 Agent summary_result 事件 → 高亮上下游 + fly-to
  useEffect(() => {
    if (!bridge) return;
    const unsub = bridge.bus.on<SummaryResultEvent>('summary_result', (event) => {
      const targetNode = nodeByLabel.get(event.entityName);

      const highlightIds = new Set<string>();
      if (targetNode) {
        highlightIds.add(targetNode.id);
      }

      const upstreamNames = event.upstreamNames ?? [];
      const downstreamNames = event.downstreamNames ?? [];
      const relatedNames = [...upstreamNames, ...downstreamNames];

      for (const name of relatedNames) {
        const relNode = nodeByLabel.get(name);
        if (relNode) {
          highlightIds.add(relNode.id);
        }
      }

      if (highlightIds.size > 0) {
        setApiSearchMatchIds(highlightIds);
      }

      if (targetNode) {
        setSelectedNodeId(targetNode.id);

        if (targetNode.x != null && targetNode.y != null) {
          if (dimension === '3d' && fg3dRef.current) {
            const d = 120;
            const r = 1 + d / Math.hypot(targetNode.x, targetNode.y, targetNode.z ?? 0);
            fg3dRef.current.cameraPosition(
              { x: targetNode.x * r, y: targetNode.y * r, z: (targetNode.z ?? 0) * r },
              { x: targetNode.x, y: targetNode.y, z: targetNode.z ?? 0 },
              1000,
            );
          } else if (fgRef.current) {
            fgRef.current.centerAt(targetNode.x, targetNode.y, 500);
            fgRef.current.zoom(2, 500);
          }
        }
      }
    });
    return unsub;
  }, [bridge, nodeByLabel, dimension, setApiSearchMatchIds, setSelectedNodeId, fgRef, fg3dRef]);

  // B8: 監聽 Agent draw_result 事件 → 高亮圖中涉及的實體
  useEffect(() => {
    if (!bridge) return;
    const unsub = bridge.bus.on<DrawResultEvent>('draw_result', (event) => {
      if (!event.relatedEntities?.length) return;
      const highlightIds = new Set<string>();
      for (const name of event.relatedEntities) {
        const node = nodeByLabel.get(name);
        if (node) highlightIds.add(node.id);
      }
      if (highlightIds.size > 0) {
        setApiSearchMatchIds(highlightIds);
      }
    });
    return unsub;
  }, [bridge, nodeByLabel, setApiSearchMatchIds]);

  return bridge;
}
