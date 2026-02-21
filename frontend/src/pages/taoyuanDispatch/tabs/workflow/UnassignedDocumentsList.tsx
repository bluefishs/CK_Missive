/**
 * UnassignedDocumentsList - 未指派公文列表
 *
 * 顯示已關聯到派工單但尚未對應作業紀錄的公文：
 * - 分為來文/發文兩欄
 * - 每筆可快速新增作業紀錄或移除關聯
 * - 含警告標示的分隔線
 *
 * @version 1.0.0
 * @date 2026-02-21
 */

import React, { useCallback } from 'react';
import {
  Row,
  Col,
  Space,
  Button,
  Tooltip,
  Popconfirm,
  Badge,
  Divider,
  Typography,
  theme,
} from 'antd';
import {
  PlusOutlined,
  FileTextOutlined,
  SendOutlined,
  DisconnectOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { DispatchDocumentLink } from '../../../../types/api';
import type { UnassignedDocsData } from '../../../../components/taoyuan/workflow/useDispatchWorkData';

const { Text } = Typography;

export interface UnassignedDocumentsListProps {
  /** 未指派公文資料 */
  unassignedDocs: UnassignedDocsData;
  /** 是否有已指派的公文對照資料（用於控制分隔線顯示） */
  hasCorrespondence: boolean;
  /** 是否可編輯 */
  canEdit: boolean;
  /** 是否正在移除關聯 */
  unlinkPending: boolean;
  /** 點擊公文回調 */
  onDocClick: (docId: number) => void;
  /** 快速建立作業紀錄回調 */
  onQuickCreateRecord: (doc: DispatchDocumentLink) => void;
  /** 移除關聯回調 */
  onUnlinkDocument: (linkId: number | undefined) => void;
}

/** 單筆未指派公文項目 */
interface UnassignedDocItemProps {
  doc: DispatchDocumentLink;
  direction: 'incoming' | 'outgoing';
  canEdit: boolean;
  unlinkPending: boolean;
  onDocClick: (docId: number) => void;
  onQuickCreateRecord: (doc: DispatchDocumentLink) => void;
  onUnlinkDocument: (linkId: number | undefined) => void;
}

const UnassignedDocItemInner: React.FC<UnassignedDocItemProps> = ({
  doc,
  direction,
  canEdit,
  unlinkPending,
  onDocClick,
  onQuickCreateRecord,
  onUnlinkDocument,
}) => {
  const { token } = theme.useToken();
  const isIncoming = direction === 'incoming';

  return (
    <div
      style={{
        padding: '6px 8px',
        borderBottom: `1px dashed ${token.colorBorderSecondary}`,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: 4,
        background: token.colorBgTextHover,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
          {isIncoming ? (
            <FileTextOutlined style={{ color: token.colorPrimary, fontSize: 12 }} />
          ) : (
            <SendOutlined style={{ color: '#52c41a', fontSize: 12 }} />
          )}
          <Text
            style={{
              fontSize: 12,
              cursor: 'pointer',
              color: token.colorPrimary,
            }}
            onClick={() => onDocClick(doc.document_id)}
          >
            {doc.doc_number || `#${doc.document_id}`}
          </Text>
          {doc.doc_date && (
            <Text type="secondary" style={{ fontSize: 11 }}>
              {dayjs(doc.doc_date).format('YYYY.MM.DD')}
            </Text>
          )}
        </div>
        {doc.subject && (
          <Text
            type="secondary"
            ellipsis={{ tooltip: doc.subject }}
            style={{ display: 'block', fontSize: 12, marginTop: 1 }}
          >
            {doc.subject}
          </Text>
        )}
      </div>

      {canEdit && (
        <Space size={2}>
          <Tooltip title="新增作業紀錄">
            <Button
              type="link"
              size="small"
              icon={<PlusOutlined />}
              onClick={() => onQuickCreateRecord(doc)}
              style={{ fontSize: 12 }}
            />
          </Tooltip>
          {doc.link_id !== undefined && (
            <Popconfirm
              title="確定移除此公文關聯？"
              onConfirm={() => onUnlinkDocument(doc.link_id)}
              okText="確定"
              cancelText="取消"
            >
              <Tooltip title="移除關聯">
                <Button
                  type="link"
                  size="small"
                  danger
                  icon={<DisconnectOutlined />}
                  loading={unlinkPending}
                  style={{ fontSize: 12 }}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      )}
    </div>
  );
};

const UnassignedDocItem = React.memo(UnassignedDocItemInner);
UnassignedDocItem.displayName = 'UnassignedDocItem';

const UnassignedDocumentsListInner: React.FC<UnassignedDocumentsListProps> = ({
  unassignedDocs,
  hasCorrespondence,
  canEdit,
  unlinkPending,
  onDocClick,
  onQuickCreateRecord,
  onUnlinkDocument,
}) => {
  const { token } = theme.useToken();

  const hasUnassigned = unassignedDocs.incoming.length > 0 || unassignedDocs.outgoing.length > 0;

  if (!hasUnassigned) return null;

  return (
    <>
      {hasCorrespondence && (
        <Divider style={{ margin: '8px 0' }}>
          <Space size={4}>
            <ExclamationCircleOutlined style={{ color: token.colorWarning }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              未指派公文 ({unassignedDocs.incoming.length + unassignedDocs.outgoing.length})
            </Text>
          </Space>
        </Divider>
      )}
      <Row gutter={12}>
        {/* 未指派來文 */}
        <Col xs={24} md={12}>
          {unassignedDocs.incoming.length > 0 && (
            <div
              style={{
                borderRadius: 6,
                border: `1px dashed ${token.colorWarning}`,
                overflow: 'hidden',
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  padding: '4px 10px',
                  background: '#fffbe6',
                  borderBottom: `1px dashed ${token.colorWarning}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Text style={{ fontSize: 12, color: token.colorWarning }}>
                  <FileTextOutlined /> 待指派來文
                </Text>
                <Badge
                  count={unassignedDocs.incoming.length}
                  style={{ backgroundColor: token.colorWarning }}
                  size="small"
                />
              </div>
              {unassignedDocs.incoming.map((doc) => (
                <UnassignedDocItem
                  key={`unassigned-in-${doc.document_id}`}
                  doc={doc}
                  direction="incoming"
                  canEdit={canEdit}
                  unlinkPending={unlinkPending}
                  onDocClick={onDocClick}
                  onQuickCreateRecord={onQuickCreateRecord}
                  onUnlinkDocument={onUnlinkDocument}
                />
              ))}
            </div>
          )}
        </Col>

        {/* 未指派發文 */}
        <Col xs={24} md={12}>
          {unassignedDocs.outgoing.length > 0 && (
            <div
              style={{
                borderRadius: 6,
                border: `1px dashed ${token.colorWarning}`,
                overflow: 'hidden',
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  padding: '4px 10px',
                  background: '#fffbe6',
                  borderBottom: `1px dashed ${token.colorWarning}`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <Text style={{ fontSize: 12, color: token.colorWarning }}>
                  <SendOutlined /> 待指派發文
                </Text>
                <Badge
                  count={unassignedDocs.outgoing.length}
                  style={{ backgroundColor: token.colorWarning }}
                  size="small"
                />
              </div>
              {unassignedDocs.outgoing.map((doc) => (
                <UnassignedDocItem
                  key={`unassigned-out-${doc.document_id}`}
                  doc={doc}
                  direction="outgoing"
                  canEdit={canEdit}
                  unlinkPending={unlinkPending}
                  onDocClick={onDocClick}
                  onQuickCreateRecord={onQuickCreateRecord}
                  onUnlinkDocument={onUnlinkDocument}
                />
              ))}
            </div>
          )}
        </Col>
      </Row>
    </>
  );
};

export const UnassignedDocumentsList = React.memo(UnassignedDocumentsListInner);
UnassignedDocumentsList.displayName = 'UnassignedDocumentsList';
