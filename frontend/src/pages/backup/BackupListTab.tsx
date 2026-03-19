import React from 'react';
import {
  Card, Button, Space, Typography, Row, Col, Alert, Tag, Tooltip, Popconfirm
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  DatabaseOutlined, FolderOutlined, SyncOutlined, DeleteOutlined
} from '@ant-design/icons';
import { ResponsiveTable } from '../../components/common';
import type { BackupItem, BackupListResponse } from '../../types/api';

const { Text } = Typography;

interface BackupListTabProps {
  backups: BackupListResponse | null;
  loading: boolean;
  onCreateBackup: () => void;
  onDeleteBackup: (item: BackupItem) => void;
  onRestoreBackup: (item: BackupItem) => void;
}

export const BackupListTab: React.FC<BackupListTabProps> = ({
  backups,
  loading,
  onCreateBackup,
  onDeleteBackup,
  onRestoreBackup,
}) => {
  const backupColumns: ColumnsType<BackupItem> = [
    {
      title: '備份名稱',
      key: 'name',
      render: (_, record) => (
        <Space>
          {record.type === 'database' ? <DatabaseOutlined /> : <FolderOutlined />}
          <Text>{record.filename || record.dirname}</Text>
          {record.mode === 'incremental' && (
            <Tag color="cyan">增量</Tag>
          )}
        </Space>
      )
    },
    {
      title: '類型',
      dataIndex: 'type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'database' ? 'blue' : 'green'}>
          {type === 'database' ? '資料庫' : '附件'}
        </Tag>
      )
    },
    {
      title: '大小',
      key: 'size',
      width: 120,
      render: (_, record) => (
        record.size_kb
          ? `${record.size_kb} KB`
          : record.size_mb
            ? `${record.size_mb} MB`
            : '-'
      )
    },
    {
      title: '統計',
      key: 'stats',
      width: 180,
      render: (_, record) => {
        if (record.mode === 'incremental' && (record.copied_count !== undefined || record.file_count !== undefined)) {
          return (
            <Tooltip title={`已複製: ${record.copied_count || 0}, 跳過: ${record.skipped_count || 0}, 移除: ${record.removed_count || 0}`}>
              <Text type="secondary">
                {record.file_count || 0} 檔案
                {record.copied_count ? ` (+${record.copied_count})` : ''}
              </Text>
            </Tooltip>
          );
        }
        return record.file_count ? `${record.file_count} 檔案` : '-';
      }
    },
    {
      title: '建立時間',
      dataIndex: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-TW')
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          {record.type === 'database' && (
            <Tooltip title="還原">
              <Button
                type="link"
                size="small"
                icon={<SyncOutlined />}
                onClick={() => onRestoreBackup(record)}
              />
            </Tooltip>
          )}
          {record.dirname !== 'attachments_latest' && (
            <Popconfirm
              title="確定刪除此備份？"
              onConfirm={() => onDeleteBackup(record)}
              okText="確定"
              cancelText="取消"
            >
              <Tooltip title="刪除">
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ];

  return (
    <Space vertical style={{ width: '100%' }} size="large">
      <Row justify="space-between" align="middle">
        <Col>
          <Alert
            title="備份管理"
            description="管理系統備份檔案，可建立、刪除或還原備份。"
            type="info"
            showIcon
          />
        </Col>
        <Col>
          <Button
            type="primary"
            icon={<DatabaseOutlined />}
            onClick={onCreateBackup}
            loading={loading}
          >
            立即備份
          </Button>
        </Col>
      </Row>

      <Card title="資料庫備份" size="small">
        <ResponsiveTable
          columns={backupColumns}
          dataSource={backups?.database_backups || []}
          rowKey="path"
          size="small"
          scroll={{ x: 700 }}
          mobileHiddenColumns={['stats', 'created_at']}
          pagination={{ pageSize: 10 }}
          loading={loading}
        />
      </Card>

      <Card title="附件備份" size="small">
        <ResponsiveTable
          columns={backupColumns}
          dataSource={backups?.attachment_backups || []}
          rowKey="path"
          size="small"
          scroll={{ x: 700 }}
          mobileHiddenColumns={['stats', 'created_at']}
          pagination={{ pageSize: 10 }}
          loading={loading}
        />
      </Card>
    </Space>
  );
};
