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
        title="異地備份由 Windows 排程執行（運作中）"
        description={
          <>
            實際異地備份由 <b>Windows 排程 CK-Missive-Offsite-Backup</b> 每日 <b>03:00</b> 執行：
            將當日 DB dump 複製到 NAS <code>\\CKNAS\CK_Project\#Project_data\missive_databsae</code>（保留 30 份）。
            「目前狀態 → 最後同步時間」即反映此排程結果。<br />
            下方「啟用自動同步」開關為<b>容器端</b>同步；因後端容器（Linux）無法存取 Windows NAS 網路磁碟，
            <b>刻意維持關閉</b>——關閉不代表異地備份停止，NAS 仍由排程每日更新。
          </>
        }
        type="success"
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
            label="啟用自動同步（容器端）"
            valuePropName="checked"
            extra="容器端同步；因後端容器無法存取 Windows NAS，維持關閉。異地備份改由上方 Windows 排程執行。"
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
