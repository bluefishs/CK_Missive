/**
 * StaffCertificationsTab
 * @description Certifications table with add/edit/delete/preview actions
 */
import React from 'react';
import {
  Button,
  Space,
  Typography,
  Table,
  Tag,
  Empty,
  Popconfirm,
  Spin,
} from 'antd';
import {
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { Certification } from '../../api/certificationsApi';
import { getCertTypeColor, getCertStatusColor } from './staffDetailUtils';

const { Text } = Typography;

interface StaffCertificationsTabProps {
  certifications: Certification[];
  certLoading: boolean;
  isMobile: boolean;
  onAdd: () => void;
  onEdit: (cert: Certification) => void;
  onDelete: (certId: number) => void;
  onPreview: (cert: Certification) => void;
}

export const StaffCertificationsTab: React.FC<StaffCertificationsTabProps> = ({
  certifications,
  certLoading,
  isMobile,
  onAdd,
  onEdit,
  onDelete,
  onPreview,
}) => {
  if (certLoading) {
    return (
      <div style={{ textAlign: 'center', padding: isMobile ? 20 : 40 }}>
        <Spin size={isMobile ? 'default' : 'large'} />
      </div>
    );
  }

  if (certifications.length === 0) {
    return (
      <Empty description="尚無證照紀錄">
        <Button
          type="primary"
          icon={<PlusOutlined />}
          size={isMobile ? 'small' : 'middle'}
          onClick={onAdd}
        >
          新增證照
        </Button>
      </Empty>
    );
  }

  return (
    <Table
      dataSource={certifications}
      rowKey="id"
      size="small"
      scroll={{ x: isMobile ? 500 : undefined }}
      pagination={false}
      title={() => (
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            size="small"
            onClick={onAdd}
          >
            新增證照
          </Button>
        </div>
      )}
      columns={[
        {
          title: '類型',
          dataIndex: 'cert_type',
          key: 'cert_type',
          width: 90,
          render: (type: string) => (
            <Tag color={getCertTypeColor(type)}>{type}</Tag>
          ),
        },
        {
          title: '證照名稱',
          dataIndex: 'cert_name',
          key: 'cert_name',
          width: 160,
          ellipsis: true,
        },
        {
          title: '核發機關',
          dataIndex: 'issuing_authority',
          key: 'issuing_authority',
          width: 120,
          ellipsis: true,
          render: (text: string) => text || '-',
        },
        {
          title: '狀態',
          dataIndex: 'status',
          key: 'status',
          width: 70,
          render: (status: string) => (
            <Tag color={getCertStatusColor(status)}>{status}</Tag>
          ),
        },
        {
          title: '附件',
          dataIndex: 'attachment_path',
          key: 'attachment',
          width: 60,
          render: (path: string, record: Certification) => (
            path ? (
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => onPreview(record)}
              />
            ) : (
              <Text type="secondary">-</Text>
            )
          ),
        },
        {
          title: '操作',
          key: 'action',
          width: 120,
          render: (_: unknown, record: Certification) => (
            <Space size="small">
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => onEdit(record)}
              >
                編輯
              </Button>
              <Popconfirm
                title="確定要刪除此證照？"
                onConfirm={() => onDelete(record.id)}
                okText="確定"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Popconfirm>
            </Space>
          ),
        },
      ]}
    />
  );
};
