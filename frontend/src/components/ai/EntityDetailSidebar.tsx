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

import React, { useState, useEffect, useMemo } from 'react';
import {
  Spin, Empty, Tag, List, Descriptions,
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
  KGTimelineItem,
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
      <Divider orientation="left" style={{ fontSize: 13 }}>
        <CodeOutlined /> 程式碼資訊
      </Divider>
      <Descriptions column={1} size="small" bordered>
        {!!meta.file_path && (
          <Descriptions.Item label="檔案路徑">
            <Text code style={{ fontSize: 11, wordBreak: 'break-all' }}>
              {String(meta.file_path)}
            </Text>
          </Descriptions.Item>
        )}
        {meta.lines != null && (
          <Descriptions.Item label="行數">{String(meta.lines)}</Descriptions.Item>
        )}
        {meta.line_start != null && (
          <Descriptions.Item label="位置">
            L{String(meta.line_start)}
            {meta.line_end ? `–L${String(meta.line_end)}` : ''}
          </Descriptions.Item>
        )}
        {meta.is_async != null && (
          <Descriptions.Item label="非同步">
            <Tag color={meta.is_async ? 'green' : 'default'}>
              {meta.is_async ? 'async' : 'sync'}
            </Tag>
          </Descriptions.Item>
        )}
        {meta.is_private != null && meta.is_private && (
          <Descriptions.Item label="可見性">
            <Tag color="orange">private</Tag>
          </Descriptions.Item>
        )}
        {Array.isArray(meta.args) && meta.args.length > 0 && (
          <Descriptions.Item label="參數">
            {(meta.args as string[]).map((arg) => (
              <Tag key={arg} style={{ fontSize: 11 }}>{arg}</Tag>
            ))}
          </Descriptions.Item>
        )}
        {Array.isArray(meta.bases) && meta.bases.length > 0 && (
          <Descriptions.Item label="繼承">
            {(meta.bases as string[]).map((base) => (
              <Tag key={base} color="purple" style={{ fontSize: 11 }}>{base}</Tag>
            ))}
          </Descriptions.Item>
        )}
        {!!meta.table_name && (
          <Descriptions.Item label="表名">
            <Text code>{String(meta.table_name)}</Text>
          </Descriptions.Item>
        )}
        {meta.column_count != null && (
          <Descriptions.Item label="欄位數">{String(meta.column_count)}</Descriptions.Item>
        )}
      </Descriptions>
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
  const [loading, setLoading] = useState(false);
  const [detail, setDetail] = useState<KGEntityDetailResponse | null>(null);
  const [timeline, setTimeline] = useState<KGTimelineItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const entityConfig = useMemo(() => getMergedNodeConfig(entityType), [entityType]);

  useEffect(() => {
    if (!visible || !entityName) {
      setDetail(null);
      setTimeline([]);
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
        const [detailResult, timelineResult] = await Promise.all([
          aiApi.getEntityDetail({ entity_id: firstMatch.id }),
          aiApi.getEntityTimeline({ entity_id: firstMatch.id }),
        ]);
        if (cancelled) return;
        setDetail(detailResult);
        setTimeline(timelineResult.timeline || []);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : '載入失敗');
        setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [visible, entityName, entityType]);

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

          {/* 自訂區塊（預設：Code Wiki 元數據） */}
          {renderExtraSections?.(detail, entityType)}

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

          {/* 時間軸 */}
          {timeline.length > 0 && (
            <>
              <Divider orientation="left" style={{ fontSize: 13 }}>
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
      width={380}
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
