import React from 'react';
import {
  Card, Button, Space, Row, Col, Alert, Statistic
} from 'antd';
import {
  PlayCircleOutlined, PauseCircleOutlined
} from '@ant-design/icons';
import type { SchedulerStatus } from '../../types/api';

interface SchedulerTabProps {
  schedulerStatus: SchedulerStatus | null;
  loading: boolean;
  onSchedulerToggle: () => void;
}

export const SchedulerTab: React.FC<SchedulerTabProps> = ({
  schedulerStatus,
  loading,
  onSchedulerToggle,
}) => {
  return (
    <Space vertical style={{ width: '100%' }} size="large">
      <Alert
        title="排程器設定"
        description="管理自動備份排程，系統會在設定的時間自動執行備份。"
        type="info"
        showIcon
      />

      <Card title="排程器狀態" size="small">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="運行狀態"
              value={schedulerStatus?.running ? '運行中' : '已停止'}
              styles={{ content: {
                color: schedulerStatus?.running ? '#3f8600' : '#cf1322'
              } }}
              prefix={schedulerStatus?.running ? <PlayCircleOutlined /> : <PauseCircleOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="備份時間"
              value={schedulerStatus?.backup_time || '--:--'}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="下次執行"
              value={schedulerStatus?.next_backup
                ? new Date(schedulerStatus.next_backup).toLocaleString('zh-TW')
                : '-'}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="上次執行"
              value={schedulerStatus?.last_backup
                ? new Date(schedulerStatus.last_backup).toLocaleString('zh-TW')
                : '-'}
            />
          </Col>
        </Row>

        <Row gutter={16} style={{ marginTop: 24 }}>
          <Col span={8}>
            <Statistic
              title="總備份次數"
              value={schedulerStatus?.stats?.total_backups || 0}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="成功次數"
              value={schedulerStatus?.stats?.successful_backups || 0}
              styles={{ content: { color: '#3f8600' } }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="失敗次數"
              value={schedulerStatus?.stats?.failed_backups || 0}
              styles={schedulerStatus?.stats?.failed_backups ? { content: { color: '#cf1322' } } : undefined}
            />
          </Col>
        </Row>
      </Card>

      <Card title="控制" size="small">
        <Space>
          <Button
            type={schedulerStatus?.running ? 'default' : 'primary'}
            icon={schedulerStatus?.running ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={onSchedulerToggle}
            loading={loading}
          >
            {schedulerStatus?.running ? '停止排程器' : '啟動排程器'}
          </Button>
        </Space>
      </Card>
    </Space>
  );
};
