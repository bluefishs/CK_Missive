/**
 * StaffDetailHeader
 * @description Top card with back button, staff name/status, and edit/delete actions
 */
import React from 'react';
import { Card, Button, Space, Typography, Tag, Popconfirm } from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
} from '@ant-design/icons';
import type { User } from '../../types/api';

const { Title } = Typography;

interface StaffDetailHeaderProps {
  staff: User;
  isMobile: boolean;
  isEditing: boolean;
  onBack: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

export const StaffDetailHeader: React.FC<StaffDetailHeaderProps> = ({
  staff,
  isMobile,
  isEditing,
  onBack,
  onEdit,
  onDelete,
}) => (
  <Card size={isMobile ? 'small' : 'medium'} style={{ marginBottom: isMobile ? 8 : 16 }}>
    <div style={{
      display: 'flex',
      flexDirection: isMobile ? 'column' : 'row',
      justifyContent: 'space-between',
      alignItems: isMobile ? 'stretch' : 'center',
      gap: isMobile ? 8 : 0,
    }}>
      <Space wrap size={isMobile ? 'small' : 'middle'}>
        <Button
          icon={<ArrowLeftOutlined />}
          size={isMobile ? 'small' : 'middle'}
          onClick={onBack}
        >
          {isMobile ? '返回' : '返回列表'}
        </Button>
        <Title level={isMobile ? 5 : 4} style={{ margin: 0 }}>
          <UserOutlined style={{ marginRight: 8 }} />
          {staff.full_name || staff.username}
        </Title>
        <Tag color={staff.is_active ? 'success' : 'default'}>
          {staff.is_active ? '啟用中' : '已停用'}
        </Tag>
      </Space>
      {!isEditing && (
        <Space size={isMobile ? 'small' : 'middle'} style={{ width: isMobile ? '100%' : 'auto' }}>
          <Button
            type="primary"
            icon={<EditOutlined />}
            size={isMobile ? 'small' : 'middle'}
            onClick={onEdit}
            style={isMobile ? { flex: 1 } : undefined}
          >
            編輯
          </Button>
          <Popconfirm
            title="確定要刪除此承辦同仁？"
            description="刪除後將無法復原"
            onConfirm={onDelete}
            okText="確定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button
              danger
              icon={<DeleteOutlined />}
              size={isMobile ? 'small' : 'middle'}
              style={isMobile ? { flex: 1 } : undefined}
            >
              {isMobile ? '' : '刪除'}
            </Button>
          </Popconfirm>
        </Space>
      )}
    </div>
  </Card>
);
