/**
 * 派工單公文關聯 Tab
 *
 * 用於管理派工單與公文的關聯關係，支援：
 * - 搜尋並新增公文關聯
 * - 自動判斷關聯類型（機關來函/乾坤發文）
 * - 顯示已關聯公文列表
 * - 解除公文關聯
 *
 * @version 1.0.0
 * @date 2026-01-26
 */

import React from 'react';
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Space,
  Tag,
  Spin,
  Empty,
  Descriptions,
  List,
  Popconfirm,
  Radio,
  Typography,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

import type { DispatchDocumentsTabProps } from './types';
import type { OfficialDocument, DispatchDocumentLink, LinkType } from '../../../types/api';
import { isReceiveDocument } from '../../../types/api';

const { Option } = Select;
const { Text } = Typography;

/**
 * 根據公文字號自動判斷關聯類型
 * - 以「乾坤」開頭的公文 -> 乾坤發文 (company_outgoing)
 * - 其他 -> 機關來函 (agency_incoming)
 */
const detectLinkType = (docNumber?: string): LinkType => {
  if (!docNumber) return 'agency_incoming';
  // 「乾坤」開頭表示公司發文
  if (docNumber.startsWith('乾坤')) {
    return 'company_outgoing';
  }
  // 其他都是機關來函
  return 'agency_incoming';
};

/**
 * 派工單公文關聯 Tab 元件
 */
export const DispatchDocumentsTab: React.FC<DispatchDocumentsTabProps> = ({
  dispatch,
  canEdit,
  isLoading,
  docSearchKeyword,
  setDocSearchKeyword,
  availableDocs,
  searchingDocs,
  selectedDocId,
  setSelectedDocId,
  selectedLinkType,
  setSelectedLinkType,
  onLinkDocument,
  linkDocMutationPending,
  onUnlinkDocument,
  unlinkDocMutationPending,
  refetch,
  navigate,
}) => {
  // 按公文日期排序（最新的排前面）
  const documents = [...(dispatch?.linked_documents || [])].sort((a, b) => {
    if (!a.doc_date && !b.doc_date) return 0;
    if (!a.doc_date) return 1;
    if (!b.doc_date) return -1;
    return new Date(b.doc_date).getTime() - new Date(a.doc_date).getTime();
  });

  /** 處理公文選取變更 */
  const handleDocumentChange = (docId: number | undefined) => {
    setSelectedDocId(docId);
    // 自動判斷關聯類型
    if (docId) {
      const selectedDoc = availableDocs.find((d: OfficialDocument) => d.id === docId);
      if (selectedDoc?.doc_number) {
        setSelectedLinkType(detectLinkType(selectedDoc.doc_number));
      }
    }
  };

  return (
    <Spin spinning={isLoading}>
      {/* 新增關聯區塊 */}
      {canEdit && (
        <Card size="small" style={{ marginBottom: 16 }} title="新增公文關聯">
          <Row gutter={[12, 12]} align="middle">
            <Col span={10}>
              <Select
                showSearch
                allowClear
                placeholder="搜尋公文字號或主旨..."
                style={{ width: '100%' }}
                value={selectedDocId}
                onChange={handleDocumentChange}
                onSearch={setDocSearchKeyword}
                filterOption={false}
                notFoundContent={
                  docSearchKeyword ? (
                    <Empty description="無符合的公文" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : (
                    <Typography.Text type="secondary">請輸入關鍵字搜尋</Typography.Text>
                  )
                }
                loading={searchingDocs}
              >
                {availableDocs.map((doc: OfficialDocument) => (
                  <Option key={doc.id} value={doc.id}>
                    <Space>
                      <Tag color={isReceiveDocument(doc.category) ? 'blue' : 'green'}>
                        {doc.doc_number || `#${doc.id}`}
                      </Tag>
                      <Text ellipsis style={{ maxWidth: 200 }}>
                        {doc.subject || '(無主旨)'}
                      </Text>
                    </Space>
                  </Option>
                ))}
              </Select>
            </Col>
            <Col span={8}>
              <Radio.Group
                value={selectedLinkType}
                onChange={(e) => setSelectedLinkType(e.target.value)}
              >
                <Radio.Button value="agency_incoming">機關來函</Radio.Button>
                <Radio.Button value="company_outgoing">乾坤發文</Radio.Button>
              </Radio.Group>
            </Col>
            <Col span={6}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={onLinkDocument}
                loading={linkDocMutationPending}
                disabled={!selectedDocId}
              >
                建立關聯
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 已關聯公文列表 */}
      {documents.length > 0 ? (
        <List
          dataSource={documents}
          renderItem={(doc: DispatchDocumentLink) => {
            // 使用 detectLinkType 根據公文字號校正關聯類型顯示
            // 解決資料庫中可能存在的錯誤 link_type 值
            const correctedLinkType = detectLinkType(doc.doc_number);
            const isAgencyIncoming = correctedLinkType === 'agency_incoming';

            return (
              <Card size="small" style={{ marginBottom: 12 }}>
                <Descriptions size="small" column={2}>
                  <Descriptions.Item label="公文字號">
                    <Space>
                      {doc.doc_date && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {dayjs(doc.doc_date).format('YYYY-MM-DD')}
                        </Text>
                      )}
                      <Tag color={isAgencyIncoming ? 'blue' : 'green'}>
                        {doc.doc_number || `#${doc.document_id}`}
                      </Tag>
                    </Space>
                  </Descriptions.Item>
                  <Descriptions.Item label="關聯類型">
                    <Tag color={isAgencyIncoming ? 'blue' : 'green'}>
                      {isAgencyIncoming ? '機關來函' : '乾坤發文'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="主旨" span={2}>
                    {doc.subject || '-'}
                  </Descriptions.Item>
                </Descriptions>
                <Space>
                  <Button
                    type="link"
                    size="small"
                    onClick={() => navigate(`/documents/${doc.document_id}`)}
                  >
                    查看公文
                  </Button>
                  {canEdit && doc.link_id !== undefined && (
                    <Popconfirm
                      title="確定要移除此關聯嗎？"
                      onConfirm={() => {
                        if (doc.link_id === undefined || doc.link_id === null) {
                          console.error('[unlinkDoc] link_id 缺失:', doc);
                          refetch();
                          return;
                        }
                        onUnlinkDocument(doc.link_id);
                      }}
                      okText="確定"
                      cancelText="取消"
                    >
                      <Button
                        type="link"
                        size="small"
                        danger
                        loading={unlinkDocMutationPending}
                      >
                        移除關聯
                      </Button>
                    </Popconfirm>
                  )}
                </Space>
              </Card>
            );
          }}
        />
      ) : (
        <Empty description="此派工單尚無關聯公文" image={Empty.PRESENTED_IMAGE_SIMPLE}>
          {!canEdit && (
            <Button type="link" onClick={() => navigate('/taoyuan/dispatch')}>
              返回派工列表
            </Button>
          )}
        </Empty>
      )}
    </Spin>
  );
};

export default DispatchDocumentsTab;
