/**
 * 晨報與推播 — 營運核心 Tab（2026-08-02）
 *
 * owner：「/ops 頁面資訊過多且對營運核心資訊雜亂，晨報與 LINE 推播請獨立 tab」。
 *
 * 取代原本擠在左側欄的 `MorningReportCard`（只有預覽／推送兩個動作）。
 * 這裡要回答的是營運上真正會問的三個問題：
 *   1. 今天的晨報長什麼樣？（預覽／手動補推）
 *   2. 最近有沒有推失敗？（近 7 日派送 log ＋ 連續失敗天數）
 *   3. LINE 這個月還能推幾則？（月配額，避免月底突然靜音）
 *
 * 資料全部來自**既有但先前零消費**的端點：
 *   - MORNING_REPORT_STATUS  近 7 日 delivery log + 連續失敗天數 + LINE 配額
 *   - MORNING_REPORT_HISTORY 近 14 日快照（內文長度／段落數）
 * 唯一新增的後端欄位是 `line_quota`，併入 status 而非另開端點——
 * 前端要的是「這個月還能推幾則」，與派送狀態是同一個判讀情境。
 */

import React, { useState } from 'react';
import {
  Card, Row, Col, Button, Space, Typography, Tag, Alert, Statistic, Progress, Empty,
} from 'antd';
import { FileTextOutlined, SendOutlined, ReloadOutlined } from '@ant-design/icons';
import { useMutation, useQuery } from '@tanstack/react-query';

import { apiClient } from '../../api/client';
import { AI_ENDPOINTS } from '../../api/endpoints';
import { EnhancedTable } from '../../components/common/EnhancedTable';
import type { ResponsiveColumn } from '../../components/common/EnhancedTable';

const { Text, Paragraph } = Typography;

interface DeliveryRow {
  id: number;
  report_date: string;
  channel: string;
  recipient?: string | null;
  status: string;
  error_msg?: string | null;
  summary_length?: number | null;
  sections_count?: number | null;
  trigger_source?: string | null;
}

interface LineQuota {
  available: boolean;
  reason?: string;
  month: string;
  used?: number;
  cap: number;
  hard_limit?: number;
  remaining?: number;
}

interface StatusResp {
  success: boolean;
  today?: string;
  deliveries?: DeliveryRow[];
  alerts?: {
    telegram_consecutive_failures: number;
    line_consecutive_failures: number;
    should_alert: boolean;
  };
  line_quota?: LineQuota;
}

interface SnapshotRow {
  report_date: string;
  summary_length?: number | null;
  sections_count?: number | null;
  generator_version?: string | null;
  generated_at?: string | null;
}

const CHANNEL_COLOR: Record<string, string> = { line: 'green', telegram: 'blue' };

