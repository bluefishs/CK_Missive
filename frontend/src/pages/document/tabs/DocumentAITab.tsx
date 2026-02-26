/**
 * DocumentAITab - 公文 AI 分析 Tab
 *
 * 整合三項 AI 功能於公文詳情頁：
 * - AI 摘要生成（AISummaryPanel，SSE 串流）
 * - 語意相似公文推薦（getSemanticSimilar）
 * - 單篇實體提取（extractEntities）
 *
 * @version 1.0.0
 * @created 2026-02-26
 */

import React, { useState, useCallback } from 'react';
import {
  Button, Divider, Typography, Space, Tag, Spin, Empty, App, Descriptions,
} from 'antd';
import {
  FileSearchOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { Document } from '../../../types';
import type { SemanticSimilarItem, EntityExtractResponse } from '../../../types/ai';
import { aiApi } from '../../../api/aiApi';
import { AISummaryPanel } from '../../../components/ai/AISummaryPanel';

const { Text } = Typography;

export interface DocumentAITabProps {
  document: Document | null;
}

export const DocumentAITab: React.FC<DocumentAITabProps> = ({ document }) => {
  const { message } = App.useApp();
  const navigate = useNavigate();

  // 語意相似
  const [similarDocs, setSimilarDocs] = useState<SemanticSimilarItem[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarSearched, setSimilarSearched] = useState(false);

  // 實體提取
  const [extractResult, setExtractResult] = useState<EntityExtractResponse | null>(null);
  const [extractLoading, setExtractLoading] = useState(false);

  const handleLoadSimilar = useCallback(async () => {
    if (!document?.id) return;
    setSimilarLoading(true);
    try {
      const resp = await aiApi.getSemanticSimilar({ document_id: document.id, limit: 8 });
      setSimilarDocs(resp?.similar_documents || []);
      setSimilarSearched(true);
    } catch {
      message.error('語意相似查詢失敗');
    } finally {
      setSimilarLoading(false);
    }
  }, [document?.id, message]);

  const handleExtract = useCallback(async () => {
    if (!document?.id) return;
    setExtractLoading(true);
    try {
      const resp = await aiApi.extractEntities({ document_id: document.id });
      setExtractResult(resp);
      if (resp?.skipped) {
        message.info('此公文已提取過實體，無需重複處理');
      } else if (resp?.success) {
        message.success(`提取完成：${resp.entities_count ?? 0} 個實體、${resp.relations_count ?? 0} 條關係`);
      }
    } catch {
      message.error('實體提取失敗');
    } finally {
      setExtractLoading(false);
    }
  }, [document?.id, message]);

  if (!document) {
    return <Empty description="公文資料載入中..." />;
  }

  return (
    <div style={{ maxWidth: 720 }}>
      {/* AI 摘要 */}
      <Divider orientation="left" style={{ fontSize: 13, marginTop: 0 }}>
        <RobotOutlined /> AI 摘要
      </Divider>
      <AISummaryPanel
        subject={document.subject}
        content={document.content}
        sender={document.sender}
        showCard={false}
      />

      {/* 語意相似公文 */}
      <Divider orientation="left" style={{ fontSize: 13 }}>
        <FileSearchOutlined /> 語意相似公文
      </Divider>
      {!similarSearched ? (
        <Button
          icon={<FileSearchOutlined />}
          onClick={handleLoadSimilar}
          loading={similarLoading}
          size="small"
        >
          查詢相似公文
        </Button>
      ) : similarLoading ? (
        <Spin size="small" />
      ) : similarDocs.length === 0 ? (
        <Text type="secondary" style={{ fontSize: 12 }}>
          無相似公文（可能 Embedding 未建立或無相似結果）
        </Text>
      ) : (
        <div>
          {similarDocs.map((doc) => (
            <div
              key={doc.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate(`/documents/${doc.id}`)}
              onKeyDown={(e) => { if (e.key === 'Enter') navigate(`/documents/${doc.id}`); }}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '6px 8px', borderRadius: 6, cursor: 'pointer',
                border: '1px solid #f0f0f0', marginBottom: 4,
                transition: 'background 0.15s',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = '#f0f5ff'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = ''; }}
            >
              <Tag color="blue" style={{ fontSize: 11, margin: 0, flexShrink: 0 }}>
                {Math.round(doc.similarity * 100)}%
              </Tag>
              <Text strong style={{ fontSize: 12, flexShrink: 0, maxWidth: 120 }} ellipsis>
                {doc.doc_number || '-'}
              </Text>
              <Text style={{ fontSize: 12, flex: 1, color: '#555' }} ellipsis>
                {doc.subject || '(無主旨)'}
              </Text>
              {doc.doc_date && (
                <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
                  {doc.doc_date}
                </Text>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 實體提取 */}
      <Divider orientation="left" style={{ fontSize: 13 }}>
        <ExperimentOutlined /> NER 實體提取
      </Divider>
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Button
          icon={<ExperimentOutlined />}
          onClick={handleExtract}
          loading={extractLoading}
          size="small"
          disabled={!!extractResult}
        >
          {extractResult ? '已提取' : '提取實體與關係'}
        </Button>
        {extractResult && (
          <Descriptions size="small" bordered column={2} style={{ maxWidth: 400 }}>
            <Descriptions.Item label="狀態">
              {extractResult.skipped ? (
                <Tag color="default">已跳過</Tag>
              ) : (
                <Tag icon={<CheckCircleOutlined />} color="success">完成</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="實體數">
              {extractResult.entities_count ?? 0}
            </Descriptions.Item>
            <Descriptions.Item label="關係數">
              {extractResult.relations_count ?? 0}
            </Descriptions.Item>
            {extractResult.reason && (
              <Descriptions.Item label="訊息" span={2}>
                <Text type="secondary" style={{ fontSize: 12 }}>{extractResult.reason}</Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Space>
    </div>
  );
};

export default DocumentAITab;
