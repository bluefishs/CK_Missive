/**
 * EntityDetailSidebar - 正規化實體詳情側邊欄
 *
 * 從 KnowledgeGraph.tsx 提取，顯示正規化實體的：
 * - 基本資訊（名稱、提及次數、別名數）
 * - 別名列表
 * - 關聯公文（前 10 筆）
 * - 關係列表（含方向、權重、時效）
 * - 關係時間軸
 *
 * @version 1.1.0
 * @created 2026-02-24
 * @updated 2026-02-26 - v1.1.0 整合時間軸 API
 */

import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Spin, Empty, Tag, Descriptions, Flex,
  Drawer, Typography, Divider, Space, Tooltip, Timeline,
} from 'antd';
import {
  CloseOutlined,
  TagsOutlined,
  FileTextOutlined,
  ShareAltOutlined,
  FieldTimeOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { aiApi } from '../../api/aiApi';
import type {
  KGEntityDetailResponse,
  KGEntityRelationship,
  KGEntityDocument,
} from '../../types/ai';
import { getMergedNodeConfig, CODE_ENTITY_TYPES } from '../../config/graphNodeConfig';

const { Text } = Typography;

/** 安全解析 JSON description（code entity 用） */
function parseCodeMeta(description: string | null | undefined): Record<string, unknown> | null {
  if (!description) return null;
  try {
    const parsed = JSON.parse(description);
    return typeof parsed === 'object' && parsed !== null ? parsed : null;
  } catch {
    return null;
  }
}

function truncate(str: string, max: number): string {
  return str.length > max ? str.slice(0, max) + '...' : str;
}

export interface EntityDetailSidebarProps {
  visible: boolean;
  entityName: string;
  entityType: string;
  onClose: () => void;
  /**
   * 自訂區塊渲染（移植時用於注入專案特定的詳情欄位）。
   * 預設顯示 Code Wiki 元數據區塊。設為 null 可隱藏。
   */
  renderExtraSections?: ((detail: KGEntityDetailResponse, entityType: string) => React.ReactNode) | null;
  /** inline 模式：不使用 Drawer overlay，改為內嵌面板（避免遮蔽圖譜） */
  inline?: boolean;
}

/** 內建的 Code Wiki 元數據渲染（CK_Missive 預設行為） */
const defaultExtraSections = (detail: KGEntityDetailResponse, type: string): React.ReactNode => {
  if (!CODE_ENTITY_TYPES.has(type)) return null;
  const meta = parseCodeMeta(detail.description);
  if (!meta) return null;
  return (
    <>
      <Divider titlePlacement="left" style={{ fontSize: 13 }}>
        <CodeOutlined /> 程式碼資訊
      </Divider>
      <Descriptions column={1} size="small" bordered items={[
        ...(meta.file_path ? [{ key: '檔案路徑', label: '檔案路徑', children: (<Text code style={{ fontSize: 11, wordBreak: 'break-all' }}>{String(meta.file_path)}</Text>) }] : []),
        ...(meta.lines != null ? [{ key: '行數', label: '行數', children: String(meta.lines) }] : []),
        ...(meta.line_start != null ? [{ key: '位置', label: '位置', children: (<>L{String(meta.line_start)}{meta.line_end ? `–L${String(meta.line_end)}` : ''}</>) }] : []),
        ...(meta.is_async != null ? [{ key: '非同步', label: '非同步', children: (<Tag color={meta.is_async ? 'green' : 'default'}>{meta.is_async ? 'async' : 'sync'}</Tag>) }] : []),
        ...(meta.is_private != null && meta.is_private ? [{ key: '可見性', label: '可見性', children: (<Tag color="orange">private</Tag>) }] : []),
        ...(Array.isArray(meta.args) && meta.args.length > 0 ? [{ key: '參數', label: '參數', children: (<>{(meta.args as string[]).map((arg) => (<Tag key={arg} style={{ fontSize: 11 }}>{arg}</Tag>))}</>) }] : []),
        ...(Array.isArray(meta.bases) && meta.bases.length > 0 ? [{ key: '繼承', label: '繼承', children: (<>{(meta.bases as string[]).map((base) => (<Tag key={base} color="purple" style={{ fontSize: 11 }}>{base}</Tag>))}</>) }] : []),
        ...(meta.table_name ? [{ key: '表名', label: '表名', children: (<Text code>{String(meta.table_name)}</Text>) }] : []),
        ...(meta.column_count != null ? [{ key: '欄位數', label: '欄位數', children: String(meta.column_count) }] : []),
      ]} />
      {meta.docstring && (
        <div style={{ marginTop: 8, padding: '6px 8px', background: '#f6f8fa', borderRadius: 4, fontSize: 12 }}>
          <Text type="secondary" style={{ fontSize: 11 }}>docstring:</Text>
          <div style={{ whiteSpace: 'pre-wrap', marginTop: 2 }}>
            {truncate(String(meta.docstring), 200)}
          </div>
        </div>
      )}
    </>
  );
};

export const EntityDetailSidebar: React.FC<EntityDetailSidebarProps> = ({
  visible,
  entityName,
  entityType,
  onClose,
  renderExtraSections = defaultExtraSections,
  inline = false,
}) => {
  const entityConfig = useMemo(() => getMergedNodeConfig(entityType), [entityType]);

  const { data: entityData, isLoading: loading, error: queryError } = useQuery({
    queryKey: ['entity-detail', entityName, entityType],
    queryFn: async () => {
      // 統一後 agency/typroject 可能來自 NER，不傳 entity_type 避免篩選衝突
      const searchResult = await aiApi.searchGraphEntities({
        query: entityName, limit: 1,
      });
      const firstMatch = searchResult.results?.[0];
      if (!firstMatch) {
        throw new Error('尚未建立正規化實體');
      }
      const [detailResult, timelineResult] = await Promise.all([
        aiApi.getEntityDetail({ entity_id: firstMatch.id }),
        aiApi.getEntityTimeline({ entity_id: firstMatch.id }),
      ]);
      return { detail: detailResult, timeline: timelineResult.timeline || [] };
    },
    enabled: visible && !!entityName,
    staleTime: 2 * 60 * 1000,
  });

  const detail = entityData?.detail ?? null;
  const timeline = entityData?.timeline ?? [];
  const error = queryError instanceof Error ? queryError.message : null;

  const titleContent = (
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
  );

  const bodyContent = (
    <>
      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Spin description="查詢正規化實體..."><div /></Spin>
        </div>
      )}

      {error && !loading && (
        <Empty description={error} image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}

      {detail && !loading && (
        <>
          {/* 基本資訊 */}
          <Descriptions column={1} size="small" bordered items={[
            { key: '正規名稱', label: '正規名稱', children: detail.canonical_name },
            { key: '提及次數', label: '提及次數', children: detail.mention_count },
            { key: '別名數', label: '別名數', children: detail.alias_count },
            ...(detail.first_seen_at ? [{ key: '首次出現', label: '首次出現', children: detail.first_seen_at.split('T')[0] }] : []),
            ...(detail.last_seen_at ? [{ key: '最近出現', label: '最近出現', children: detail.last_seen_at.split('T')[0] }] : []),
          ]} />

          {/* 自訂區塊（預設：Code Wiki 元數據） */}
          {renderExtraSections?.(detail, entityType)}

          {/* 別名 */}
          {detail.aliases.length > 0 && (
            <>
              <Divider titlePlacement="left" style={{ fontSize: 13 }}>
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
              <Divider titlePlacement="left" style={{ fontSize: 13 }}>
                <FileTextOutlined /> 關聯公文 ({detail.documents.length})
              </Divider>
              <Flex vertical gap={4}>
                {detail.documents.slice(0, 10).map((doc: KGEntityDocument) => (
                  <div key={doc.document_id} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
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
                ))}
              </Flex>
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
              <Divider titlePlacement="left" style={{ fontSize: 13 }}>
                <ShareAltOutlined /> 關係 ({detail.relationships.length})
              </Divider>
              <Flex vertical gap={4}>
                {detail.relationships.map((rel: KGEntityRelationship, idx: number) => {
                  const otherName = rel.direction === 'outgoing'
                    ? rel.target_name : rel.source_name;
                  const otherType = rel.direction === 'outgoing'
                    ? rel.target_type : rel.source_type;
                  const arrow = rel.direction === 'outgoing' ? ' → ' : ' ← ';
                  return (
                    <div key={idx} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
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
                    </div>
                  );
                })}
              </Flex>
            </>
          )}

          {/* 時間軸 */}
          {timeline.length > 0 && (
            <>
              <Divider titlePlacement="left" style={{ fontSize: 13 }}>
                <FieldTimeOutlined /> 關係時間軸 ({timeline.length})
              </Divider>
              <Timeline
                items={timeline.slice(0, 15).map((item) => ({
                  color: item.direction === 'outgoing' ? 'blue' : 'green',
                  children: (
                    <div style={{ fontSize: 12 }}>
                      <Tag color="geekblue" style={{ fontSize: 11 }}>
                        {item.relation_label || item.relation_type}
                      </Tag>
                      <Text>{item.direction === 'outgoing' ? ' → ' : ' ← '}</Text>
                      <Text strong>{item.other_name}</Text>
                      <div style={{ fontSize: 10, color: '#999' }}>
                        {item.valid_from && `自 ${item.valid_from.split('T')[0]}`}
                        {item.valid_to && ` 至 ${item.valid_to.split('T')[0]}`}
                        {` | 權重 ${item.weight} | ${item.document_count} 篇公文`}
                      </div>
                    </div>
                  ),
                }))}
              />
              {timeline.length > 15 && (
                <Text type="secondary" style={{ fontSize: 11 }}>
                  ...還有 {timeline.length - 15} 筆
                </Text>
              )}
            </>
          )}
        </>
      )}
    </>
  );

  if (inline) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#fff' }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '12px 16px', borderBottom: '1px solid #f0f0f0', flexShrink: 0,
        }}>
          <div style={{ fontSize: 14, fontWeight: 500 }}>{titleContent}</div>
          <CloseOutlined onClick={onClose} style={{ cursor: 'pointer', color: '#999' }} />
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: '12px 16px' }}>
          {bodyContent}
        </div>
      </div>
    );
  }

  return (
    <Drawer
      title={titleContent}
      placement="right"

      open={visible}
      onClose={onClose}
      mask={false}
      push={false}
      closeIcon={<CloseOutlined />}
      styles={{ body: { padding: '12px 16px' } }}
    >
      {bodyContent}
    </Drawer>
  );
};

export default EntityDetailSidebar;
