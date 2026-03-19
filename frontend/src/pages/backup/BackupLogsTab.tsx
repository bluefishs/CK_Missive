import React from 'react';
import {
  Card, Button, Space, Row, Col, Alert, Tag, Tooltip, Select
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons';
import { ResponsiveTable } from '../../components/common';
import type { BackupLogEntry, BackupLogListResponse } from '../../types/api';

interface LogFilters {
  page: number;
  page_size: number;
  action_filter: string | undefined;
  status_filter: string | undefined;
}

interface BackupLogsTabProps {
  logs: BackupLogListResponse | null;
  logFilters: LogFilters;
  loading: boolean;
  onLogFiltersChange: (updater: (prev: LogFilters) => LogFilters) => void;
  onRefreshLogs: () => void;
}

export const BackupLogsTab: React.FC<BackupLogsTabProps> = ({
  logs,
  logFilters,
  loading,
  onLogFiltersChange,
  onRefreshLogs,
}) => {
  const logColumns: ColumnsType<BackupLogEntry> = [
    {
      title: '時間',
      dataIndex: 'timestamp',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-TW')
    },
    {
      title: '操作',
      dataIndex: 'action',
      width: 100,
      render: (action: string) => {
        const actionMap: Record<string, { text: string; color: string }> = {
          create: { text: '建立', color: 'blue' },
          delete: { text: '刪除', color: 'red' },
          restore: { text: '還原', color: 'orange' },
          sync: { text: '同步', color: 'cyan' },
          config_update: { text: '設定', color: 'purple' }
        };
        const info = actionMap[action] || { text: action, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      }
    },
    {
      title: '狀態',
      dataIndex: 'status',
      width: 80,
      render: (status: string) => (
        status === 'success'
          ? <Tag icon={<CheckCircleOutlined />} color="success">成功</Tag>
          : <Tag icon={<CloseCircleOutlined />} color="error">失敗</Tag>
      )
    },
    {
      title: '詳細資訊',
      dataIndex: 'details',
      width: 250,
      ellipsis: { showTitle: false },
      render: (text: string) => text ? (
        <Tooltip title={text} placement="topLeft"><span>{text}</span></Tooltip>
      ) : '-'
    },
    {
      title: '操作者',
      dataIndex: 'operator',
      width: 100
    }
  ];

  return (
    <Space vertical style={{ width: '100%' }} size="large">
      <Alert
        title="備份日誌"
        description="查看所有備份操作的歷史記錄。"
        type="info"
        showIcon
      />

      <Card title="篩選條件" size="small">
        <Row gutter={16}>
          <Col span={6}>
            <Select
              placeholder="操作類型"
              style={{ width: '100%' }}
              allowClear
              value={logFilters.action_filter}
              onChange={(v) => onLogFiltersChange(prev => ({ ...prev, action_filter: v, page: 1 }))}
              options={[
                { value: 'create', label: '建立' },
                { value: 'delete', label: '刪除' },
                { value: 'restore', label: '還原' },
                { value: 'sync', label: '同步' },
                { value: 'config_update', label: '設定' }
              ]}
            />
          </Col>
          <Col span={6}>
            <Select
              placeholder="狀態"
              style={{ width: '100%' }}
              allowClear
              value={logFilters.status_filter}
              onChange={(v) => onLogFiltersChange(prev => ({ ...prev, status_filter: v, page: 1 }))}
              options={[
                { value: 'success', label: '成功' },
                { value: 'failed', label: '失敗' }
              ]}
            />
          </Col>
          <Col span={6}>
            <Button icon={<ReloadOutlined />} onClick={onRefreshLogs}>
              重新整理
            </Button>
          </Col>
        </Row>
      </Card>

      <ResponsiveTable
        columns={logColumns}
        dataSource={logs?.logs || []}
        rowKey="id"
        size="small"
        scroll={{ x: 600 }}
        mobileHiddenColumns={['operator', 'details']}
        loading={loading}
        pagination={{
          current: logs?.page || 1,
          pageSize: logs?.page_size || 20,
          total: logs?.total || 0,
          showTotal: (total: number) => `共 ${total} 筆記錄`,
          onChange: (page: number, pageSize: number) => onLogFiltersChange(prev => ({
            ...prev,
            page,
            page_size: pageSize
          }))
        }}
      />
    </Space>
  );
};
