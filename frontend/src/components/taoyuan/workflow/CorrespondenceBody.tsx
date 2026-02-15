/**
 * CorrespondenceBody - 公文對照雙欄（來文/發文）
 *
 * 可獨立使用於：
 * - 工程總覽的 CorrespondenceMatrix（多派工 Collapse 面板內容）
 * - 派工作業歷程的公文對照視圖（單一派工直接呈現）
 *
 * @version 1.0.0
 * @date 2026-02-13
 */

import React, { useState } from 'react';
import {
  Tag,
  Typography,
  Row,
  Col,
  Empty,
  Badge,
  Tooltip,
  Button,
  theme,
} from 'antd';
import {
  FileTextOutlined,
  SendOutlined,
  EditOutlined,
  DownOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import type { WorkRecord, DocBrief } from '../../../types/taoyuan';
import {
  statusLabel,
  statusColor,
} from './useProjectWorkData';
import {
  getCategoryLabel,
  getCategoryColor,
} from './chainConstants';

const { Text } = Typography;

// ============================================================================
// DocEntry - 單筆公文項目
// ============================================================================

export interface DocEntryProps {
  doc: DocBrief;
  record: WorkRecord;
  direction: 'incoming' | 'outgoing';
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  canEdit?: boolean;
}

const DocEntryInner: React.FC<DocEntryProps> = ({
  doc,
  record,
  direction,
  onDocClick,
  onEditRecord,
  canEdit,
}) => {
  const { token } = theme.useToken();
  const dateStr = doc.doc_date ? dayjs(doc.doc_date).format('YYYY.MM.DD') : '';
  const isIncoming = direction === 'incoming';

  return (
    <div
      style={{
        padding: '6px 8px',
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: 4,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        {/* 文號 + 日期 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
          {isIncoming ? (
            <FileTextOutlined style={{ color: token.colorPrimary, fontSize: 12 }} />
          ) : (
            <SendOutlined style={{ color: '#52c41a', fontSize: 12 }} />
          )}
          {doc.doc_number ? (
            <Text
              style={{
                fontSize: 12,
                cursor: onDocClick ? 'pointer' : 'default',
                color: onDocClick ? token.colorPrimary : undefined,
              }}
              onClick={() => doc.id && onDocClick?.(doc.id)}
            >
              {doc.doc_number}
            </Text>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              (無文號)
            </Text>
          )}
          {dateStr && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {dateStr}
            </Text>
          )}
        </div>

        {/* 說明 */}
        {(record.description || doc.subject) && (
          <Text
            type="secondary"
            ellipsis={{ tooltip: record.description || doc.subject }}
            style={{ display: 'block', fontSize: 12, marginTop: 2 }}
          >
            {record.description || doc.subject}
          </Text>
        )}

        {/* 類別標籤（getCategoryLabel 自動處理新/舊格式 fallback） */}
        <Tag
          color={getCategoryColor(record)}
          style={{ fontSize: 10, lineHeight: '16px', marginTop: 2 }}
        >
          {getCategoryLabel(record)}
        </Tag>
        <Tag
          color={statusColor(record.status)}
          style={{ fontSize: 10, lineHeight: '16px', marginTop: 2 }}
        >
          {statusLabel(record.status)}
        </Tag>
      </div>

      {canEdit && onEditRecord && (
        <Tooltip title="編輯紀錄">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => onEditRecord(record)}
            style={{ flexShrink: 0 }}
          />
        </Tooltip>
      )}
    </div>
  );
};

export const DocEntry = React.memo(DocEntryInner);

// ============================================================================
// CorrespondenceBody - 來文/發文雙欄
// ============================================================================

export interface CorrespondenceBodyData {
  incomingDocs: { record: WorkRecord; doc: DocBrief }[];
  outgoingDocs: { record: WorkRecord; doc: DocBrief }[];
}

export interface CorrespondenceBodyProps {
  data: CorrespondenceBodyData;
  onDocClick?: (docId: number) => void;
  onEditRecord?: (record: WorkRecord) => void;
  canEdit?: boolean;
  /** 預設顯示上限（超過則顯示「展開更多」），0 = 不限制 */
  defaultVisibleCount?: number;
}

/** 預設每欄最多顯示 15 筆 */
const DEFAULT_VISIBLE_COUNT = 15;

const CorrespondenceBodyInner: React.FC<CorrespondenceBodyProps> = ({
  data,
  onDocClick,
  onEditRecord,
  canEdit,
  defaultVisibleCount = DEFAULT_VISIBLE_COUNT,
}) => {
  const { token } = theme.useToken();
  const { incomingDocs, outgoingDocs } = data;
  const [expandedIncoming, setExpandedIncoming] = useState(false);
  const [expandedOutgoing, setExpandedOutgoing] = useState(false);

  if (incomingDocs.length === 0 && outgoingDocs.length === 0) {
    return (
      <Empty
        description="尚無關聯公文紀錄"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        style={{ padding: '16px 0' }}
      />
    );
  }

  const limit = defaultVisibleCount > 0 ? defaultVisibleCount : Infinity;
  const visibleIncoming = expandedIncoming ? incomingDocs : incomingDocs.slice(0, limit);
  const visibleOutgoing = expandedOutgoing ? outgoingDocs : outgoingDocs.slice(0, limit);
  const hasMoreIncoming = incomingDocs.length > limit;
  const hasMoreOutgoing = outgoingDocs.length > limit;

  return (
    <Row gutter={12}>
      {/* 機關來文 */}
      <Col xs={24} md={12}>
        <div
          style={{
            borderRadius: 6,
            border: `1px solid ${token.colorBorderSecondary}`,
            overflow: 'hidden',
            marginBottom: 8,
          }}
        >
          <div
            style={{
              padding: '6px 10px',
              background: '#e6f4ff',
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Text strong style={{ fontSize: 12, color: '#1677ff' }}>
              <FileTextOutlined /> 機關來文
            </Text>
            <Badge
              count={incomingDocs.length}
              style={{ backgroundColor: '#1677ff' }}
              size="small"
            />
          </div>
          {incomingDocs.length > 0 ? (
            <>
              {visibleIncoming.map((item, i) => (
                <DocEntry
                  key={item.record.id || i}
                  doc={item.doc}
                  record={item.record}
                  direction="incoming"
                  onDocClick={onDocClick}
                  onEditRecord={onEditRecord}
                  canEdit={canEdit}
                />
              ))}
              {hasMoreIncoming && !expandedIncoming && (
                <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                  <Button
                    type="link"
                    size="small"
                    icon={<DownOutlined />}
                    onClick={() => setExpandedIncoming(true)}
                  >
                    展開全部 ({incomingDocs.length} 筆)
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: '12px', textAlign: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                無來文紀錄
              </Text>
            </div>
          )}
        </div>
      </Col>

      {/* 公司發文 */}
      <Col xs={24} md={12}>
        <div
          style={{
            borderRadius: 6,
            border: `1px solid ${token.colorBorderSecondary}`,
            overflow: 'hidden',
            marginBottom: 8,
          }}
        >
          <div
            style={{
              padding: '6px 10px',
              background: '#f6ffed',
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Text strong style={{ fontSize: 12, color: '#52c41a' }}>
              <SendOutlined /> 公司發文
            </Text>
            <Badge
              count={outgoingDocs.length}
              style={{ backgroundColor: '#52c41a' }}
              size="small"
            />
          </div>
          {outgoingDocs.length > 0 ? (
            <>
              {visibleOutgoing.map((item, i) => (
                <DocEntry
                  key={item.record.id || i}
                  doc={item.doc}
                  record={item.record}
                  direction="outgoing"
                  onDocClick={onDocClick}
                  onEditRecord={onEditRecord}
                  canEdit={canEdit}
                />
              ))}
              {hasMoreOutgoing && !expandedOutgoing && (
                <div style={{ padding: '4px 8px', textAlign: 'center' }}>
                  <Button
                    type="link"
                    size="small"
                    icon={<DownOutlined />}
                    onClick={() => setExpandedOutgoing(true)}
                  >
                    展開全部 ({outgoingDocs.length} 筆)
                  </Button>
                </div>
              )}
            </>
          ) : (
            <div style={{ padding: '12px', textAlign: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                無發文紀錄
              </Text>
            </div>
          )}
        </div>
      </Col>
    </Row>
  );
};

export const CorrespondenceBody = React.memo(CorrespondenceBodyInner);
