import React, { Suspense, lazy } from 'react';
import { Spin } from 'antd';
import ForceGraph2D, { type ForceGraphMethods } from 'react-force-graph-2d';
import type { MergedNodeConfig } from '../../../config/graphNodeConfig';
import { EntityDetailSidebar } from '../EntityDetailSidebar';
import { SelectedNodeInfoCard } from './SelectedNodeInfoCard';
import type { ForceNode, GraphData } from './types';

const ForceGraph3D = lazy(() => import('react-force-graph-3d'));

interface GraphCanvasProps {
  dimension: '2d' | '3d';
  graphData: GraphData;
  effectiveWidth: number;
  height: number;
  fgRef: React.RefObject<ForceGraphMethods | undefined>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fg3dRef: React.RefObject<any>;
  // 2D callbacks
  paintNode: unknown;
  nodePointerAreaPaint: unknown;
  linkColor: unknown;
  linkWidth: unknown;
  linkDirectionalArrowColor: unknown;
  linkCanvasObject: unknown;
  // 3D callbacks
  graph3dCallbacks: {
    nodeThreeObject: unknown;
    linkColor: unknown;
    linkWidth: unknown;
    linkDirectionalArrowColor: unknown;
    linkThreeObject: unknown;
    linkPositionUpdate: unknown;
  };
  // Event handlers
  onNodeClick: (node: ForceNode) => void;
  onNodeHover: (node: ForceNode | null) => void;
  onBackgroundClick: () => void;
  // Selected node info
  selectedNode: ForceNode | null;
  selectedNodeConfig: MergedNodeConfig | null;
  selectedNeighborCount: number;
  onSelectedNodeClose: () => void;
  onViewDetail: (label: string, type: string) => void;
  // Sidebar
  sidebarVisible: boolean;
  sidebarEntityName: string;
  sidebarEntityType: string;
  onSidebarClose: () => void;
}

const SIDEBAR_WIDTH = 380;

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  dimension,
  graphData,
  effectiveWidth,
  height,
  fgRef,
  fg3dRef,
  paintNode,
  nodePointerAreaPaint,
  linkColor,
  linkWidth,
  linkDirectionalArrowColor,
  linkCanvasObject,
  graph3dCallbacks,
  onNodeClick,
  onNodeHover,
  onBackgroundClick,
  selectedNode,
  selectedNodeConfig,
  selectedNeighborCount,
  onSelectedNodeClose,
  onViewDetail,
  sidebarVisible,
  sidebarEntityName,
  sidebarEntityType,
  onSidebarClose,
}) => {
  return (
    <div style={{ display: 'flex', gap: 0 }}>
      {/* 圖譜區域 */}
      <div style={{
        flex: 1, minWidth: 0, position: 'relative',
        border: '1px solid #f0f0f0', borderRadius: sidebarVisible ? '8px 0 0 8px' : 8,
        overflow: 'hidden', background: dimension === '3d' ? '#1a1a2e' : '#fafafa',
      }}>
        {dimension === '2d' ? (
          <ForceGraph2D
            ref={fgRef as never}
            graphData={graphData as never}
            width={effectiveWidth}
            height={height}
            d3AlphaDecay={0.04}
            d3VelocityDecay={0.3}
            nodeCanvasObject={paintNode as never}
            nodePointerAreaPaint={nodePointerAreaPaint as never}
            onNodeClick={onNodeClick as never}
            onNodeHover={onNodeHover as never}
            linkColor={linkColor as never}
            linkWidth={linkWidth as never}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={0.85}
            linkDirectionalArrowColor={linkDirectionalArrowColor as never}
            linkCanvasObjectMode={() => 'after'}
            linkCanvasObject={linkCanvasObject as never}
            onBackgroundClick={onBackgroundClick}
            onEngineStop={() => {
              fgRef.current?.zoomToFit(400, 60);
            }}
            warmupTicks={30}
            cooldownTicks={200}
          />
        ) : (
          <Suspense fallback={<div style={{ height, display: 'flex', justifyContent: 'center', alignItems: 'center' }}><Spin description="載入 3D 引擎..."><div /></Spin></div>}>
            <ForceGraph3D
              ref={fg3dRef}
              graphData={graphData as never}
              width={effectiveWidth}
              height={height}
              nodeThreeObject={graph3dCallbacks.nodeThreeObject as never}
              nodeThreeObjectExtend={false}
              onNodeClick={onNodeClick as never}
              onNodeHover={onNodeHover as never}
              linkColor={graph3dCallbacks.linkColor as never}
              linkWidth={graph3dCallbacks.linkWidth as never}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={0.85}
              linkDirectionalArrowColor={graph3dCallbacks.linkDirectionalArrowColor as never}
              linkThreeObject={graph3dCallbacks.linkThreeObject as never}
              linkThreeObjectExtend={false}
              linkPositionUpdate={graph3dCallbacks.linkPositionUpdate as never}
              onBackgroundClick={onBackgroundClick}
              onEngineStop={() => {
                fg3dRef.current?.zoomToFit(400, 60);
              }}
              warmupTicks={30}
              cooldownTicks={200}
              backgroundColor="#1a1a2e"
            />
          </Suspense>
        )}

        {/* 選取節點資訊面板（浮動在圖譜內） */}
        {selectedNode && selectedNodeConfig && !sidebarVisible && (
          <SelectedNodeInfoCard
            node={selectedNode}
            nodeConfig={selectedNodeConfig}
            neighborCount={selectedNeighborCount}
            onClose={onSelectedNodeClose}
            onViewDetail={onViewDetail}
          />
        )}
      </div>

      {/* Entity Detail Sidebar — inline 面板 */}
      {sidebarVisible && (
        <div style={{
          width: SIDEBAR_WIDTH,
          minWidth: SIDEBAR_WIDTH,
          height: height + 2,
          borderTop: '1px solid #f0f0f0',
          borderRight: '1px solid #f0f0f0',
          borderBottom: '1px solid #f0f0f0',
          borderRadius: '0 8px 8px 0',
          overflow: 'hidden',
        }}>
          <EntityDetailSidebar
            visible={sidebarVisible}
            entityName={sidebarEntityName}
            entityType={sidebarEntityType}
            onClose={onSidebarClose}
            inline
          />
        </div>
      )}
    </div>
  );
};
