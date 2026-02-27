/**
 * SelectedNodeInfoCard - Floating info panel for a selected graph node
 *
 * Displays node metadata (type, label, doc_number, category, status),
 * neighbor count, and an optional link to the entity detail sidebar.
 *
 * Extracted from KnowledgeGraph.tsx to reduce main component complexity.
 *
 * @version 1.0.0
 * @created 2026-02-27
 */

import React from 'react';
import { LinkOutlined } from '@ant-design/icons';
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

export const SelectedNodeInfoCard: React.FC<SelectedNodeInfoCardProps> = ({
  node,
  nodeConfig,
  neighborCount,
  onClose,
  onViewDetail,
}) => {
  return (
    <div
      style={{
        position: 'absolute', top: 45, right: 8,
        background: 'white', border: '1px solid #d9d9d9', borderRadius: 6,
        padding: '10px 14px', fontSize: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        minWidth: 200, maxWidth: 280, zIndex: 10,
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
    </div>
  );
};
