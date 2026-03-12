/**
 * GraphToolbar - Knowledge Graph toolbar with search, type filters, and action buttons
 *
 * Extracted from KnowledgeGraph.tsx to reduce main component complexity.
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

import React, { useCallback } from 'react';
import {
  Input, Button, Space, Spin, Tag, Divider,
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
import { getNodeConfig } from '../../../config/graphNodeConfig';

const { CheckableTag } = Tag;

/** 類型分組定義 */
const TYPE_GROUPS: { label: string; types: string[] }[] = [
  { label: '公文', types: ['document', 'project', 'agency', 'dispatch', 'typroject'] },
  { label: 'AI 提取', types: ['org', 'person', 'ner_project', 'location', 'date', 'topic'] },
  { label: '程式碼', types: ['py_module', 'py_class', 'py_function', 'db_table', 'ts_module', 'ts_component', 'ts_hook'] },
  { label: '模組', types: ['menu_module', 'api_group'] },
];

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
              {gIdx > 0 && <Divider type="vertical" style={{ height: 20, margin: '0 2px' }} />}
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
