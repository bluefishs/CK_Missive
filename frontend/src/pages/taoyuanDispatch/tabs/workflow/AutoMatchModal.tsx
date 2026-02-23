/**
 * AutoMatchModal - 自動匹配公文結果 Modal
 *
 * 顯示根據工程名稱自動匹配到的公文，讓使用者勾選後批次建立關聯。
 * 分「機關來函」與「乾坤發文」兩區，支援全選/反選。
 *
 * @version 1.0.0
 * @date 2026-02-23
 */

import React, { useCallback } from 'react';
import {
  Modal,
  Checkbox,
  Tag,
  Typography,
  Space,
  Empty,
  Divider,
  Tooltip,
} from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import type { DocumentHistoryItem } from '../../../../types/taoyuan';

const { Text, Title } = Typography;

export interface AutoMatchModalProps {
  open: boolean;
  projectName: string;
  agencyDocs: DocumentHistoryItem[];
  companyDocs: DocumentHistoryItem[];
  selectedIds: Set<number>;
  onSelectedIdsChange: (ids: Set<number>) => void;
  onConfirm: () => void;
  onCancel: () => void;
  loading: boolean;
}

/** 單筆公文行 */
const DocRowInner: React.FC<{
  doc: DocumentHistoryItem;
  checked: boolean;
  onChange: (id: number, checked: boolean) => void;
}> = ({ doc, checked, onChange }) => {
  const docNumber = doc.doc_number || `#${doc.id}`;
  const subject = doc.subject || '(無主旨)';
  const dateStr = doc.doc_date ? doc.doc_date.substring(0, 10) : '';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 0',
        borderBottom: '1px solid #f0f0f0',
      }}
    >
      <Checkbox
        checked={checked}
        onChange={(e) => onChange(doc.id, e.target.checked)}
      />
      <FileTextOutlined style={{ color: '#999', flexShrink: 0 }} />
      <Text strong style={{ flexShrink: 0, minWidth: 160 }}>
        {docNumber}
      </Text>
      <Tooltip title={subject}>
        <Text
          type="secondary"
          ellipsis
          style={{ flex: 1, maxWidth: 300 }}
        >
          {subject}
        </Text>
      </Tooltip>
      {dateStr && (
        <Text type="secondary" style={{ flexShrink: 0, fontSize: 12 }}>
          {dateStr}
        </Text>
      )}
    </div>
  );
};

const DocRow = React.memo(DocRowInner);
DocRow.displayName = 'DocRow';

/** 公文區塊（機關來函/乾坤發文） */
const DocSection: React.FC<{
  title: string;
  tagColor: string;
  docs: DocumentHistoryItem[];
  selectedIds: Set<number>;
  onToggle: (id: number, checked: boolean) => void;
  onToggleAll: (ids: number[], checked: boolean) => void;
}> = ({ title, tagColor, docs, selectedIds, onToggle, onToggleAll }) => {
  if (docs.length === 0) return null;

  const allChecked = docs.every((d) => selectedIds.has(d.id));
  const someChecked = docs.some((d) => selectedIds.has(d.id)) && !allChecked;
  const docIds = docs.map((d) => d.id);

  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          marginBottom: 8,
        }}
      >
        <Checkbox
          checked={allChecked}
          indeterminate={someChecked}
          onChange={(e) => onToggleAll(docIds, e.target.checked)}
        />
        <Tag color={tagColor}>{title}</Tag>
        <Text type="secondary">({docs.length} 筆)</Text>
      </div>
      <div style={{ paddingLeft: 24 }}>
        {docs.map((doc) => (
          <DocRow
            key={doc.id}
            doc={doc}
            checked={selectedIds.has(doc.id)}
            onChange={onToggle}
          />
        ))}
      </div>
    </div>
  );
};

const AutoMatchModalInner: React.FC<AutoMatchModalProps> = ({
  open,
  projectName,
  agencyDocs,
  companyDocs,
  selectedIds,
  onSelectedIdsChange,
  onConfirm,
  onCancel,
  loading,
}) => {
  const totalDocs = agencyDocs.length + companyDocs.length;
  const selectedCount = selectedIds.size;

  const handleToggle = useCallback(
    (id: number, checked: boolean) => {
      const next = new Set(selectedIds);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      onSelectedIdsChange(next);
    },
    [selectedIds, onSelectedIdsChange],
  );

  const handleToggleAll = useCallback(
    (ids: number[], checked: boolean) => {
      const next = new Set(selectedIds);
      for (const id of ids) {
        if (checked) {
          next.add(id);
        } else {
          next.delete(id);
        }
      }
      onSelectedIdsChange(next);
    },
    [selectedIds, onSelectedIdsChange],
  );

  return (
    <Modal
      title={
        <Space>
          <FileTextOutlined />
          <span>自動匹配公文結果</span>
        </Space>
      }
      open={open}
      onOk={onConfirm}
      onCancel={onCancel}
      okText={`關聯 ${selectedCount} 筆`}
      cancelText="取消"
      okButtonProps={{ disabled: selectedCount === 0, loading }}
      width={700}
      styles={{ body: { maxHeight: 500, overflow: 'auto' } }}
    >
      <div style={{ marginBottom: 12 }}>
        <Text type="secondary">
          根據工程名稱及作業類別關鍵字匹配到{' '}
          <Text strong>{totalDocs}</Text> 筆尚未關聯的公文：
        </Text>
      </div>

      {totalDocs === 0 ? (
        <Empty description="無匹配結果" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <>
          <DocSection
            title="機關來函"
            tagColor="blue"
            docs={agencyDocs}
            selectedIds={selectedIds}
            onToggle={handleToggle}
            onToggleAll={handleToggleAll}
          />

          {agencyDocs.length > 0 && companyDocs.length > 0 && <Divider style={{ margin: '8px 0' }} />}

          <DocSection
            title="乾坤發文"
            tagColor="green"
            docs={companyDocs}
            selectedIds={selectedIds}
            onToggle={handleToggle}
            onToggleAll={handleToggleAll}
          />
        </>
      )}
    </Modal>
  );
};

export const AutoMatchModal = React.memo(AutoMatchModalInner);
AutoMatchModal.displayName = 'AutoMatchModal';
