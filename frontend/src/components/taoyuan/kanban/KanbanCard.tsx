/**
 * KanbanCard - 看板派工單卡片
 *
 * 顯示派工單摘要：單號、分案名稱、狀態、承辦人、關聯公文數、紀錄數
 *
 * @version 1.2.0 - 修正 docCount 重複計算、優化主標題顯示
 * @date 2026-02-13
 */

import React from 'react';
import { Card, Tag, Typography, Space, Button, Progress, theme } from 'antd';
import { FileTextOutlined, HistoryOutlined, PlayCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';

import { STATUS_CONFIG, STATUS_BUTTON_CONFIG, NEXT_STATUS, type KanbanCardData } from './kanbanConstants';
import type { WorkRecordStatus } from '../../../types/taoyuan';

const { Text } = Typography;

/** Calculate deadline countdown info for display */
function getDeadlineInfo(deadline?: string): { text: string; color: string } | null {
  if (!deadline) return null;
  const dl = new Date(deadline);
  const now = new Date();
  const diffDays = Math.ceil((dl.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (diffDays < 0) return { text: `逾期 ${Math.abs(diffDays)} 天`, color: '#ff4d4f' };
  if (diffDays === 0) return { text: '今日到期', color: '#ff4d4f' };
  if (diffDays <= 3) return { text: `剩 ${diffDays} 天`, color: '#fa8c16' };
  if (diffDays <= 7) return { text: `剩 ${diffDays} 天`, color: '#faad14' };
  return null; // Don't show if > 7 days
}

interface KanbanCardProps {
  data: KanbanCardData;
  onClick: (dispatchId: number) => void;
  onStatusChange?: (dispatchId: number, recordIds: number[], newStatus: WorkRecordStatus) => void;
  isUpdating?: boolean;
}

const KanbanCardInner: React.FC<KanbanCardProps> = ({ data, onClick, onStatusChange, isUpdating }) => {
  const { dispatch, computedStatus, recordCount, recordIds } = data;
  const { token } = theme.useToken();
  const statusCfg = STATUS_CONFIG[computedStatus] || STATUS_CONFIG.pending;

  // linked_documents 已包含 agency_doc + company_doc（_sync_document_links 同步）
  const docCount = dispatch.linked_documents?.length ?? 0;

  // 卡片主標題：分案名稱 > 派工單號（project_name 在同工程下重複）
  const title = dispatch.sub_case_name || dispatch.dispatch_no;
  const tooltipTitle = dispatch.sub_case_name
    ? `${dispatch.dispatch_no} - ${dispatch.sub_case_name}`
    : dispatch.dispatch_no;

  return (
    <Card
      size="small"
      hoverable
      onClick={() => onClick(dispatch.id)}
      style={{
        marginBottom: 8,
        borderRadius: 8,
        border: `1px solid ${token.colorBorderSecondary}`,
        background: token.colorBgContainer,
        cursor: 'pointer',
      }}
      styles={{
        body: { padding: '10px 12px' },
      }}
    >
      {/* Header: 狀態 + 截止倒數 + 單號 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <Space size={4}>
          <Tag
            color={statusCfg.color}
            style={{ margin: 0, fontSize: 11, lineHeight: '18px', borderRadius: 4 }}
          >
            {statusCfg.label}
          </Tag>
          {(() => {
            if (computedStatus === 'completed') return null;
            const dlInfo = getDeadlineInfo(dispatch.deadline);
            return dlInfo ? (
              <Tag color={dlInfo.color} style={{ margin: 0, fontSize: 10, lineHeight: '16px', borderRadius: 4 }}>
                {dlInfo.text}
              </Tag>
            ) : null;
          })()}
        </Space>
        <Text type="secondary" style={{ fontSize: 11 }}>
          {dispatch.dispatch_no}
        </Text>
      </div>

      {/* 主標題：分案名稱（或派工單號） */}
      <Text
        strong
        ellipsis={{ tooltip: tooltipTitle }}
        style={{ display: 'block', marginBottom: 6, fontSize: 13 }}
      >
        {title}
      </Text>

      {/* Footer: 承辦人 + 統計 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {dispatch.case_handler ? (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {dispatch.case_handler}
          </Text>
        ) : (
          <span />
        )}
        <Space size={8}>
          {docCount > 0 && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              <FileTextOutlined /> {docCount}
            </Text>
          )}
          {recordCount > 0 && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              <HistoryOutlined /> {recordCount}
            </Text>
          )}
        </Space>
      </div>

      {/* Progress bar */}
      {recordCount > 0 && (
        <div style={{ marginTop: 4 }}>
          <Progress
            percent={Math.round((dispatch.work_progress?.completed ?? 0) / Math.max(recordCount, 1) * 100)}
            size="small"
            strokeColor={computedStatus === 'completed' ? '#52c41a' : '#1677ff'}
            format={() => `${dispatch.work_progress?.completed ?? 0}/${recordCount}`}
            style={{ marginBottom: 0 }}
          />
        </div>
      )}

      {/* Quick status toggle */}
      {onStatusChange && STATUS_BUTTON_CONFIG[computedStatus] && NEXT_STATUS[computedStatus] && recordIds.length > 0 && (
        <Button
          type="link"
          size="small"
          icon={STATUS_BUTTON_CONFIG[computedStatus]!.icon === 'play' ? <PlayCircleOutlined /> : <CheckCircleOutlined />}
          loading={isUpdating}
          onClick={(e) => {
            e.stopPropagation();
            onStatusChange(dispatch.id, recordIds, NEXT_STATUS[computedStatus]!);
          }}
          style={{ padding: 0, fontSize: 12, marginTop: 4, height: 'auto', lineHeight: 1 }}
        >
          {STATUS_BUTTON_CONFIG[computedStatus]!.label}
        </Button>
      )}
    </Card>
  );
};

export const KanbanCard = React.memo(KanbanCardInner);
