/**
 * GraphToolbar - Knowledge Graph toolbar with search, type filters, and action buttons
 *
 * Extracted from KnowledgeGraph.tsx to reduce main component complexity.
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

import React from 'react';
import {
  Input, Checkbox, Button, Space, Spin,
  Tooltip as AntTooltip,
} from 'antd';
import {
  AimOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import type { GraphNode } from '../../../types/ai';
import type { MergedNodeConfig } from '../../../config/graphNodeConfig';
import { GRAPH_NODE_CONFIG, getNodeConfig } from '../../../config/graphNodeConfig';

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
  mergedConfigs: Record<string, MergedNodeConfig>;
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
  mergedConfigs,
}) => {
  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8,
      marginBottom: 8, padding: '6px 0',
    }}>
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

      <Space size={4}>
        {Object.entries(GRAPH_NODE_CONFIG)
          .filter(([type]) => rawNodes.some((n) => n.type === type))
          .map(([type]) => {
            const merged = mergedConfigs[type] ?? getNodeConfig(type);
            return (
              <AntTooltip key={type} title={merged.description} mouseEnterDelay={0.4}>
                <Checkbox
                  checked={visibleTypes.has(type)}
                  onChange={(e) => onTypeToggle(type, e.target.checked)}
                  style={{ fontSize: 12 }}
                >
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                    <span style={{
                      width: 8, height: 8, borderRadius: '50%',
                      background: merged.color, display: 'inline-block',
                    }} />
                    {merged.label}
                  </span>
                </Checkbox>
              </AntTooltip>
            );
          })}
      </Space>

      <Space size={4} style={{ marginLeft: 'auto' }}>
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
