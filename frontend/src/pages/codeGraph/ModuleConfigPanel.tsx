import React from 'react';
import {
  Card,
  Space,
  Button,
  Tag,
  Divider,
  Typography,
  Input,
} from 'antd';
import type { ModuleMapping } from '../../config/moduleGraphConfig';

const { Title, Text } = Typography;

export interface ModuleConfigPanelProps {
  editingModule: ModuleMapping | null;
  setEditingModule: (mod: ModuleMapping | null) => void;
  moduleMappings: ModuleMapping[];
  editFieldValues: Record<string, string>;
  setEditFieldValues: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  handleModuleEdit: (mod: ModuleMapping) => void;
  handleModuleSave: () => void;
  handleModuleReset: () => void;
}

const FIELD_LABELS: Record<string, string> = {
  pages: '前端頁面',
  apiGroups: 'API 端點群組',
  backendServices: '後端服務',
  dbTables: '資料庫表',
};

const EDITABLE_FIELDS = ['pages', 'apiGroups', 'backendServices', 'dbTables'] as const;

const ModuleConfigPanel: React.FC<ModuleConfigPanelProps> = ({
  editingModule,
  setEditingModule,
  moduleMappings,
  editFieldValues,
  setEditFieldValues,
  handleModuleEdit,
  handleModuleSave,
  handleModuleReset,
}) => {
  return (
    <div style={{ width: 320, minWidth: 320, background: '#fff', borderLeft: '1px solid #f0f0f0', overflow: 'auto', padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Title level={5} style={{ margin: 0, fontSize: 14 }}>模組配置</Title>
        <Button size="small" onClick={handleModuleReset}>重置預設</Button>
      </div>
      <Divider style={{ margin: '8px 0' }} />

      {editingModule ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Tag color={editingModule.color} style={{ fontSize: 13 }}>{editingModule.title}</Tag>
            <Space size="small">
              <Button size="small" type="primary" onClick={handleModuleSave}>儲存</Button>
              <Button size="small" onClick={() => setEditingModule(null)}>取消</Button>
            </Space>
          </div>

          {EDITABLE_FIELDS.map((field) => (
            <Card key={field} size="small" title={<span style={{ fontSize: 12 }}>{FIELD_LABELS[field]}</span>} styles={{ body: { padding: 8 } }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {editingModule[field].map((item, idx) => (
                  <Tag
                    key={idx}
                    closable
                    onClose={() => {
                      const updated = { ...editingModule, [field]: editingModule[field].filter((_: string, i: number) => i !== idx) };
                      setEditingModule(updated);
                    }}
                    style={{ fontSize: 11 }}
                  >
                    {item}
                  </Tag>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                <Input
                  size="small"
                  placeholder={`新增${FIELD_LABELS[field]}...`}
                  value={editFieldValues[field] || ''}
                  onChange={(e) => setEditFieldValues((prev) => ({ ...prev, [field]: e.target.value }))}
                  onPressEnter={() => {
                    const val = (editFieldValues[field] || '').trim();
                    if (val) {
                      const updated = { ...editingModule, [field]: [...editingModule[field], val] };
                      setEditingModule(updated);
                      setEditFieldValues((prev) => ({ ...prev, [field]: '' }));
                    }
                  }}
                  style={{ flex: 1 }}
                />
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <Text type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>
            點擊圖譜中的模組節點進行編輯
          </Text>
          {moduleMappings.map((mod) => (
            <Card
              key={mod.key}
              size="small"
              hoverable
              onClick={() => handleModuleEdit(mod)}
              styles={{ body: { padding: '6px 10px' } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>
                  <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: mod.color, marginRight: 6 }} />
                  <Text strong style={{ fontSize: 12 }}>{mod.title}</Text>
                </span>
                <Space size={2}>
                  <Tag style={{ fontSize: 10 }}>{mod.pages.length} 頁面</Tag>
                  <Tag style={{ fontSize: 10 }}>{mod.dbTables.length} 表</Tag>
                </Space>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default ModuleConfigPanel;
