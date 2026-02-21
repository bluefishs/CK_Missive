/**
 * InlineDocumentSearch - 行內公文搜尋與關聯
 *
 * 在 Tab 內直接搜尋公文並建立關聯：
 * - Select + showSearch 搜尋公文字號/主旨
 * - Radio 切換關聯類型（機關來函 / 乾坤發文）
 * - 建立關聯按鈕
 *
 * @version 1.0.0
 * @date 2026-02-21
 */

import React from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  Radio,
  Button,
  Space,
  Empty,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { isReceiveDocument } from '../../../../types/api';
import type { LinkType } from '../../../../types/api';

const { Text } = Typography;
const { Option } = Select;

/** 可關聯公文選項 */
interface LinkableDocumentOption {
  id: number;
  doc_number: string | null;
  subject: string | null;
  doc_date: string | null;
  category: string | null;
  sender: string | null;
  receiver: string | null;
}

export interface InlineDocumentSearchProps {
  /** 搜尋到的可關聯公文列表 */
  availableDocs: LinkableDocumentOption[];
  /** 選中的公文 ID */
  selectedDocId: number | undefined;
  /** 選中的關聯類型 */
  selectedLinkType: LinkType;
  /** 搜尋關鍵字 */
  docSearchKeyword: string;
  /** 是否正在搜尋 */
  searchingDocs: boolean;
  /** 是否正在建立關聯 */
  linkingDoc: boolean;
  /** 公文選取變更回調 */
  onDocumentChange: (docId: number | undefined) => void;
  /** 搜尋關鍵字變更回調 */
  onSearchKeywordChange: (keyword: string) => void;
  /** 關聯類型變更回調 */
  onLinkTypeChange: (linkType: LinkType) => void;
  /** 建立關聯回調 */
  onLinkDocument: () => void;
}

const InlineDocumentSearchInner: React.FC<InlineDocumentSearchProps> = ({
  availableDocs,
  selectedDocId,
  selectedLinkType,
  docSearchKeyword,
  searchingDocs,
  linkingDoc,
  onDocumentChange,
  onSearchKeywordChange,
  onLinkTypeChange,
  onLinkDocument,
}) => {
  return (
    <Card
      size="small"
      style={{ marginTop: 12 }}
      styles={{
        header: { minHeight: 36, padding: '0 12px' },
        body: { padding: '8px 12px' },
      }}
      title={
        <Space size={4}>
          <SearchOutlined />
          <Text style={{ fontSize: 13 }}>新增公文關聯</Text>
        </Space>
      }
    >
      <Row gutter={[8, 8]} align="middle">
        <Col xs={24} sm={24} md={12} lg={12}>
          <Select
            showSearch
            allowClear
            placeholder="搜尋公文字號或主旨..."
            style={{ width: '100%' }}
            value={selectedDocId}
            onChange={onDocumentChange}
            onSearch={onSearchKeywordChange}
            filterOption={false}
            popupMatchSelectWidth={false}
            styles={{ popup: { root: { minWidth: 500, maxWidth: 700 } } }}
            notFoundContent={
              docSearchKeyword ? (
                <Empty description="無符合的公文" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : (
                <Text type="secondary">請輸入關鍵字搜尋</Text>
              )
            }
            loading={searchingDocs}
            optionLabelProp="label"
            size="small"
          >
            {availableDocs.map((doc) => {
              const docNumber = doc.doc_number || `#${doc.id}`;
              const subject = doc.subject || '(無主旨)';
              const docIsReceive = isReceiveDocument(doc.category);
              const dateStr = doc.doc_date ? doc.doc_date.substring(0, 10) : '';
              const tooltipContent = (
                <div style={{ maxWidth: 400 }}>
                  <div><strong>字號：</strong>{docNumber}</div>
                  <div><strong>主旨：</strong>{subject}</div>
                  {dateStr && <div><strong>日期：</strong>{dateStr}</div>}
                  {doc.sender && <div><strong>發文：</strong>{doc.sender}</div>}
                  {doc.receiver && <div><strong>受文：</strong>{doc.receiver}</div>}
                </div>
              );

              return (
                <Option key={doc.id} value={doc.id} label={docNumber}>
                  <Tooltip title={tooltipContent} placement="right" mouseEnterDelay={0.5}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Tag
                        color={docIsReceive ? 'blue' : 'green'}
                        style={{ flexShrink: 0, margin: 0 }}
                      >
                        {docIsReceive ? '收' : '發'}
                      </Tag>
                      <Text strong style={{ flexShrink: 0, minWidth: 140 }}>
                        {docNumber}
                      </Text>
                      <Text
                        type="secondary"
                        ellipsis
                        style={{ flex: 1, maxWidth: 250 }}
                      >
                        {subject}
                      </Text>
                    </div>
                  </Tooltip>
                </Option>
              );
            })}
          </Select>
        </Col>
        <Col xs={16} sm={14} md={7} lg={7}>
          <Radio.Group
            value={selectedLinkType}
            onChange={(e) => onLinkTypeChange(e.target.value)}
            size="small"
          >
            <Radio.Button value="agency_incoming">機關來函</Radio.Button>
            <Radio.Button value="company_outgoing">乾坤發文</Radio.Button>
          </Radio.Group>
        </Col>
        <Col xs={8} sm={10} md={5} lg={5}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={onLinkDocument}
            loading={linkingDoc}
            disabled={!selectedDocId}
            size="small"
          >
            建立關聯
          </Button>
        </Col>
      </Row>
    </Card>
  );
};

export const InlineDocumentSearch = React.memo(InlineDocumentSearchInner);
InlineDocumentSearch.displayName = 'InlineDocumentSearch';
