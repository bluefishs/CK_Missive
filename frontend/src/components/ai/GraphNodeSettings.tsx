/**
 * GraphNodeSettings - 知識圖譜節點配置面板
 *
 * 使用者可自訂各節點類型的顏色、標籤、說明、可見性。
 * 設定持久化到 localStorage，重新整理頁面後仍保留。
 *
 * @version 1.0.0
 * @created 2026-02-24
 */

import React, { useState, useEffect } from 'react';
import {
  Drawer, Button, Input, Switch, Space, Divider,
  Typography, Popconfirm, ColorPicker, App,
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

export interface GraphNodeSettingsProps {
  open: boolean;
  onClose: () => void;
  /** 儲存後通知父元件重繪 */
  onSaved?: () => void;
}

interface EditableConfig {
  color: string;
  label: string;
  description: string;
  visible: boolean;
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
    };
  }
  return state;
}

export const GraphNodeSettings: React.FC<GraphNodeSettingsProps> = ({
  open,
  onClose,
  onSaved,
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

  const handleFieldChange = (
    type: string,
    field: keyof EditableConfig,
    value: string | boolean,
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

  const handleSave = () => {
    // 計算覆蓋差異（只存與預設不同的值）
    const overrides: NodeConfigOverrides = {};
    for (const [type, edited] of Object.entries(editState)) {
      const base = GRAPH_NODE_CONFIG[type];
      if (!base) continue;
      const diff: Record<string, string | boolean> = {};
      if (edited.color !== base.color) diff.color = edited.color;
      if (edited.label !== base.label) diff.label = edited.label;
      if (edited.description !== base.description) diff.description = edited.description;
      if (!edited.visible) diff.visible = false;
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
      mask={false}
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
      {Object.entries(GRAPH_NODE_CONFIG).map(([type, base], idx) => {
        const edited = editState[type];
        if (!edited) return null;
        const isBusinessEntity = !base.detailable;
        return (
          <div key={type}>
            {idx > 0 && <Divider style={{ margin: '12px 0' }} />}
            <div style={{ marginBottom: 8 }}>
              <Space align="center">
                <span style={{
                  width: 12, height: 12, borderRadius: '50%',
                  background: edited.color, display: 'inline-block',
                  border: '1px solid #d9d9d9',
                }} />
                <Text strong>{edited.label}</Text>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  ({type})
                </Text>
                {isBusinessEntity && (
                  <Text type="secondary" style={{ fontSize: 10 }}>
                    [業務實體]
                  </Text>
                )}
                {!isBusinessEntity && (
                  <Text type="secondary" style={{ fontSize: 10 }}>
                    [AI 提取]
                  </Text>
                )}
              </Space>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: '6px 12px', alignItems: 'center', paddingLeft: 8 }}>
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
      })}
    </Drawer>
  );
};

export default GraphNodeSettings;
