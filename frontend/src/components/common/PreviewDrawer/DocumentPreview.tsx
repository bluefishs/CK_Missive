/**
 * 公文預覽內容元件
 *
 * 在 PreviewDrawer 中顯示公文摘要資訊：
 * - 基本資訊（文號、主旨、發受文單位）
 * - 承攬案件資訊
 * - 狀態與日期
 * - 附件/派工數量統計
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import {
  Descriptions,
  Tag,
  Space,
  Typography,
  Divider,
  Empty,
  Badge,
} from 'antd';
import {
  FileTextOutlined,
  CalendarOutlined,
  TeamOutlined,
  PaperClipOutlined,
  SendOutlined,
  EnvironmentOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import type { Document } from '../../../types';
import { useResponsive } from '../../../hooks';

const { Text, Paragraph } = Typography;

// ============================================================================
// 型別定義
// ============================================================================

export interface DocumentPreviewProps {
  /** 公文資料 */
  document: Document | null;
  /** 附件數量 */
  attachmentCount?: number;
  /** 派工數量 */
  dispatchCount?: number;
  /** 工程關聯數量 */
  projectLinkCount?: number;
  /** 是否顯示完整說明 */
  showFullContent?: boolean;
}

// ============================================================================
// 輔助函數
// ============================================================================

/** 取得狀態標籤顏色 */
const getStatusColor = (status?: string): string => {
  const statusColors: Record<string, string> = {
    '待處理': 'orange',
    '處理中': 'processing',
    '已辦畢': 'success',
    '已結案': 'default',
    '已歸檔': 'default',
  };
  return statusColors[status || ''] || 'default';
};

/** 取得公文類型標籤顏色 */
const getDocTypeColor = (docType?: string): string => {
  if (docType === '收文') return 'blue';
  if (docType === '發文') return 'green';
  return 'default';
};

// ============================================================================
// 主元件
// ============================================================================

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  document,
  attachmentCount = 0,
  dispatchCount = 0,
  projectLinkCount = 0,
  showFullContent = false,
}) => {
  const { isMobile } = useResponsive();

  if (!document) {
    return (
      <Empty
        description="無公文資料"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  const isReceiveDoc = document.doc_type === '收文' || document.category === '收文';

  return (
    <div>
      {/* 標籤區 */}
      <Space wrap style={{ marginBottom: 16 }}>
        <Tag color={getDocTypeColor(document.doc_type || document.category)}>
          {document.doc_type || document.category || '公文'}
        </Tag>
        {document.status && (
          <Tag color={getStatusColor(document.status)}>
            {document.status}
          </Tag>
        )}
        {document.delivery_method && (
          <Tag>{document.delivery_method}</Tag>
        )}
      </Space>

      {/* 基本資訊 */}
      <Descriptions
        column={1}
        size="small"
        styles={{
          label: {
            width: isMobile ? 70 : 90,
            color: '#666',
            fontWeight: 500,
          },
          content: {
            color: '#333',
          },
        }}
      >
        <Descriptions.Item label="文號">
          <Text strong copyable={{ text: document.doc_number || '' }}>
            {document.doc_number || '-'}
          </Text>
        </Descriptions.Item>

        {document.auto_serial && (
          <Descriptions.Item label="流水號">
            <Tag color="purple">{document.auto_serial}</Tag>
          </Descriptions.Item>
        )}

        <Descriptions.Item label="主旨">
          <Paragraph
            ellipsis={showFullContent ? false : { rows: 2, expandable: true }}
            style={{ margin: 0 }}
          >
            {document.subject || document.title || '-'}
          </Paragraph>
        </Descriptions.Item>

        <Descriptions.Item label={isReceiveDoc ? '發文單位' : '受文單位'}>
          {isReceiveDoc ? document.sender : document.receiver || '-'}
        </Descriptions.Item>

        {isReceiveDoc ? (
          <Descriptions.Item label="受文者">
            {document.receiver || '-'}
          </Descriptions.Item>
        ) : (
          <Descriptions.Item label="發文單位">
            {document.sender || '-'}
          </Descriptions.Item>
        )}
      </Descriptions>

      <Divider style={{ margin: '12px 0' }} />

      {/* 日期與承攬案件 */}
      <Descriptions
        column={isMobile ? 1 : 2}
        size="small"
        styles={{
          label: {
            width: isMobile ? 70 : 80,
            color: '#666',
          },
        }}
      >
        <Descriptions.Item
          label={<><CalendarOutlined /> {isReceiveDoc ? '收文日' : '發文日'}</>}
        >
          {isReceiveDoc
            ? (document.receive_date ? dayjs(document.receive_date).format('YYYY/MM/DD') : '-')
            : (document.doc_date ? dayjs(document.doc_date).format('YYYY/MM/DD') : '-')
          }
        </Descriptions.Item>

        {document.send_date && (
          <Descriptions.Item label={<><ClockCircleOutlined /> 發送日</>}>
            {dayjs(document.send_date).format('YYYY/MM/DD')}
          </Descriptions.Item>
        )}
      </Descriptions>

      {/* 承攬案件 */}
      {document.contract_project_name && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div style={{ marginBottom: 8 }}>
            <Text type="secondary" style={{ fontSize: 12 }}>
              <TeamOutlined style={{ marginRight: 4 }} />
              承攬案件
            </Text>
          </div>
          <Tag color="geekblue" style={{ whiteSpace: 'normal', height: 'auto', lineHeight: 1.5, padding: '4px 8px' }}>
            {document.contract_project_name}
          </Tag>
        </>
      )}

      {/* 承辦人 */}
      {document.assignee && (
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            <TeamOutlined style={{ marginRight: 4 }} />
            業務同仁
          </Text>
          <div style={{ marginTop: 4 }}>
            {document.assignee.split(',').map((name, index) => (
              <Tag key={index} style={{ marginBottom: 4 }}>{name.trim()}</Tag>
            ))}
          </div>
        </div>
      )}

      {/* 備註 */}
      {(document.notes || document.ck_note) && (
        <>
          <Divider style={{ margin: '12px 0' }} />
          <div>
            <Text type="secondary" style={{ fontSize: 12 }}>備註</Text>
            <Paragraph
              type="secondary"
              ellipsis={showFullContent ? false : { rows: 2, expandable: true }}
              style={{ margin: '4px 0 0 0', fontSize: 13 }}
            >
              {document.ck_note || document.notes}
            </Paragraph>
          </div>
        </>
      )}

      {/* 統計資訊 */}
      <Divider style={{ margin: '12px 0' }} />
      <Space size={16} wrap>
        <Badge count={attachmentCount} showZero overflowCount={99}>
          <Tag icon={<PaperClipOutlined />}>附件</Tag>
        </Badge>
        {dispatchCount > 0 && (
          <Badge count={dispatchCount} overflowCount={99}>
            <Tag icon={<SendOutlined />} color="blue">派工</Tag>
          </Badge>
        )}
        {projectLinkCount > 0 && (
          <Badge count={projectLinkCount} overflowCount={99}>
            <Tag icon={<EnvironmentOutlined />} color="green">工程</Tag>
          </Badge>
        )}
      </Space>
    </div>
  );
};

export default DocumentPreview;
