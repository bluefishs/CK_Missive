import React from 'react';
import { Card, Tag, Button, Typography, Space, Popconfirm } from 'antd';
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { CATEGORY_OPTIONS, STATUS_OPTIONS } from './tabs';

const { Title } = Typography;

const getStatusTagColor = (status?: string) => {
  const statusOption = STATUS_OPTIONS.find(s => s.value === status);
  return statusOption?.color || 'default';
};

const getStatusTagText = (status?: string) => {
  const statusOption = STATUS_OPTIONS.find(s => s.value === status);
  return statusOption?.label || status || '未設定';
};

const getCategoryTagColor = (category?: string) => {
  const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
  return categoryOption?.color || 'default';
};

interface DetailPageHeaderProps {
  projectName: string;
  category?: string;
  status?: string;
  onBack: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  deleting?: boolean;
}

export const DetailPageHeader: React.FC<DetailPageHeaderProps> = ({
  projectName,
  category,
  status,
  onBack,
  onEdit,
  onDelete,
  deleting,
}) => {
  return (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Button type="text" icon={<ArrowLeftOutlined />} onClick={onBack}>
            返回
          </Button>
          <div>
            <Title level={3} style={{ margin: 0 }}>{projectName}</Title>
            <div style={{ marginTop: 8 }}>
              <Tag color={getCategoryTagColor(category)}>
                {category || '未分類'}
              </Tag>
              <Tag color={getStatusTagColor(status)}>
                {getStatusTagText(status)}
              </Tag>
            </div>
          </div>
        </div>
        <Space>
          {onEdit && (
            <Button icon={<EditOutlined />} onClick={onEdit}>
              編輯
            </Button>
          )}
          {onDelete && (
            <Popconfirm
              title="確定要刪除此承攬案件嗎？"
              description="刪除後將無法復原，關聯的承辦同仁與廠商資料也會一併刪除。"
              onConfirm={onDelete}
              okText="確定刪除"
              cancelText="取消"
              okButtonProps={{ danger: true, loading: deleting }}
            >
              <Button danger icon={<DeleteOutlined />} loading={deleting}>
                刪除
              </Button>
            </Popconfirm>
          )}
        </Space>
      </div>
    </Card>
  );
};
