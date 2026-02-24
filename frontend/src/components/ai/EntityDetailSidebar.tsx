/**
 * EntityDetailSidebar - 正規化實體詳情側邊欄
 *
 * 從 KnowledgeGraph.tsx 提取，顯示正規化實體的：
 * - 基本資訊（名稱、提及次數、別名數）
 * - 別名列表
 * - 關聯公文（前 10 筆）
 * - 關係列表（含方向、權重、時效）
 *
 * @version 1.0.0
 * @created 2026-02-24
 * @extracted-from KnowledgeGraph.tsx
 */

import React, { useState, useEffect, useMemo } from 'react';
import {
  Spin, Empty, Tag, List, Descriptions,
  Drawer, Typography, Divider, Space, Tooltip,
} from 'antd';
import {
  CloseOutlined,
  TagsOutlined,
  FileTextOutlined,
  ShareAltOutlined,
} from '@ant-design/icons';
import { aiApi } from '../../api/aiApi';
import type {
  KGEntityDetailResponse,
  KGEntityRelationship,
  KGEntityDocument,
} from '../../types/ai';
import { getMergedNodeConfig } from '../../config/graphNodeConfig';

const { Text } = Typography;

function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + '...' : str;
}

export interface EntityDetailSidebarProps {
  visible: boolean;
  entityName: string;
  entityType: string;
  onClose: () => void;
}

export const EntityDetailSidebar: React.FC<EntityDetailSidebarProps> = ({
  visible,
  entityName,
  entityType,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<KGEntityDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const entityConfig = useMemo(() => getMergedNodeConfig(entityType), [entityType]);

  useEffect(() => {
    if (!visible || !entityName) {
      setDetail(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        // 圖譜顯示層用 "ner_project" 區分，但 DB 存的是 "project"
        const dbEntityType = entityType === 'ner_project' ? 'project' : entityType;
        const searchResult = await aiApi.searchGraphEntities({
          query: entityName, entity_type: dbEntityType, limit: 1,
        });
        if (cancelled) return;
        const firstMatch = searchResult.results?.[0];
        if (!firstMatch) {
          setError('尚未建立正規化實體');
          setLoading(false);
          return;
        }
        const detailResult = await aiApi.getEntityDetail({ entity_id: firstMatch.id });
        if (cancelled) return;
        setDetail(detailResult);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : '載入失敗');
        setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [visible, entityName, entityType]);

  return (
    <Drawer
      title={
        <Space>
          <span style={{
            width: 10, height: 10, borderRadius: '50%', display: 'inline-block',
            background: entityConfig.color,
          }} />
          <span>{entityName}</span>
          <Tooltip title={entityConfig.description}>
            <Tag color={entityConfig.color}>{entityConfig.label}</Tag>
          </Tooltip>
        </Space>
      }
      placement="right"
      width={380}
      open={visible}
      onClose={onClose}
      mask={false}
      closeIcon={<CloseOutlined />}
      styles={{ body: { padding: '12px 16px' } }}
    >
      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin tip="查詢正規化實體..."><div /></Spin>
        </div>
      )}

      {error && !loading && (
        <Empty description={error} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      {detail && !loading && (
        <>
          {/* 基本資訊 */}
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label="正規名稱">{detail.canonical_name}</Descriptions.Item>
            <Descriptions.Item label="提及次數">{detail.mention_count}</Descriptions.Item>
            <Descriptions.Item label="別名數">{detail.alias_count}</Descriptions.Item>
            {detail.first_seen_at && (
              <Descriptions.Item label="首次出現">{detail.first_seen_at.split('T')[0]}</Descriptions.Item>
            )}
            {detail.last_seen_at && (
              <Descriptions.Item label="最近出現">{detail.last_seen_at.split('T')[0]}</Descriptions.Item>
            )}
          </Descriptions>

          {/* 別名 */}
          {detail.aliases.length > 0 && (
            <>
              <Divider orientation="left" style={{ fontSize: 13 }}>
                <TagsOutlined /> 別名 ({detail.aliases.length})
              </Divider>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {detail.aliases.map((alias) => (
                  <Tag key={alias} color="blue">{alias}</Tag>
                ))}
              </div>
            </>
          )}

          {/* 關聯公文 */}
          {detail.documents.length > 0 && (
            <>
              <Divider orientation="left" style={{ fontSize: 13 }}>
                <FileTextOutlined /> 關聯公文 ({detail.documents.length})
              </Divider>
              <List
                size="small"
                dataSource={detail.documents.slice(0, 10)}
                renderItem={(doc: KGEntityDocument) => (
                  <List.Item style={{ padding: '4px 0' }}>
                    <div style={{ width: '100%' }}>
                      <div style={{ fontSize: 12 }}>
                        <Text strong>{doc.doc_number || `#${doc.document_id}`}</Text>
                        {doc.doc_date && (
                          <Text type="secondary" style={{ marginLeft: 8, fontSize: 11 }}>
                            {doc.doc_date}
                          </Text>
                        )}
                      </div>
                      {doc.subject && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {truncate(doc.subject, 40)}
                        </Text>
                      )}
                    </div>
                  </List.Item>
                )}
              />
              {detail.documents.length > 10 && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  ...還有 {detail.documents.length - 10} 篇
                </Text>
              )}
            </>
          )}

          {/* 關係 */}
          {detail.relationships.length > 0 && (
            <>
              <Divider orientation="left" style={{ fontSize: 13 }}>
                <ShareAltOutlined /> 關係 ({detail.relationships.length})
              </Divider>
              <List
                size="small"
                dataSource={detail.relationships}
                renderItem={(rel: KGEntityRelationship) => {
                  const otherName = rel.direction === 'outgoing'
                    ? rel.target_name : rel.source_name;
                  const otherType = rel.direction === 'outgoing'
                    ? rel.target_type : rel.source_type;
                  const arrow = rel.direction === 'outgoing' ? ' → ' : ' ← ';
                  return (
                    <List.Item style={{ padding: '4px 0' }}>
                      <div style={{ fontSize: 12, width: '100%' }}>
                        <Tag color="geekblue" style={{ fontSize: 11 }}>
                          {rel.relation_label || rel.relation_type}
                        </Tag>
                        <span>{arrow}</span>
                        <Text strong>{otherName}</Text>
                        {otherType && (
                          <Tag style={{ marginLeft: 4, fontSize: 10 }}>
                            {getMergedNodeConfig(otherType).label}
                          </Tag>
                        )}
                        <div style={{ fontSize: 10, color: '#999' }}>
                          權重: {rel.weight} | 佐證公文: {rel.document_count}
                          {rel.valid_from && ` | 自 ${rel.valid_from.split('T')[0]}`}
                        </div>
                      </div>
                    </List.Item>
                  );
                }}
              />
            </>
          )}
        </>
      )}
    </Drawer>
  );
};

export default EntityDetailSidebar;
