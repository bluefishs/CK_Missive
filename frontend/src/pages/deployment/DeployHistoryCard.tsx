import React from 'react';
import { Card, Table, Space, Button, Tag, Tooltip, Badge, Typography } from 'antd';
import {
  HistoryOutlined,
  ReloadOutlined,
  BranchesOutlined,
  UserOutlined,
  FileTextOutlined,
  GithubOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { ColumnsType } from 'antd/es/table';
import type { DeploymentRecord, DeploymentStatus } from '../../api/deploymentApi';
import { DeploymentStatusTag } from './StatusTags';

const { Text } = Typography;

interface DeployHistoryCardProps {
  deployHistory: { records: DeploymentRecord[]; total: number } | null;
  historyLoading: boolean;
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number, size: number) => void;
  onRefresh: () => void;
  onViewLogs: (runId: number) => void;
}

export const DeployHistoryCard: React.FC<DeployHistoryCardProps> = ({
  deployHistory,
  historyLoading,
  currentPage,
  pageSize,
  onPageChange,
  onRefresh,
  onViewLogs,
}) => {
  const historyColumns: ColumnsType<DeploymentRecord> = [
    {
      title: '#',
      dataIndex: 'run_number',
      key: 'run_number',
      width: 70,
      render: (num: number) => <Text strong>#{num}</Text>,
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: DeploymentStatus, record) => (
        <DeploymentStatusTag status={status} conclusion={record.conclusion} />
      ),
    },
    {
      title: '分支',
      dataIndex: 'branch',
      key: 'branch',
      width: 120,
      render: (branch: string) => (
        <Tag icon={<BranchesOutlined />} color="blue">
          {branch}
        </Tag>
      ),
    },
    {
      title: 'Commit',
      dataIndex: 'commit_sha',
      key: 'commit_sha',
      width: 100,
      render: (sha: string) => (
        <Tooltip title={sha}>
          <code>{sha}</code>
        </Tooltip>
      ),
    },
    {
      title: '訊息',
      dataIndex: 'commit_message',
      key: 'commit_message',
      width: 250,
      ellipsis: { showTitle: false },
      render: (msg: string) => (
        <Tooltip title={msg} placement="topLeft">
          <span>{msg || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '觸發者',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
      width: 120,
      render: (user: string) => (
        <Space>
          <UserOutlined />
          {user}
        </Space>
      ),
    },
    {
      title: '開始時間',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 160,
      render: (time: string) => (
        <Tooltip title={dayjs(time).format('YYYY-MM-DD HH:mm:ss')}>
          {dayjs(time).fromNow()}
        </Tooltip>
      ),
    },
    {
      title: '耗時',
      dataIndex: 'duration_seconds',
      key: 'duration_seconds',
      width: 80,
      render: (seconds: number) =>
        seconds ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : '-',
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, record) => (
        <Space>
          <Tooltip title="查看日誌">
            <Button
              type="link"
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => onViewLogs(record.id)}
            />
          </Tooltip>
          <Tooltip title="在 GitHub 查看">
            <Button
              type="link"
              size="small"
              icon={<GithubOutlined />}
              href={record.url}
              target="_blank"
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <HistoryOutlined />
          部署歷史
          {deployHistory && (
            <Badge count={deployHistory.total} style={{ backgroundColor: '#1890ff' }} />
          )}
        </Space>
      }
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={onRefresh}
          loading={historyLoading}
          size="small"
        >
          刷新
        </Button>
      }
    >
      <Table
        columns={historyColumns}
        dataSource={deployHistory?.records || []}
        rowKey="id"
        loading={historyLoading}
        pagination={{
          current: currentPage,
          pageSize: pageSize,
          total: deployHistory?.total || 0,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 筆記錄`,
          onChange: onPageChange,
        }}
        scroll={{ x: 1000 }}
        size="small"
      />
    </Card>
  );
};
