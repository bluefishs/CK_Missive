/**
 * KanbanCard - 看板派工單卡片
 *
 * 顯示派工單摘要：單號、分案名稱、狀態、承辦人、關聯公文數、紀錄數
 *
 * @version 1.2.0 - 修正 docCount 重複計算、優化主標題顯示
 * @date 2026-02-13
 */

import React from 'react';
import { Card, Tag, Typography, Space, Button, theme } from 'antd';
import { FileTextOutlined, HistoryOutlined, PlayCircleOutlined, CheckCircleOutlined } from '@ant-design/icons';

import { STATUS_CONFIG, STATUS_BUTTON_CONFIG, NEXT_STATUS, type KanbanCardData } from './kanbanConstants';
import type { WorkRecordStatus } from '../../../types/taoyuan';

const { Text } = Typography;

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
      {/* Header: 狀態 + 單號 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <Tag
          color={statusCfg.color}
          style={{ margin: 0, fontSize: 11, lineHeight: '18px', borderRadius: 4 }}
        >
          {statusCfg.label}
        </Tag>
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
