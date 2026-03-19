import React from 'react';
import { Card, Tag, Button, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
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
}

export const DetailPageHeader: React.FC<DetailPageHeaderProps> = ({
  projectName,
  category,
  status,
  onBack,
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
      </div>
    </Card>
  );
};
