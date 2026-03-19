import { Button, Space, Popconfirm } from 'antd';
import {
  SendOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  DeleteOutlined,
} from '@ant-design/icons';

export interface DispatchDetailHeaderProps {
  dispatchNo?: string;
  workType?: string;
  isEditing: boolean;
  canEdit: boolean;
  canDelete: boolean;
  isSaving: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancelEdit: () => void;
  onDelete: () => void;
}

export function buildDispatchDetailHeader({
  dispatchNo,
  workType,
  isEditing,
  canEdit,
  canDelete,
  isSaving,
  onEdit,
  onSave,
  onCancelEdit,
  onDelete,
}: DispatchDetailHeaderProps) {
  return {
    title: dispatchNo || '派工詳情',
    icon: <SendOutlined />,
    backText: '返回派工列表',
    backPath: '/taoyuan/dispatch',
    tags: workType
      ? [{ text: workType, color: 'blue' as const }]
      : [],
    extra: (
      <Space>
        {isEditing ? (
          <>
            <Button icon={<CloseOutlined />} onClick={onCancelEdit}>
              取消
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={isSaving}
              disabled={isSaving}
              onClick={onSave}
            >
              儲存
            </Button>
          </>
        ) : (
          <>
            {canEdit && (
              <Button
                type="primary"
                icon={<EditOutlined />}
                onClick={onEdit}
              >
                編輯
              </Button>
            )}
            {canDelete && (
              <Popconfirm
                title="確定要刪除此派工單嗎？"
                description="刪除後將無法復原，請確認是否繼續。"
                onConfirm={onDelete}
                okText="確定刪除"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button danger icon={<DeleteOutlined />}>
                  刪除
                </Button>
              </Popconfirm>
            )}
          </>
        )}
      </Space>
    ),
  };
}
