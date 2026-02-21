/**
 * 公文卡片元件 - 手機版列表專用
 *
 * 以卡片形式呈現公文重點資訊，適合手機瀏覽
 *
 * @version 1.0.0
 * @date 2026-01-12
 */

import React from 'react';
import { Card, Tag, Space, Typography } from 'antd';
import {
  FileTextOutlined,
  CalendarOutlined,
  BankOutlined,
  PaperClipOutlined,
  FolderOutlined,
} from '@ant-design/icons';
import { Document } from '../../types';
import './DocumentCard.css';

const { Text, Paragraph } = Typography;

interface DocumentCardProps {
  document: Document;
  onClick?: (document: Document) => void;
}

/** 格式化日期 */
const formatDate = (dateString: string | null | undefined): string => {
  if (!dateString) return '-';
  try {
    return new Date(dateString).toLocaleDateString('zh-TW');
  } catch {
    return dateString;
  }
};

/** 取得類別標籤顏色 */
const getCategoryColor = (category: string | undefined): string => {
  switch (category) {
    case '收文': return 'blue';
    case '發文': return 'green';
    default: return 'default';
  }
};

/** 取得狀態標籤顏色 */
const getStatusColor = (status: string | undefined): string => {
  const statusColors: Record<string, string> = {
    '收文完成': 'success',
    '使用者確認': 'processing',
    '收文異常': 'error',
    '待處理': 'warning',
    '已辦畢': 'success',
    '處理中': 'processing',
  };
  return statusColors[status || ''] || 'default';
};

const DocumentCardInner: React.FC<DocumentCardProps> = ({
  document,
  onClick,
}) => {
  const handleClick = () => {
    onClick?.(document);
  };

  return (
    <Card
      className="document-card"
      hoverable
      onClick={handleClick}
      size="small"
    >
      {/* 標題區：主旨 */}
      <Paragraph
        className="document-card-title"
        ellipsis={{ rows: 2 }}
        style={{ marginBottom: 8, fontWeight: 500 }}
      >
        {document.subject || '(無主旨)'}
      </Paragraph>

      {/* 標籤區 */}
      <Space size={4} wrap style={{ marginBottom: 8 }}>
        {document.category && (
          <Tag color={getCategoryColor(document.category)}>
            {document.category}
          </Tag>
        )}
        {document.doc_type && (
          <Tag>{document.doc_type}</Tag>
        )}
        {document.status && (
          <Tag color={getStatusColor(document.status)}>
            {document.status}
          </Tag>
        )}
      </Space>

      {/* 資訊列表 */}
      <div className="document-card-info">
        {/* 公文字號 */}
        <div className="info-row">
          <FileTextOutlined className="info-icon" />
          <Text className="info-label">字號：</Text>
          <Text className="info-value" copyable={{ tooltips: false }}>
            {document.doc_number || '-'}
          </Text>
        </div>

        {/* 發文機關 */}
        {document.sender && (
          <div className="info-row">
            <BankOutlined className="info-icon" />
            <Text className="info-label">發文：</Text>
            <Text className="info-value" ellipsis>
              {document.sender}
            </Text>
          </div>
        )}

        {/* 公文日期 */}
        <div className="info-row">
          <CalendarOutlined className="info-icon" />
          <Text className="info-label">日期：</Text>
          <Text className="info-value">
            {formatDate(document.doc_date)}
          </Text>
        </div>

        {/* 承攬案件 */}
        {document.contract_case && (
          <div className="info-row">
            <FolderOutlined className="info-icon" />
            <Text className="info-label">案件：</Text>
            <Text className="info-value" ellipsis type="secondary">
              {document.contract_case}
            </Text>
          </div>
        )}

        {/* 附件數量 */}
        {(document.attachment_count ?? 0) > 0 && (
          <div className="info-row">
            <PaperClipOutlined className="info-icon" />
            <Text className="info-label">附件：</Text>
            <Tag color="cyan" style={{ margin: 0 }}>
              {document.attachment_count} 個
            </Tag>
          </div>
        )}
      </div>
    </Card>
  );
};

export const DocumentCard = React.memo(DocumentCardInner);

export default DocumentCard;
