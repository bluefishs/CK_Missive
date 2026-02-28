/**
 * DocumentAITab - 公文 AI 分析 Tab
 *
 * 整合持久化 AI 分析結果（摘要/分類/關鍵字）+ 語意相似 + NER。
 * 分析結果存入 document_ai_analyses 資料表，可復用、免重複呼叫 LLM。
 *
 * @version 2.0.0
 * @created 2026-02-26
 * @updated 2026-02-28 - 持久化重構，改用 Collapse 面板
 */

import React, { useState, useCallback } from 'react';
import {
  Button, Collapse, Typography, Space, Tag, Spin, Empty, App,
  Descriptions, Progress, Tooltip, Badge,
} from 'antd';
import {
  FileSearchOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  RobotOutlined,
  TagsOutlined,
  FolderOutlined,
  ReloadOutlined,
  WarningOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { Document } from '../../../types';
import type { SemanticSimilarItem, EntityExtractResponse } from '../../../types/ai';
import { aiApi } from '../../../api/aiApi';
import { useDocumentAnalysis, useTriggerAnalysis } from '../../../hooks';

const { Text, Paragraph } = Typography;

export interface DocumentAITabProps {
  document: Document | null;
}

export const DocumentAITab: React.FC<DocumentAITabProps> = ({ document }) => {
  const { message } = App.useApp();
  const navigate = useNavigate();

  // 持久化分析
  const {
    data: analysis,
    isLoading: analysisLoading,
  } = useDocumentAnalysis(document?.id);
  const triggerMutation = useTriggerAnalysis();

  // 語意相似
  const [similarDocs, setSimilarDocs] = useState<SemanticSimilarItem[]>([]);
  const [similarLoading, setSimilarLoading] = useState(false);
  const [similarSearched, setSimilarSearched] = useState(false);

  // 實體提取
  const [extractResult, setExtractResult] = useState<EntityExtractResponse | null>(null);
  const [extractLoading, setExtractLoading] = useState(false);

  const handleTriggerAnalysis = useCallback(async (force = false) => {
    if (!document?.id) return;
    try {
      await triggerMutation.mutateAsync({ documentId: document.id, force });
      message.success(force ? '重新分析完成' : '分析完成');
    } catch {
      message.error('AI 分析失敗');
    }
  }, [document?.id, triggerMutation, message]);

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

  const hasAnalysis = !!analysis;
  const isStale = analysis?.is_stale ?? false;
  const isAnalyzing = triggerMutation.isPending;

  const collapseItems = [
    // 1. AI 摘要
    {
      key: 'summary',
      label: (
        <Space size={4}>
          <RobotOutlined />
          <span>AI 摘要</span>
          {isStale && <Badge status="warning" text="需更新" />}
        </Space>
      ),
      children: (
        <div>
          {analysisLoading ? (
            <Spin size="small" />
          ) : analysis?.summary ? (
            <Paragraph style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}>
              {analysis.summary}
            </Paragraph>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              尚未生成摘要，點擊下方「分析」按鈕開始
            </Text>
          )}
          {analysis?.summary_confidence != null && (
            <Space size={4} style={{ fontSize: 11 }}>
              <Text type="secondary">信心度：</Text>
              <Progress
                percent={Math.round(analysis.summary_confidence * 100)}
                size="small"
                style={{ width: 100 }}
                strokeColor={analysis.summary_confidence >= 0.8 ? '#52c41a' : analysis.summary_confidence >= 0.5 ? '#faad14' : '#ff4d4f'}
              />
            </Space>
          )}
        </div>
      ),
    },

    // 2. 分類建議
    {
      key: 'classification',
      label: (
        <Space size={4}>
          <FolderOutlined />
          <span>分類建議</span>
        </Space>
      ),
      children: (
        <div>
          {analysisLoading ? (
            <Spin size="small" />
          ) : analysis?.suggested_doc_type || analysis?.suggested_category ? (
            <Descriptions size="small" bordered column={2} style={{ maxWidth: 500 }}>
              {analysis.suggested_doc_type && (
                <Descriptions.Item label="文件類型">
                  <Space size={4}>
                    <Tag color="blue">{analysis.suggested_doc_type}</Tag>
                    {analysis.doc_type_confidence != null && (
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {Math.round(analysis.doc_type_confidence * 100)}%
                      </Text>
                    )}
                  </Space>
                </Descriptions.Item>
              )}
              {analysis.suggested_category && (
                <Descriptions.Item label="分類">
                  <Space size={4}>
                    <Tag color="green">{analysis.suggested_category}</Tag>
                    {analysis.category_confidence != null && (
                      <Text type="secondary" style={{ fontSize: 11 }}>
                        {Math.round(analysis.category_confidence * 100)}%
                      </Text>
                    )}
                  </Space>
                </Descriptions.Item>
              )}
              {analysis.classification_reasoning && (
                <Descriptions.Item label="分類依據" span={2}>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {analysis.classification_reasoning}
                  </Text>
                </Descriptions.Item>
              )}
            </Descriptions>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              尚未分析分類
            </Text>
          )}
        </div>
      ),
    },

    // 3. 關鍵字
    {
      key: 'keywords',
      label: (
        <Space size={4}>
          <TagsOutlined />
          <span>關鍵字</span>
          {analysis?.keywords && analysis.keywords.length > 0 && (
            <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
              {analysis.keywords.length}
            </Tag>
          )}
        </Space>
      ),
      children: (
        <div>
          {analysisLoading ? (
            <Spin size="small" />
          ) : analysis?.keywords && analysis.keywords.length > 0 ? (
            <Space size={[4, 4]} wrap>
              {analysis.keywords.map((kw, i) => (
                <Tag key={i} color="processing">{kw}</Tag>
              ))}
              {analysis.keywords_confidence != null && (
                <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                  信心度 {Math.round(analysis.keywords_confidence * 100)}%
                </Text>
              )}
            </Space>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>
              尚未提取關鍵字
            </Text>
          )}
        </div>
      ),
    },

    // 4. NER 實體
    {
      key: 'ner',
      label: (
        <Space size={4}>
          <ExperimentOutlined />
          <span>NER 實體提取</span>
          {hasAnalysis && (analysis.entities_count > 0 || analysis.relations_count > 0) && (
            <Tag style={{ fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>
              {analysis.entities_count} 實體 / {analysis.relations_count} 關係
            </Tag>
          )}
        </Space>
      ),
      children: (
        <Space direction="vertical" size={8} style={{ width: '100%' }}>
          {hasAnalysis && (analysis.entities_count > 0 || analysis.relations_count > 0) ? (
            <Descriptions size="small" bordered column={2} style={{ maxWidth: 400 }}>
              <Descriptions.Item label="實體數">{analysis.entities_count}</Descriptions.Item>
              <Descriptions.Item label="關係數">{analysis.relations_count}</Descriptions.Item>
            </Descriptions>
          ) : null}
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
      ),
    },

    // 5. 語意相似公文
    {
      key: 'similar',
      label: (
        <Space size={4}>
          <FileSearchOutlined />
          <span>語意相似公文</span>
        </Space>
      ),
      children: (
        <div>
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
        </div>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 720 }}>
      {/* 分析狀態列 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <Space size={8}>
          {hasAnalysis ? (
            <>
              <Tag
                icon={isStale ? <WarningOutlined /> : <CheckCircleOutlined />}
                color={isStale ? 'warning' : 'success'}
              >
                {isStale ? '內容已變更，建議重新分析' : `分析完成 (${analysis.status})`}
              </Tag>
              {analysis.analyzed_at && (
                <Tooltip title={`分析時間：${analysis.analyzed_at}`}>
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    <ClockCircleOutlined style={{ marginRight: 2 }} />
                    {new Date(analysis.analyzed_at).toLocaleDateString('zh-TW')}
                  </Text>
                </Tooltip>
              )}
              {analysis.llm_model && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {analysis.llm_model}
                </Text>
              )}
            </>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>尚未進行 AI 分析</Text>
          )}
        </Space>
        <Space size={4}>
          <Button
            type="primary"
            size="small"
            icon={<RobotOutlined />}
            loading={isAnalyzing}
            onClick={() => handleTriggerAnalysis(false)}
            disabled={hasAnalysis && !isStale}
          >
            {hasAnalysis ? '重新分析' : '開始分析'}
          </Button>
          {hasAnalysis && (
            <Tooltip title="強制重新分析（忽略快取）">
              <Button
                size="small"
                icon={<ReloadOutlined />}
                loading={isAnalyzing}
                onClick={() => handleTriggerAnalysis(true)}
              />
            </Tooltip>
          )}
        </Space>
      </div>

      {/* Collapse 面板 */}
      <Collapse
        defaultActiveKey={hasAnalysis ? ['summary', 'classification', 'keywords'] : []}
        size="small"
        items={collapseItems}
      />
    </div>
  );
};

export default DocumentAITab;
