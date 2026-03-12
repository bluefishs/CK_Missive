/**
 * GraphNodeSettings - 知識圖譜節點配置面板
 *
 * 使用者可自訂各節點類型的顏色、標籤、說明、可見性。
 * 設定持久化到 localStorage，重新整理頁面後仍保留。
 *
 * v2.0: 加入 activeTypes 過濾 + 分類分組顯示
 *
 * @version 2.0.0
 * @created 2026-02-24
 * @updated 2026-03-12
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Drawer, Button, Input, Switch, Space, Divider, Slider,
  Typography, Popconfirm, ColorPicker, App, Collapse, Tag,
} from 'antd';
import {
  SettingOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import type { Color } from 'antd/es/color-picker';
import {
  GRAPH_NODE_CONFIG,
  getUserOverrides,
  saveUserOverrides,
  resetUserOverrides,
  type NodeConfigOverrides,
  type GraphNodeTypeConfig,
} from '../../config/graphNodeConfig';

const { Text } = Typography;
const { TextArea } = Input;

/** 節點類型分組定義 */
const NODE_TYPE_GROUPS: { key: string; label: string; types: string[] }[] = [
  {
    key: 'business',
    label: '業務實體',
    types: ['document', 'project', 'agency', 'dispatch', 'typroject'],
  },
  {
    key: 'ner',
    label: 'AI 提取實體',
    types: ['org', 'person', 'ner_project', 'location', 'date', 'topic'],
  },
  {
    key: 'code',
    label: '程式碼圖譜',
    types: ['py_module', 'py_class', 'py_function', 'db_table', 'ts_module', 'ts_component', 'ts_hook'],
  },
  {
    key: 'module',
    label: '模組總覽',
    types: ['menu_module', 'api_group'],
  },
];

export interface GraphNodeSettingsProps {
  open: boolean;
  onClose: () => void;
  /** 儲存後通知父元件重繪 */
  onSaved?: () => void;
  /** 當前圖譜中實際出現的節點類型（未傳入則顯示全部） */
  activeTypes?: Set<string>;
}

interface EditableConfig {
  color: string;
  label: string;
  description: string;
  visible: boolean;
  radius: number;
}

type EditState = Record<string, EditableConfig>;

function buildEditState(
  defaults: Record<string, GraphNodeTypeConfig>,
  overrides: NodeConfigOverrides,
): EditState {
  const state: EditState = {};
  for (const [type, base] of Object.entries(defaults)) {
    const ov = overrides[type];
    state[type] = {
      color: ov?.color ?? base.color,
      label: ov?.label ?? base.label,
      description: ov?.description ?? base.description,
      visible: ov?.visible ?? true,
      radius: ov?.radius ?? base.radius,
    };
  }
  return state;
}

