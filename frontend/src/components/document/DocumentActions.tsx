import React, { useState } from 'react';
import { Button, Space, Popconfirm, Tooltip, Dropdown, App } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  FilePdfOutlined,
  CopyOutlined,
  SendOutlined,
  FileZipOutlined,
  MoreOutlined,
  ExportOutlined,
  CalendarOutlined, // Add this import
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { Document } from '../../types';
import { useCalendarIntegration } from '../../hooks/useCalendarIntegration';

type ActionHandler = (document: Document) => void | Promise<void>;

interface DocumentActionsProps {
  document: Document;
  onView: ActionHandler;
  onEdit: ActionHandler;
  onDelete: ActionHandler;
  onCopy?: ActionHandler | undefined;
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
  onView,
  onEdit,
  onDelete,
  onCopy,
  onExportPdf,
  onArchive,
  onSend,
  size = 'small',
  mode = 'buttons',
  loadingStates = {},
}) => {
  const [internalLoading, setInternalLoading] = useState<Record<string, boolean>>({});
  const { loading: calendarLoading, addToCalendar } = useCalendarIntegration();
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

  const loading = { ...internalLoading, ...loadingStates };

  const actionConfig: {
    key: string;
    handler: ActionHandler;
    title: string;
    icon: React.ReactNode;
  }[] = [
    { key: 'view', handler: onView, title: '檢視', icon: <EyeOutlined /> },
    { key: 'edit', handler: onEdit, title: '編輯', icon: <EditOutlined /> },
    { key: 'delete', handler: onDelete, title: '刪除', icon: <DeleteOutlined /> },
    ...(onCopy
      ? [{ key: 'copy', handler: onCopy, title: '複製內容', icon: <CopyOutlined /> }]
      : []),
    ...(onExportPdf
      ? [{ key: 'exportPdf', handler: onExportPdf, title: '匯出 PDF', icon: <FilePdfOutlined /> }]
      : []),
    ...(onSend ? [{ key: 'send', handler: onSend, title: '傳送', icon: <SendOutlined /> }] : []),
    ...(onArchive
      ? [{ key: 'archive', handler: onArchive, title: '歸檔', icon: <FileZipOutlined /> }]
      : []),
  ];

  // 更多操作放入下拉選單
  const moreMenuItems: MenuProps['items'] = [
    {
      key: 'addToCalendar',
      label: '新增至日曆',
      icon: <CalendarOutlined />,
      onClick: async () => {
        const success = await addToCalendar(document);
        if (success) {
          message.success(`公文 ${document.doc_number || document.id} 已成功新增至日曆`);
        } else {
          message.error('新增至日曆失敗，請稍後再試');
        }
      },
    },
    ...(onExportPdf ? [{
      key: 'exportPdf',
      label: '匯出 PDF',
      icon: <FilePdfOutlined />,
      onClick: () => handleAction('exportPdf', onExportPdf),
    }] : []),
    ...(onCopy ? [{
      key: 'copy',
      label: '複製內容',
      icon: <CopyOutlined />,
      onClick: () => handleAction('copy', onCopy),
    }] : []),
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
    { type: 'divider' as const },
    {
      key: 'delete',
      label: '刪除',
      icon: <DeleteOutlined />,
      danger: true,
      onClick: () => handleAction('delete', onDelete),
    },
  ];

  // 主要按鈕只顯示「檢視」和「編輯」
  if (mode === 'buttons') {
    return (
      <Space size="small">
        <Button
          type="primary"
          icon={<EyeOutlined />}
          onClick={() => handleAction('view', onView)}
          loading={!!loading['view']}
          size={size}
        >
          檢視
        </Button>
        <Button
          icon={<EditOutlined />}
          onClick={() => handleAction('edit', onEdit)}
          loading={!!loading['edit']}
          size={size}
        >
          編輯
        </Button>
        <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
          <Button icon={<MoreOutlined />} size={size} />
        </Dropdown>
      </Space>
    );
  }

  if (mode === 'inline') {
    return (
      <Space>
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
    <Dropdown menu={{ items: menuItems }} trigger={['click']}>
      <Button icon={<MoreOutlined />} size={size} />
    </Dropdown>
  );
};

// 批量操作元件
interface BatchActionsProps {
  selectedCount: number;
  onExportSelected: () => void;
  onDeleteSelected: () => void;
  onArchiveSelected: () => void;
  onCopySelected: () => void;
  onClearSelection: () => void;
  loading?: boolean;
}

export const BatchActions: React.FC<BatchActionsProps> = ({
  selectedCount,
  onExportSelected,
  onDeleteSelected,
  onArchiveSelected,
  onCopySelected,
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

        <Button size="small" icon={<CopyOutlined />} onClick={onCopySelected} loading={loading}>
          批量複製
        </Button>

        <Button
          size="small"
          icon={<FileZipOutlined />}
          onClick={onArchiveSelected}
          loading={loading}
        >
          批量歸檔
        </Button>

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

        <Button size="small" type="text" onClick={onClearSelection}>
          取消選擇
        </Button>
      </Space>
    </div>
  );
};