export const MorningReportOpsTab: React.FC = () => {
  const [preview, setPreview] = useState<string | null>(null);

  const { data: status, isLoading: statusLoading, refetch: refetchStatus } = useQuery<StatusResp>({
    queryKey: ['morning-report-status'],
    queryFn: () => apiClient.post(AI_ENDPOINTS.MORNING_REPORT_STATUS, {}),
    staleTime: 60_000,
  });

  const { data: history, isLoading: historyLoading } = useQuery<{ success: boolean; snapshots?: SnapshotRow[] }>({
    queryKey: ['morning-report-history'],
    queryFn: () => apiClient.post(AI_ENDPOINTS.MORNING_REPORT_HISTORY, {}),
    staleTime: 5 * 60_000,
  });

  const loadPreview = useMutation({
    mutationFn: () =>
      apiClient.post<{ success: boolean; summary: string }>(AI_ENDPOINTS.MORNING_REPORT_PREVIEW, {}),
    onSuccess: (d) => setPreview(d.summary),
  });

  const pushReport = useMutation({
    mutationFn: () =>
      apiClient.post<{ success: boolean; pushed_to: string[]; message: string }>(
        AI_ENDPOINTS.MORNING_REPORT_PUSH, {},
      ),
    onSuccess: (d) => {
      setPreview((prev) => (prev ? `${prev}\n\n--- ${d.message}` : d.message));
      refetchStatus();  // 推完立刻反映到派送狀態，不用手動重整
    },
  });

  const alerts = status?.alerts;
  const quota = status?.line_quota;
  const deliveries = status?.deliveries ?? [];
  const snapshots = history?.snapshots ?? [];

  const deliveryColumns: ResponsiveColumn<DeliveryRow>[] = [
    { title: '日期', dataIndex: 'report_date', key: 'report_date', width: 110 },
    {
      title: '管道', dataIndex: 'channel', key: 'channel', width: 90,
      render: (v: string) => <Tag color={CHANNEL_COLOR[v] ?? 'default'}>{v}</Tag>,
    },
    {
      title: '結果', dataIndex: 'status', key: 'status', width: 90,
      render: (v: string, r) => (
        <Tag color={v === 'success' ? 'green' : 'red'} title={r.error_msg ?? undefined}>
          {v === 'success' ? '成功' : v}
        </Tag>
      ),
    },
    {
      title: '內文長度', dataIndex: 'summary_length', key: 'summary_length', width: 100,
      align: 'right', hideOnMobile: true,
      render: (v?: number | null) => (v != null ? `${v} 字` : '-'),
    },
    {
      title: '段落', dataIndex: 'sections_count', key: 'sections_count', width: 70,
      align: 'center', hideOnMobile: true,
      render: (v?: number | null) => v ?? '-',
    },
    {
      title: '觸發來源', dataIndex: 'trigger_source', key: 'trigger_source', width: 110,
      hideOnMobile: true, render: (v?: string | null) => v ?? '-',
    },
    {
      title: '錯誤', dataIndex: 'error_msg', key: 'error_msg', ellipsis: true,
      hideOnMobile: true, render: (v?: string | null) => v || '-',
    },
  ];

  const snapshotColumns: ResponsiveColumn<SnapshotRow>[] = [
    { title: '日期', dataIndex: 'report_date', key: 'report_date', width: 110 },
    {
      title: '內文長度', dataIndex: 'summary_length', key: 'summary_length', width: 110,
      align: 'right', render: (v?: number | null) => (v != null ? `${v} 字` : '-'),
    },
    {
      title: '段落數', dataIndex: 'sections_count', key: 'sections_count', width: 90,
      align: 'center', render: (v?: number | null) => v ?? '-',
    },
    {
      title: '產生器版本', dataIndex: 'generator_version', key: 'generator_version',
      width: 110, hideOnMobile: true, render: (v?: string | null) => v ?? '-',
    },
  ];

  return (
    <div>
      {/* 有連續失敗才顯示——沒事的時候不佔版面 */}
      {alerts?.should_alert && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message="晨報推播連續失敗"
          description={
            `LINE 連續失敗 ${alerts.line_consecutive_failures} 天、`
            + `Telegram 連續失敗 ${alerts.telegram_consecutive_failures} 天。`
            + '請確認頻道設定與月配額。'
          }
        />
      )}

      <Row gutter={[16, 16]}>
        {/* ── 今日晨報 ── */}
        <Col xs={24} lg={12}>
          <Card
            size="small"
            title={<span><FileTextOutlined /> 今日晨報</span>}
            extra={
              <Space size={4}>
                <Button size="small" icon={<FileTextOutlined />}
                  onClick={() => loadPreview.mutate()} loading={loadPreview.isPending}>
                  預覽
                </Button>
                <Button size="small" type="primary" icon={<SendOutlined />}
                  onClick={() => pushReport.mutate()} loading={pushReport.isPending}
                  disabled={!preview}>
                  推送
                </Button>
              </Space>
            }
          >
            <Paragraph style={{ fontSize: 12, whiteSpace: 'pre-wrap', maxHeight: 260, overflowY: 'auto', marginBottom: 0 }}>
              {preview || '點擊「預覽」查看今日晨報內容；確認無誤後才會啟用「推送」。'}
            </Paragraph>
          </Card>
        </Col>

        {/* ── LINE 月配額 ── */}
        <Col xs={24} lg={12}>
          <Card size="small" title="LINE 月推播配額"
            extra={<Button size="small" type="text" icon={<ReloadOutlined />}
              onClick={() => refetchStatus()} loading={statusLoading} />}>
            {quota?.available ? (
              <>
                <Row gutter={16}>
                  <Col xs={12} sm={8}><Statistic title="本月已推" value={quota.used ?? 0} suffix="則" /></Col>
                  <Col xs={12} sm={8}><Statistic title="剩餘" value={quota.remaining ?? 0} suffix="則" /></Col>
                  <Col xs={12} sm={8}><Statistic title="軟上限" value={quota.cap} suffix={`/${quota.hard_limit ?? 200}`} /></Col>
                </Row>
                <Progress
                  percent={Math.min(100, Math.round(((quota.used ?? 0) / (quota.cap || 1)) * 100))}
                  status={(quota.used ?? 0) >= quota.cap ? 'exception' : 'normal'}
                  style={{ marginTop: 8 }}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {quota.month}｜達軟上限即停止推播，為 LINE 硬限 {quota.hard_limit ?? 200} 則預留重試餘裕
                </Text>
              </>
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    配額查不到（{quota?.reason ?? '未知'}）——這不等於「本月未推播」
                  </Text>
                }
              />
            )}
          </Card>
        </Col>

        {/* ── 近 7 日派送狀態 ── */}
        <Col xs={24}>
          <Card size="small" title="近 7 日派送狀態">
            <EnhancedTable<DeliveryRow>
              columns={deliveryColumns}
              dataSource={deliveries}
              rowKey="id"
              loading={statusLoading}
              size="small"
              pagination={false}
              locale={{ emptyText: '近 7 日沒有派送紀錄' }}
            />
          </Card>
        </Col>

        {/* ── 近 14 日快照趨勢 ── */}
        <Col xs={24}>
          <Card size="small" title="近 14 日晨報快照"
            extra={<Text type="secondary" style={{ fontSize: 12 }}>內文長度突然變短＝內容來源可能斷了</Text>}>
            <EnhancedTable<SnapshotRow>
              columns={snapshotColumns}
              dataSource={snapshots}
              rowKey="report_date"
              loading={historyLoading}
              size="small"
              pagination={false}
              locale={{ emptyText: '近 14 日沒有快照' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default MorningReportOpsTab;
