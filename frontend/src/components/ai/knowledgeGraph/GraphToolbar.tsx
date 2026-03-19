/**
 * GraphToolbar - Knowledge Graph toolbar with search, type filters, and action buttons
 *
 * Extracted from KnowledgeGraph.tsx to reduce main component complexity.
 * v1.1.0: 2D/3D 維度切換按鈕從 canvas 容器移至 toolbar（修復 canvas 覆蓋問題）
 *
 * @version 1.1.0
 * @created 2026-02-27
 * @updated 2026-03-12
 */

import React, { useCallback } from 'react';
import {
  Input, Button, Space, Spin, Tag, Divider, Segmented,
  Tooltip as AntTooltip,
} from 'antd';
import {
  AimOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { GraphNode } from '../../../types/ai';
import type { GraphEdge } from '../../../types/ai';
import type { MergedNodeConfig } from '../../../config/graphNodeConfig';
import { getNodeConfig } from '../../../config/graphNodeConfig';
import { EDGE_COLORS, DEFAULT_EDGE_COLOR } from './types';

const { CheckableTag } = Tag;

/** 邊類型中文標籤 */
const EDGE_TYPE_LABELS: Record<string, string> = {
  sends: '發文',
  receives: '收文',
  mentions: '提及',
  agency_entity: '機關關聯',
  project_entity: '工程關聯',
  dispatch_entity: '派工關聯',
  co_mention: '共現',
  manages: '管理',
  located_in: '位於',
  related_to: '相關',
  dispatch_project: '關聯工程',
  belongs_to: '所屬',
  reply: '收發配對',
  issues: '發出',
  deadline: '截止',
  approves: '核准',
  copies: '副本',
};

/** 類型分組定義 */
const TYPE_GROUPS: { label: string; types: string[] }[] = [
  { label: '公文', types: ['document', 'project', 'agency', 'dispatch', 'typroject'] },
  { label: 'AI 提取', types: ['person', 'location', 'date', 'topic'] },
  { label: '程式碼', types: ['py_module', 'py_class', 'py_function', 'db_table', 'ts_module', 'ts_component', 'ts_hook'] },
  { label: '模組', types: ['menu_module', 'api_group'] },
];

export type GraphViewMode = 'entity' | 'full';

export interface GraphToolbarProps {
  searchText: string;
  onSearchChange: (value: string) => void;
  onSearchSubmit: () => void;
  apiSearching: boolean;
  visibleTypes: Set<string>;
  onTypeToggle: (type: string, checked: boolean) => void;
  onSettingsOpen: () => void;
  onZoomToFit: () => void;
  onRefresh: () => void;
  rawNodes: GraphNode[];
  rawEdges?: GraphEdge[];
  mergedConfigs: Record<string, MergedNodeConfig>;
  /** 2D/3D 維度切換 */
  dimension?: '2d' | '3d';
  onDimensionChange?: (dim: '2d' | '3d') => void;
  /** 視圖模式 */
  viewMode?: GraphViewMode;
  onViewModeChange?: (mode: GraphViewMode) => void;
}

export const GraphToolbar: React.FC<GraphToolbarProps> = ({
  searchText,
  onSearchChange,
  onSearchSubmit,
  apiSearching,
  visibleTypes,
  onTypeToggle,
  onSettingsOpen,
  onZoomToFit,
  onRefresh,
  rawNodes,
  rawEdges,
  mergedConfigs,
  dimension,
  onDimensionChange,
  viewMode,
  onViewModeChange,
}) => {
  // 群組全選/全取消切換
  const handleGroupToggle = useCallback((types: string[]) => {
    const presentTypes = types.filter((t) => rawNodes.some((n) => n.type === t));
    const allChecked = presentTypes.every((t) => visibleTypes.has(t));
    for (const t of presentTypes) {
      onTypeToggle(t, !allChecked);
    }
  }, [rawNodes, visibleTypes, onTypeToggle]);

  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8,
      marginBottom: 8, padding: '6px 0',
    }}>
      {/* 視圖模式切換 */}
      {viewMode && onViewModeChange && (
        <AntTooltip title="核心關係：僅顯示有連結的節點 / 完整：含孤立節點">
          <Segmented
            size="small"
            value={viewMode}
            options={[
              { label: '核心關係', value: 'entity' },
              { label: '完整網絡', value: 'full' },
            ]}
            onChange={(val) => onViewModeChange(val as GraphViewMode)}
          />
        </AntTooltip>
      )}

      <Input
        prefix={<SearchOutlined />}
        suffix={apiSearching ? <Spin size="small" /> : undefined}
        placeholder="搜尋節點（Enter 擴展搜尋）"
        value={searchText}
        onChange={(e) => onSearchChange(e.target.value)}
        onPressEnter={onSearchSubmit}
        allowClear
        size="small"
        style={{ width: 220 }}
      />

      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
        {TYPE_GROUPS.map((group, gIdx) => {
          const presentTypes = group.types.filter((t) => rawNodes.some((n) => n.type === t));
          if (presentTypes.length === 0) return null;
          return (
            <React.Fragment key={group.label}>
              {gIdx > 0 && <Divider orientation="vertical" style={{ height: 20, margin: '0 2px' }} />}
              <span
                onClick={() => handleGroupToggle(group.types)}
                style={{
                  fontSize: 11, color: '#666', cursor: 'pointer',
                  userSelect: 'none', fontWeight: 500, marginRight: 2,
                }}
              >
                {group.label}
              </span>
              {presentTypes.map((type) => {
                const merged = mergedConfigs[type] ?? getNodeConfig(type);
                return (
                  <AntTooltip key={type} title={merged.description} mouseEnterDelay={0.4}>
                    <CheckableTag
                      checked={visibleTypes.has(type)}
                      onChange={(checked) => onTypeToggle(type, checked)}
                      style={{ fontSize: 11, padding: '0 6px', margin: 0, lineHeight: '22px' }}
                    >
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                        <span style={{
                          width: 7, height: 7, borderRadius: '50%',
                          background: merged.color, display: 'inline-block',
                        }} />
                        {merged.label}
                      </span>
                    </CheckableTag>
                  </AntTooltip>
                );
              })}
            </React.Fragment>
          );
        })}
      </div>

      {/* 邊類型圖例 */}
      {rawEdges && rawEdges.length > 0 && (() => {
        const edgeTypesInGraph = [...new Set(rawEdges.map((e) => e.type))];
        if (edgeTypesInGraph.length === 0) return null;
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            <Divider orientation="vertical" style={{ height: 20, margin: '0 2px' }} />
            <span style={{ fontSize: 11, color: '#666', fontWeight: 500 }}>邊</span>
            {edgeTypesInGraph.map((type) => (
              <AntTooltip key={type} title={type} mouseEnterDelay={0.4}>
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 11 }}>
                  <span style={{
                    width: 14, height: 2, borderRadius: 1,
                    background: EDGE_COLORS[type] || DEFAULT_EDGE_COLOR,
                    display: 'inline-block',
                  }} />
                  {EDGE_TYPE_LABELS[type] || type}
                </span>
              </AntTooltip>
            ))}
          </div>
        );
      })()}

      <Space size={4} style={{ marginLeft: 'auto' }}>
        {/* 2D/3D 維度切換 */}
        {dimension && onDimensionChange && (
          <Segmented
            size="small"
            value={dimension}
            options={[
              { label: '2D', value: '2d' },
              { label: '3D', value: '3d' },
            ]}
            onChange={(val) => onDimensionChange(val as '2d' | '3d')}
          />
        )}
        <AntTooltip title="節點設定">
          <Button size="small" icon={<SettingOutlined />} onClick={onSettingsOpen} />
        </AntTooltip>
        <AntTooltip title="自動適配畫面">
          <Button size="small" icon={<AimOutlined />} onClick={onZoomToFit} />
        </AntTooltip>
        <AntTooltip title="重新載入">
          <Button size="small" icon={<ReloadOutlined />} onClick={onRefresh} />
        </AntTooltip>
      </Space>
    </div>
  );
};
