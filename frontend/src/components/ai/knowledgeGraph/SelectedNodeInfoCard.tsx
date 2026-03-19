/**
 * SelectedNodeInfoCard - Floating info panel for a selected graph node
 *
 * Displays node metadata (type, label, doc_number, category, status),
 * neighbor count, and contextual action links:
 * - NER entities: "檢視正規化實體詳情" (opens EntityDetailSidebar)
 * - Business entities: "前往頁面" (navigates to the corresponding system page)
 *
 * @version 1.1.0
 * @created 2026-02-27
 * @updated 2026-03-12 — v1.1.0 新增業務實體頁面導航
 */

import React from 'react';
import { LinkOutlined, ExportOutlined } from '@ant-design/icons';
import type { MergedNodeConfig } from '../../../config/graphNodeConfig';

export interface SelectedNodeData {
  id: string;
  label: string;
  type: string;
  color: string;
  category?: string | null;
  doc_number?: string | null;
  status?: string | null;
}

export interface SelectedNodeInfoCardProps {
  node: SelectedNodeData;
  nodeConfig: MergedNodeConfig;
  neighborCount: number;
  onClose: () => void;
  onViewDetail: (label: string, type: string) => void;
}

/** 業務實體 → 系統頁面路徑映射 */
function getBusinessEntityUrl(node: SelectedNodeData): string | null {
  // 從 node.id 取出數字 ID (格式: doc_123, project_456, etc.)
  const numId = node.id.replace(/^[a-z]+_/, '');

  switch (node.type) {
    case 'document':
      return numId ? `/documents/${numId}` : '/documents';
    case 'project':
      return numId ? `/contract-cases/${numId}` : '/contract-cases';
    case 'agency':
      return '/agencies';
    case 'dispatch':
      return numId ? `/taoyuan/dispatch/${numId}` : '/taoyuan/dispatch';
    case 'typroject':
      return numId ? `/taoyuan/project/${numId}` : '/taoyuan/dispatch';
    default:
      return null;
  }
}

/** 業務實體類型集合 */
const BUSINESS_ENTITY_TYPES = new Set(['document', 'project', 'agency', 'dispatch', 'typroject']);

export const SelectedNodeInfoCard: React.FC<SelectedNodeInfoCardProps> = ({
  node,
  nodeConfig,
  neighborCount,
  onClose,
  onViewDetail,
}) => {
  const businessUrl = BUSINESS_ENTITY_TYPES.has(node.type) ? getBusinessEntityUrl(node) : null;

  return (
    <div
      style={{
        position: 'absolute', top: 45, right: 8,
        background: 'white', border: '1px solid #d9d9d9', borderRadius: 6,
        padding: '10px 14px', fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        minWidth: 200, maxWidth: 280, zIndex: 1000,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ fontWeight: 'bold', color: node.color, fontSize: 13 }}>
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            background: node.color, display: 'inline-block', marginRight: 6,
          }} />
          {nodeConfig.label}
        </div>
        <span
          style={{ color: '#999', cursor: 'pointer', fontSize: 14 }}
          onClick={onClose}
        >
          &#x2715;
        </span>
      </div>
      <div style={{ fontWeight: 500, marginBottom: 4 }}>{node.label}</div>
      {nodeConfig.description && (
        <div style={{ color: '#999', fontSize: 11, marginBottom: 4 }}>{nodeConfig.description}</div>
      )}
      {node.doc_number && <div style={{ color: '#666' }}>文號：{node.doc_number}</div>}
      {node.category && <div style={{ color: '#666' }}>分類：{node.category}</div>}
      {node.status && <div style={{ color: '#666' }}>狀態：{node.status}</div>}
      <div style={{ color: '#666', marginTop: 2 }}>關聯節點：{neighborCount} 個</div>

      {/* NER 實體：檢視正規化實體詳情 */}
      {nodeConfig.detailable && (
        <div
          style={{
            color: '#1890ff', marginTop: 8, fontSize: 12, cursor: 'pointer',
            padding: '4px 8px', background: '#f0f5ff', borderRadius: 4,
            textAlign: 'center', border: '1px solid #d6e4ff',
          }}
          onClick={() => onViewDetail(node.label, node.type)}
        >
          <LinkOutlined /> 檢視正規化實體詳情
        </div>
      )}

      {/* 業務實體：前往對應系統頁面 */}
      {businessUrl && (
        <div
          style={{
            color: '#52c41a', marginTop: 6, fontSize: 12, cursor: 'pointer',
            padding: '4px 8px', background: '#f6ffed', borderRadius: 4,
            textAlign: 'center', border: '1px solid #b7eb8f',
          }}
          onClick={() => window.open(businessUrl, '_blank')}
        >
          <ExportOutlined /> 前往對應頁面
        </div>
      )}
    </div>
  );
};
