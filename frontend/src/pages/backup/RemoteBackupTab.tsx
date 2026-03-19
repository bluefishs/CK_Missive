import React from 'react';
import {
  Card, Button, Space, Row, Col, Alert, Statistic,
  Form, Input, Switch, InputNumber
} from 'antd';
import type { FormInstance } from 'antd';
import { FolderOutlined, CloudUploadOutlined } from '@ant-design/icons';
import type { RemoteBackupConfig } from '../../types/api';

interface RemoteBackupTabProps {
  remoteConfig: RemoteBackupConfig | null;
  form: FormInstance;
  loading: boolean;
  onUpdateConfig: (values: { remote_path: string; sync_enabled: boolean; sync_interval_hours: number }) => void;
  onRemoteSync: () => void;
}

export const RemoteBackupTab: React.FC<RemoteBackupTabProps> = ({
  remoteConfig,
  form,
  loading,
  onUpdateConfig,
  onRemoteSync,
}) => {
  return (
    <Space vertical style={{ width: '100%' }} size="large">
      <Alert
        title="異地備份設定"
        description="設定異地備份路徑，系統會自動將備份同步到指定位置。"
        type="info"
        showIcon
      />

      <Card title="目前狀態" size="small">
        <Row gutter={16}>
          <Col span={8}>
            <Statistic
              title="同步狀態"
              value={remoteConfig?.sync_status === 'idle' ? '閒置' : remoteConfig?.sync_status === 'syncing' ? '同步中' : '錯誤'}
              styles={{ content: {
                color: remoteConfig?.sync_status === 'error' ? '#cf1322' : '#3f8600'
              } }}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="最後同步時間"
              value={remoteConfig?.last_sync_time
                ? new Date(remoteConfig.last_sync_time).toLocaleString('zh-TW')
                : '尚未同步'}
            />
          </Col>
          <Col span={8}>
            <Statistic
              title="同步間隔"
              value={remoteConfig?.sync_interval_hours || 24}
              suffix="小時"
            />
          </Col>
        </Row>
      </Card>

      <Card title="設定" size="small">
        <Form
          form={form}
          layout="vertical"
          onFinish={onUpdateConfig}
        >
          <Form.Item
            name="remote_path"
            label="異地備份路徑"
            rules={[{ required: true, message: '請輸入異地備份路徑' }]}
            extra="可使用本地路徑或網路共享路徑 (如: \\\\server\\backup)"
          >
            <Input
              prefix={<FolderOutlined />}
              placeholder="例如: D:\Backup 或 \\server\backup"
            />
          </Form.Item>

          <Form.Item
            name="sync_enabled"
            label="啟用自動同步"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item
            name="sync_interval_hours"
            label="同步間隔 (小時)"
            rules={[{ required: true, message: '請輸入同步間隔' }]}
          >
            <InputNumber min={1} max={168} style={{ width: 120 }} />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                儲存設定
              </Button>
              <Button
                icon={<CloudUploadOutlined />}
                onClick={onRemoteSync}
                loading={loading}
                disabled={!remoteConfig?.remote_path}
              >
                立即同步
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
};