export const GraphNodeSettings: React.FC<GraphNodeSettingsProps> = ({
  open,
  onClose,
  onSaved,
  activeTypes,
}) => {
  const { message } = App.useApp();
  const [editState, setEditState] = useState<EditState>(() =>
    buildEditState(GRAPH_NODE_CONFIG, getUserOverrides())
  );

  // 每次開啟時重新從 localStorage 載入
  useEffect(() => {
    if (open) {
      setEditState(buildEditState(GRAPH_NODE_CONFIG, getUserOverrides()));
    }
  }, [open]);

  // 過濾分組：只顯示有實際節點的分組
  const filteredGroups = useMemo(() => {
    if (!activeTypes || activeTypes.size === 0) return NODE_TYPE_GROUPS;
    return NODE_TYPE_GROUPS
      .map((group) => ({
        ...group,
        types: group.types.filter((t) => activeTypes.has(t)),
      }))
      .filter((group) => group.types.length > 0);
  }, [activeTypes]);

  const handleFieldChange = (
    type: string,
    field: keyof EditableConfig,
    value: string | boolean | number,
  ) => {
    setEditState((prev) => {
      const current = prev[type];
      if (!current) return prev;
      const updated: EditableConfig = { ...current, [field]: value as never };
      return { ...prev, [type]: updated };
    });
  };

  const handleColorChange = (type: string, color: Color) => {
    handleFieldChange(type, 'color', color.toHexString());
  };

  // 群組全部顯示/隱藏切換
  const handleGroupVisibilityToggle = (types: string[], visible: boolean) => {
    setEditState((prev) => {
      const next = { ...prev };
      for (const t of types) {
        if (next[t]) {
          next[t] = { ...next[t], visible };
        }
      }
      return next;
    });
  };

  const handleSave = () => {
    // 計算覆蓋差異（只存與預設不同的值）
    const overrides: NodeConfigOverrides = {};
    for (const [type, edited] of Object.entries(editState)) {
      const base = GRAPH_NODE_CONFIG[type];
      if (!base) continue;
      const diff: Record<string, string | boolean | number> = {};
      if (edited.color !== base.color) diff.color = edited.color;
      if (edited.label !== base.label) diff.label = edited.label;
      if (edited.description !== base.description) diff.description = edited.description;
      if (!edited.visible) diff.visible = false;
      if (edited.radius !== base.radius) diff.radius = edited.radius;
      if (Object.keys(diff).length > 0) {
        overrides[type] = diff;
      }
    }
    saveUserOverrides(overrides);
    message.success('節點設定已儲存');
    onSaved?.();
    onClose();
  };

  const handleReset = () => {
    resetUserOverrides();
    setEditState(buildEditState(GRAPH_NODE_CONFIG, {}));
    message.info('已恢復預設設定');
    onSaved?.();
  };

  const renderNodeTypeRow = (type: string) => {
    const base = GRAPH_NODE_CONFIG[type];
    const edited = editState[type];
    if (!base || !edited) return null;

    return (
      <div key={type} style={{ marginBottom: 12 }}>
        <div style={{ marginBottom: 6 }}>
          <Space align="center" size={4}>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: edited.color, display: 'inline-block',
              border: '1px solid #d9d9d9',
            }} />
            <Text strong style={{ fontSize: 13 }}>{edited.label}</Text>
            <Text type="secondary" style={{ fontSize: 10 }}>({type})</Text>
          </Space>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '4px 12px', alignItems: 'center', paddingLeft: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>顏色</Text>
          <ColorPicker
            value={edited.color}
            size="small"
            onChange={(c) => handleColorChange(type, c)}
            showText
          />

          <Text type="secondary" style={{ fontSize: 12 }}>標籤</Text>
          <Input
            size="small"
            value={edited.label}
            onChange={(e) => handleFieldChange(type, 'label', e.target.value)}
            style={{ width: 160 }}
            maxLength={20}
          />

          <Text type="secondary" style={{ fontSize: 12 }}>說明</Text>
          <TextArea
            size="small"
            value={edited.description}
            onChange={(e) => handleFieldChange(type, 'description', e.target.value)}
            rows={2}
            maxLength={100}
            style={{ fontSize: 12 }}
          />

          <Text type="secondary" style={{ fontSize: 12 }}>大小</Text>
          <Slider
            min={2}
            max={15}
            step={1}
            value={edited.radius}
            onChange={(v) => handleFieldChange(type, 'radius', v)}
            style={{ width: 160, margin: '4px 0' }}
          />

          <Text type="secondary" style={{ fontSize: 12 }}>顯示</Text>
          <Switch
            size="small"
            checked={edited.visible}
            onChange={(v) => handleFieldChange(type, 'visible', v)}
            checkedChildren="顯示"
            unCheckedChildren="隱藏"
          />
        </div>
      </div>
    );
  };

  return (
    <Drawer
      title={
        <Space>
          <SettingOutlined />
          <span>知識圖譜節點設定</span>
        </Space>
      }
      placement="right"
      width={420}
      open={open}
      onClose={onClose}
      extra={
        <Popconfirm
          title="確定要恢復所有預設設定？"
          onConfirm={handleReset}
          okText="確認"
          cancelText="取消"
        >
          <Button size="small" icon={<UndoOutlined />}>
            重置預設
          </Button>
        </Popconfirm>
      }
      footer={
        <div style={{ textAlign: 'right' }}>
          <Space>
            <Button onClick={onClose}>取消</Button>
            <Button type="primary" onClick={handleSave}>儲存</Button>
          </Space>
        </div>
      }
    >
      <Collapse
        defaultActiveKey={filteredGroups.map((g) => g.key)}
        ghost
        items={filteredGroups.map((group) => {
          const visibleCount = group.types.filter((t) => editState[t]?.visible).length;
          const allVisible = visibleCount === group.types.length;
          return {
            key: group.key,
            label: (
              <Space size={6}>
                <Text strong style={{ fontSize: 13 }}>{group.label}</Text>
                <Tag color={allVisible ? 'green' : 'default'} style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>
                  {visibleCount}/{group.types.length}
                </Tag>
              </Space>
            ),
            extra: (
              <Button
                type="link"
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleGroupVisibilityToggle(group.types, !allVisible);
                }}
                style={{ fontSize: 11, padding: '0 4px' }}
              >
                {allVisible ? '全部隱藏' : '全部顯示'}
              </Button>
            ),
            children: (
              <div style={{ paddingLeft: 4 }}>
                {group.types.map((type, idx) => (
                  <React.Fragment key={type}>
                    {idx > 0 && <Divider style={{ margin: '8px 0' }} />}
                    {renderNodeTypeRow(type)}
                  </React.Fragment>
                ))}
              </div>
            ),
          };
        })}
      />
    </Drawer>
  );
};

export default GraphNodeSettings;
