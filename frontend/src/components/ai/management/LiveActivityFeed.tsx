/**
 * LiveActivityFeed — 即時 Swarm 轉播卡片 (V-2.2)
 *
 * 以時間軸形式呈現 OpenClaw EventRelay 的即時任務事件，
 * 含狀態色標、agent 標籤、耗時等資訊。
 *
 * @version 1.0.0
 * @created 2026-03-23
 */

import React from 'react';
import { Badge, Card, Empty, Space, Tag, Timeline, Typography } from 'antd';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import type { LiveJobEvent } from '../../../hooks/system/useLiveActivitySSE';

const { Text } = Typography;

const EVENT_CONFIG: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  job_created:          { color: 'blue',      label: '建立',   icon: <PlusOutlined /> },
  job_running:          { color: 'processing', label: '執行中', icon: <PlayCircleOutlined /> },
  job_pending_approval: { color: 'purple',    label: '待審批', icon: <ClockCircleOutlined /> },
  job_approved:         { color: 'success',   label: '已核准', icon: <CheckCircleOutlined /> },
  job_rejected:         { color: 'error',     label: '已拒絕', icon: <CloseCircleOutlined /> },
  job_completed:        { color: 'cyan',      label: '完成',   icon: <CheckCircleOutlined /> },
  job_failed:           { color: 'error',     label: '失敗',   icon: <ExclamationCircleOutlined /> },
};

const DEFAULT_CONFIG = { color: 'default', label: '未知', icon: <ClockCircleOutlined /> };

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('zh-TW', { hour12: false });
  } catch {
    return iso;
  }
}

interface LiveActivityFeedProps {
  events: LiveJobEvent[];
  isConnected: boolean;
}

export const LiveActivityFeed: React.FC<LiveActivityFeedProps> = React.memo(({ events, isConnected }) => {
  return (
    <Card
      title={
        <Space>
          <ThunderboltOutlined />
          <span>即時 Swarm 轉播</span>
          <Badge
            status={isConnected ? 'processing' : 'default'}
            text={isConnected ? '已連線' : '離線'}
          />
        </Space>
      }
      size="small"
    >
      {events.length === 0 ? (
        <Empty
          description={isConnected ? '等待事件中...' : '尚未連線至 EventRelay'}
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      ) : (
        <Timeline
          style={{ maxHeight: 400, overflowY: 'auto', paddingTop: 8 }}
          items={events.map((evt, i) => {
            const cfg = EVENT_CONFIG[evt.type] ?? DEFAULT_CONFIG;
            const p = evt.payload;

            return {
              key: `${evt.timestamp}-${i}`,
              dot: cfg.icon,
              color: cfg.color === 'processing' ? 'blue' : cfg.color,
              children: (
                <div style={{ fontSize: 12 }}>
                  <Space size={4} wrap>
                    <Tag color={cfg.color} style={{ fontSize: 11 }}>{cfg.label}</Tag>
                    {p.agent_id && <Tag style={{ fontSize: 11 }}>{p.agent_id}</Tag>}
                    {p.job_id && (
                      <Text code style={{ fontSize: 10 }}>
                        {p.job_id.length > 16 ? `${p.job_id.slice(0, 16)}…` : p.job_id}
                      </Text>
                    )}
                  </Space>
                  <div style={{ marginTop: 2 }}>
                    {p.approved_by && (
                      <Text type="secondary" style={{ fontSize: 11 }}>核准: {p.approved_by} </Text>
                    )}
                    {p.rejected_by && (
                      <Text type="secondary" style={{ fontSize: 11 }}>拒絕: {p.rejected_by} </Text>
                    )}
                    {p.reason && (
                      <Text type="secondary" style={{ fontSize: 11 }}>原因: {p.reason} </Text>
                    )}
                    {p.error && (
                      <Text type="danger" style={{ fontSize: 11 }}>錯誤: {p.error} </Text>
                    )}
                    {p.answer_length != null && (
                      <Text type="secondary" style={{ fontSize: 11 }}>回應 {p.answer_length} 字 </Text>
                    )}
                    <Text type="secondary" style={{ fontSize: 10, float: 'right' }}>
                      {formatTime(evt.timestamp)}
                    </Text>
                  </div>
                </div>
              ),
            };
          })}
        />
      )}
    </Card>
  );
});

LiveActivityFeed.displayName = 'LiveActivityFeed';

export default LiveActivityFeed;
