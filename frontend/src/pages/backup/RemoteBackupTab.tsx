import React from 'react';
import {
  Card, Button, Space, Row, Col, Alert, Statistic,
  Form, Input, Switch, InputNumber, Tooltip
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
  // ── 健康判定：以 NAS 上「最新 dump 的時間」為唯一依據（ground truth）──
  // 舊版只顯示容器端 sync_enabled（刻意關閉）與可能過期的 last_sync_time，
  // 導致「開關是關的 → 無法確認服務是否正常」。改由實際檔案回答。
  const latestTimeStr = remoteConfig?.latest_remote_time ?? remoteConfig?.last_sync_time;
  const latestTime = latestTimeStr ? new Date(latestTimeStr) : null;
  const ageHours = latestTime ? (Date.now() - latestTime.getTime()) / 36e5 : null;
  const hasError = remoteConfig?.last_sync_result === 'error';
  // 每日 03:00 執行 → 36 小時內有新檔即正常（容許單次延遲/重啟）
  const isHealthy = !hasError && ageHours !== null && ageHours < 36;
  const healthText = hasError
    ? '異常：最近一次同步失敗'
    : ageHours === null
      ? '無法判定：尚無同步紀錄'
      : isHealthy
        ? '正常運作中'
        : `異常：NAS 最新備份已 ${Math.floor(ageHours / 24)} 天未更新`;

  return (
    <Space vertical style={{ width: '100%' }} size="large">
      <Alert
        title={`異地備份${healthText}`}
        description={
          <>
            執行方式：Windows 排程「CK-Missive-Offsite-Backup」每日 03:00，
            把容器每日 02:00 產生的 DB dump 複製到 NAS（保留 30 份）。
            {remoteConfig?.remote_path ? `目的地：${remoteConfig.remote_path}` : ''}
            {hasError && remoteConfig?.last_sync_message
              ? ` 失敗原因：${remoteConfig.last_sync_message}`
              : ''}
          </>
        }
        type={isHealthy ? 'success' : hasError || ageHours !== null ? 'error' : 'warning'}
        showIcon
      />

      <Card title="NAS 實際狀態（判斷是否正常請看這裡）" size="small">
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="NAS 最新備份時間"
              value={latestTime ? latestTime.toLocaleString('zh-TW') : '尚無資料'}
              styles={{ content: { color: isHealthy ? '#3f8600' : '#cf1322', fontSize: 16 } }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="NAS 現存份數"
              value={remoteConfig?.remote_file_count ?? '—'}
              suffix={remoteConfig?.remote_file_count != null ? '份' : ''}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="最新備份檔"
              value={remoteConfig?.latest_remote_file ?? '—'}
              styles={{ content: { fontSize: 13, wordBreak: 'break-all' } }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="檔案大小"
              value={remoteConfig?.latest_remote_size_mb ?? '—'}
              suffix={remoteConfig?.latest_remote_size_mb != null ? 'MB' : ''}
            />
          </Col>
        </Row>
        <div style={{ marginTop: 12, color: '#888', fontSize: 12 }}>
          最後一次排程執行：
          {remoteConfig?.last_sync_time
            ? new Date(remoteConfig.last_sync_time).toLocaleString('zh-TW')
            : '無紀錄'}
          {remoteConfig?.last_sync_result ? `（${remoteConfig.last_sync_result}）` : ''}
          {remoteConfig?.last_sync_source ? ` 執行者：${remoteConfig.last_sync_source}` : ''}
        </div>
        {remoteConfig?.remote_file_count == null && (
          <div style={{ marginTop: 8, color: '#d46b08', fontSize: 12 }}>
            尚未取得 NAS 明細 — 需待下次排程（每日 03:00）執行後才會寫入；
            或手動執行 <code>scripts\backup\offsite-sync-nas.ps1</code> 立即更新。
          </div>
        )}
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
            label="容器端自動同步（非現行機制，維持關閉即可）"
            valuePropName="checked"
            extra="⚠️ 這個開關與上方 NAS 狀態無關。後端容器是 Linux，無法存取 Windows 網路磁碟，因此這條路刻意停用；打開也不會生效。異地備份實際由 Windows 排程執行，正常與否請看上方「NAS 實際狀態」。"
          >
            <Switch disabled />
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
              <Tooltip title="容器端無法存取 Windows NAS，此按鈕不會有作用。要立即同步請在主機執行 scripts\backup\offsite-sync-nas.ps1，或等每日 03:00 排程。">
                <Button
                  icon={<CloudUploadOutlined />}
                  onClick={onRemoteSync}
                  loading={loading}
                  disabled
                >
                  立即同步（容器端，停用）
                </Button>
              </Tooltip>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
};
