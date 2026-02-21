import React, { useState } from 'react';
import { Button, Space, Dropdown, App } from 'antd';
import {
  DeleteOutlined,
  FilePdfOutlined,
  SendOutlined,
  FileZipOutlined,
  MoreOutlined,
  ExportOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Document } from '../../types';

type ActionHandler = (document: Document) => void | Promise<void>;

interface DocumentActionsProps {
  document: Document;
  onView: ActionHandler;
  onEdit: ActionHandler;
  onDelete: ActionHandler;
  onCopy?: ActionHandler;
  onExportPdf?: ActionHandler | undefined;
  onArchive?: ActionHandler | undefined;
  onSend?: ActionHandler | undefined;
  size?: 'small' | 'middle' | 'large';
  mode?: 'buttons' | 'dropdown' | 'inline';
  loadingStates?: {
    isExporting?: boolean;
    isAddingToCalendar?: boolean;
    [key: string]: boolean | undefined;
  };
}

export const DocumentActions: React.FC<DocumentActionsProps> = ({
  document,
  onView: _onView,
  onEdit: _onEdit,
  onDelete,
  onCopy: _onCopy,
  onExportPdf,
  onArchive,
  onSend,
  size = 'small',
  mode = 'buttons',
  loadingStates: _loadingStates = {},
}) => {
  const [, setInternalLoading] = useState<Record<string, boolean>>({});
  const { message } = App.useApp();

  const handleAction = async (key: string, handler: ActionHandler) => {
    setInternalLoading(prev => ({ ...prev, [key]: true }));
    try {
      await handler(document);
    } catch (error) {
      message.error(`操作失敗: ${error}`);
    } finally {
      setInternalLoading(prev => ({ ...prev, [key]: false }));
    }
  };

  const actionConfig: {
    key: string;
    handler: ActionHandler;
    title: string;
    icon: React.ReactNode;
  }[] = [
    { key: 'delete', handler: onDelete, title: '刪除', icon: <DeleteOutlined /> },
    // 複製公文功能已停用 (2026-01-12)
    // ...(onCopy
    //   ? [{ key: 'copy', handler: onCopy, title: '複製內容', icon: <CopyOutlined /> }]
    //   : []),
    ...(onExportPdf
      ? [{ key: 'exportPdf', handler: onExportPdf, title: '匯出 PDF', icon: <FilePdfOutlined /> }]
      : []),
    ...(onSend ? [{ key: 'send', handler: onSend, title: '傳送', icon: <SendOutlined /> }] : []),
    ...(onArchive
      ? [{ key: 'archive', handler: onArchive, title: '歸檔', icon: <FileZipOutlined /> }]
      : []),
  ];

  // 更多操作下拉選單 - 功能已移至詳情頁頂部按鈕 (2026-01-12)
  // 列表頁操作欄已移除，點擊行直接進入詳情頁進行操作
  const moreMenuItems: MenuProps['items'] = [
    // 新增至日曆 - 已移至詳情頁頂部
    // {
    //   key: 'addToCalendar',
    //   label: '新增至日曆',
    //   icon: <CalendarOutlined />,
    //   onClick: async () => {
    //     const success = await addToCalendar(document);
    //     if (success) {
    //       message.success(`公文 ${document.doc_number || document.id} 已成功新增至日曆`);
    //     } else {
    //       message.error('新增至日曆失敗，請稍後再試');
    //     }
    //   },
    // },
    ...(onExportPdf ? [{
      key: 'exportPdf',
      label: '匯出 PDF',
      icon: <FilePdfOutlined />,
      onClick: () => handleAction('exportPdf', onExportPdf),
    }] : []),
    // 複製公文功能已停用 (2026-01-12)
    // ...(onCopy ? [{
    //   key: 'copy',
    //   label: '複製內容',
    //   icon: <CopyOutlined />,
    //   onClick: () => handleAction('copy', onCopy),
    // }] : []),
    ...(onSend ? [{
      key: 'send',
      label: '傳送',
      icon: <SendOutlined />,
      onClick: () => handleAction('send', onSend),
    }] : []),
    ...(onArchive ? [{
      key: 'archive',
      label: '歸檔',
      icon: <FileZipOutlined />,
      onClick: () => handleAction('archive', onArchive),
    }] : []),
    // 刪除 - 已移至詳情頁頂部
    // { type: 'divider' as const },
    // {
    //   key: 'delete',
    //   label: '刪除',
    //   icon: <DeleteOutlined />,
    //   danger: true,
    //   onClick: () => handleAction('delete', onDelete),
    // },
  ];

  // 操作按鈕：只顯示下拉選單（點擊列可檢視/編輯）
  if (mode === 'buttons') {
    return (
      <Space size="small" onClick={(e) => e.stopPropagation()}>
        <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
          <Button icon={<MoreOutlined />} size={size}>
            更多
          </Button>
        </Dropdown>
      </Space>
    );
  }

  if (mode === 'inline') {
    return (
      <Space onClick={(e) => e.stopPropagation()}>
        {actionConfig.map(action => (
          <Button
            key={action.key}
            type="link"
            icon={action.icon}
            onClick={() => handleAction(action.key, action.handler)}
            size={size}
          >
            {action.title}
          </Button>
        ))}
      </Space>
    );
  }

  // Default to dropdown mode
  return (
    <div onClick={(e) => e.stopPropagation()}>
      <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
        <Button icon={<MoreOutlined />} size={size} aria-label="更多操作" />
      </Dropdown>
    </div>
  );
};

// 批量操作元件
interface BatchActionsProps {
  selectedCount: number;
  onExportSelected: () => void;
  onDeleteSelected?: () => void;
  onArchiveSelected?: () => void;
  onCopySelected?: () => void;
  onClearSelection: () => void;
  loading?: boolean;
}

export const BatchActions: React.FC<BatchActionsProps> = ({
  selectedCount,
  onExportSelected,
  onDeleteSelected: _onDeleteSelected,
  onArchiveSelected: _onArchiveSelected,
  onCopySelected: _onCopySelected,
  onClearSelection,
  loading = false,
}) => {
  if (selectedCount === 0) return null;

  return (
    <div
      style={{
        marginBottom: 16,
        padding: '8px 16px',
        background: '#f0f0f0',
        borderRadius: 6,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}
    >
      <span style={{ color: '#666' }}>
        已選中 <strong>{selectedCount}</strong> 個公文
      </span>

      <Space>
        <Button size="small" icon={<ExportOutlined />} onClick={onExportSelected} loading={loading}>
          批量匯出
        </Button>

        {/* 批量複製功能已停用 (2026-01-12)
        <Button size="small" icon={<CopyOutlined />} onClick={onCopySelected} loading={loading}>
          批量複製
        </Button>
        */}

        {/* 批量歸檔功能 - 目前尚無管理需求，暫時隱藏 (2026-01-12)
        <Button
          size="small"
          icon={<FileZipOutlined />}
          onClick={onArchiveSelected}
          loading={loading}
        >
          批量歸檔
        </Button>
        */}

        {/* 批量刪除功能 - 已移至詳情頁操作 (2026-01-12)
        <Popconfirm
          title={`確定要刪除選中的 ${selectedCount} 個公文嗎？`}
          onConfirm={onDeleteSelected}
          okText="確定"
          cancelText="取消"
        >
          <Button size="small" danger icon={<DeleteOutlined />} loading={loading}>
            批量刪除
          </Button>
        </Popconfirm>
        */}

        <Button size="small" type="text" onClick={onClearSelection}>
          取消選擇
        </Button>
      </Space>
    </div>
  );
};
