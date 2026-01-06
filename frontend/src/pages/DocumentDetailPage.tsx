import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Spin, Button, Space, Typography, Descriptions, Tag, App, Empty, Divider, List, Row, Col } from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  CopyOutlined,
  CalendarOutlined,
  FileTextOutlined,
  PaperClipOutlined,
  DownloadOutlined,
  EyeOutlined,
  FilePdfOutlined,
  FileImageOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { documentsApi } from '../api/documentsApi';
import { filesApi } from '../api/filesApi';
import { Document } from '../types';
import { DocumentOperations } from '../components/document/DocumentOperations';
import { calendarIntegrationService } from '../services/calendarIntegrationService';

const { Title, Text } = Typography;

export const DocumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();

  const [loading, setLoading] = useState(true);
  const [document, setDocument] = useState<Document | null>(null);
  const [attachments, setAttachments] = useState<any[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);

  // 編輯/複製模態框狀態
  const [operationModal, setOperationModal] = useState<{
    visible: boolean;
    type: 'view' | 'edit' | 'copy' | null;
  }>({ visible: false, type: null });

  // 載入公文資料
  useEffect(() => {
    const loadDocument = async () => {
      if (!id) return;

      setLoading(true);
      try {
        const docId = parseInt(id, 10);
        const doc = await documentsApi.getDocument(docId);
        setDocument(doc);

        // 載入附件
        setAttachmentsLoading(true);
        try {
          const atts = await filesApi.getDocumentAttachments(docId);
          setAttachments(atts);
        } catch (error) {
          console.error('載入附件失敗:', error);
          setAttachments([]);
        } finally {
          setAttachmentsLoading(false);
        }
      } catch (error) {
        console.error('載入公文失敗:', error);
        message.error('載入公文失敗');
        setDocument(null);
      } finally {
        setLoading(false);
      }
    };

    loadDocument();
  }, [id, message]);

  // 加入行事曆
  const handleAddToCalendar = async () => {
    if (!document) return;

    try {
      setCalendarLoading(true);
      await calendarIntegrationService.addDocumentToCalendar(document);
    } catch (error) {
      console.error('加入行事曆失敗:', error);
    } finally {
      setCalendarLoading(false);
    }
  };

  // 下載附件
  const handleDownload = async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename);
    } catch (error) {
      console.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  };

  // 預覽附件
  const handlePreview = async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      console.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  };

  // 判斷是否可預覽
  const isPreviewable = (contentType?: string, filename?: string): boolean => {
    if (contentType) {
      if (contentType.startsWith('image/') ||
          contentType === 'application/pdf' ||
          contentType.startsWith('text/')) {
        return true;
      }
    }
    if (filename) {
      const ext = filename.toLowerCase().split('.').pop();
      return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'txt', 'csv'].includes(ext || '');
    }
    return false;
  };

  // 取得檔案圖示
  const getFileIcon = (contentType?: string, filename?: string) => {
    const ext = filename?.toLowerCase().split('.').pop();
    if (contentType?.startsWith('image/') || ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '')) {
      return <FileImageOutlined style={{ fontSize: 20, color: '#52c41a' }} />;
    }
    if (contentType === 'application/pdf' || ext === 'pdf') {
      return <FilePdfOutlined style={{ fontSize: 20, color: '#ff4d4f' }} />;
    }
    return <PaperClipOutlined style={{ fontSize: 20, color: '#1890ff' }} />;
  };

  // 取得狀態標籤顏色
  const getStatusColor = (status?: string) => {
    switch (status) {
      case '收文完成': return 'processing';
      case '使用者確認': return 'success';
      case '收文異常': return 'error';
      default: return 'default';
    }
  };

  // 儲存公文（編輯/複製後）
  const handleSaveDocument = async (docData: Partial<Document>): Promise<Document | void> => {
    if (!document) return;

    try {
      if (operationModal.type === 'edit') {
        await documentsApi.updateDocument(document.id, docData);
        message.success('公文更新成功');
        // 重新載入資料
        const updated = await documentsApi.getDocument(document.id);
        setDocument(updated);
      } else if (operationModal.type === 'copy') {
        const newDoc = await documentsApi.createDocument(docData);
        message.success('公文複製成功');
        return newDoc;
      }
    } catch (error) {
      console.error('儲存公文失敗:', error);
      message.error('儲存失敗');
      throw error;
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" tip="載入中..." />
      </div>
    );
  }

  if (!document) {
    return (
      <Card>
        <Empty
          description="找不到此公文"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" onClick={() => navigate('/documents')}>
            返回公文列表
          </Button>
        </Empty>
      </Card>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 頁面標題 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate(-1)}
            >
              返回
            </Button>
            <div>
              <Title level={4} style={{ margin: 0 }}>
                <FileTextOutlined style={{ marginRight: 8 }} />
                {document.subject}
              </Title>
              <div style={{ marginTop: 8 }}>
                <Tag color="blue">{document.doc_type || '函'}</Tag>
                <Tag color={getStatusColor(document.status)}>{document.status || '未設定'}</Tag>
                {document.priority && (
                  <Tag color={document.priority <= 2 ? 'red' : 'default'}>
                    優先級 {document.priority}
                  </Tag>
                )}
              </div>
            </div>
          </div>
          <Space>
            <Button
              icon={<CalendarOutlined />}
              loading={calendarLoading}
              onClick={handleAddToCalendar}
            >
              加入行事曆
            </Button>
            <Button
              icon={<CopyOutlined />}
              onClick={() => setOperationModal({ visible: true, type: 'copy' })}
            >
              複製
            </Button>
            <Button
              type="primary"
              icon={<EditOutlined />}
              onClick={() => setOperationModal({ visible: true, type: 'edit' })}
            >
              編輯
            </Button>
          </Space>
        </div>
      </Card>

      <Row gutter={16}>
        {/* 左側：公文資訊 */}
        <Col span={16}>
          <Card title="公文資訊" style={{ marginBottom: 16 }}>
            <Descriptions column={2} bordered size="small">
              <Descriptions.Item label="公文字號" span={2}>
                <Text strong copyable>{document.doc_number}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="發文機關">
                {document.sender || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="受文者">
                {document.receiver || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="發文日期">
                {document.doc_date ? dayjs(document.doc_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="收文日期">
                {document.receive_date ? dayjs(document.receive_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="發送日期">
                {document.send_date ? dayjs(document.send_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="業務同仁">
                {(document as any).assignee || '-'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* 說明內容 */}
          {document.content && (
            <Card title="說明" style={{ marginBottom: 16 }}>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
                {document.content}
              </div>
            </Card>
          )}

          {/* 備註 */}
          {(document as any).notes && (
            <Card title="備註" style={{ marginBottom: 16 }}>
              <div style={{ whiteSpace: 'pre-wrap' }}>
                {(document as any).notes}
              </div>
            </Card>
          )}
        </Col>

        {/* 右側：附件與系統資訊 */}
        <Col span={8}>
          {/* 附件列表 */}
          <Card
            title={
              <Space>
                <PaperClipOutlined />
                <span>附件</span>
                <Tag color="blue">{attachments.length}</Tag>
              </Space>
            }
            style={{ marginBottom: 16 }}
            loading={attachmentsLoading}
          >
            {attachments.length > 0 ? (
              <List
                size="small"
                dataSource={attachments}
                renderItem={(item: any) => (
                  <List.Item
                    actions={[
                      isPreviewable(item.content_type, item.original_filename || item.filename) && (
                        <Button
                          key="preview"
                          type="link"
                          size="small"
                          icon={<EyeOutlined />}
                          onClick={() => handlePreview(item.id, item.original_filename || item.filename)}
                        >
                          預覽
                        </Button>
                      ),
                      <Button
                        key="download"
                        type="link"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => handleDownload(item.id, item.original_filename || item.filename)}
                      >
                        下載
                      </Button>,
                    ].filter(Boolean)}
                  >
                    <List.Item.Meta
                      avatar={getFileIcon(item.content_type, item.original_filename || item.filename)}
                      title={item.original_filename || item.filename}
                      description={
                        <span style={{ fontSize: 12, color: '#999' }}>
                          {item.file_size ? `${(item.file_size / 1024).toFixed(1)} KB` : ''}
                        </span>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="尚無附件" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          {/* 系統資訊 */}
          <Card title="系統資訊" size="small">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="建立時間">
                {document.created_at ? dayjs(document.created_at).format('YYYY-MM-DD HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="更新時間">
                {document.updated_at ? dayjs(document.updated_at).format('YYYY-MM-DD HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="建立者">
                {(document as any).creator || '系統'}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>

      {/* 編輯/複製模態框 */}
      <DocumentOperations
        document={document}
        operation={operationModal.type}
        visible={operationModal.visible}
        onClose={() => setOperationModal({ visible: false, type: null })}
        onSave={handleSaveDocument}
      />
    </div>
  );
};

export default DocumentDetailPage;
