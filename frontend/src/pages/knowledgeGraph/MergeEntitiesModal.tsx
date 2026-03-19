import React from 'react';
import { Modal, Select, Space, Typography } from 'antd';
import { SwapOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface MergeEntitiesModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: () => void;
  keepId: number | null;
  mergeId: number | null;
  onKeepChange: (val: number | null) => void;
  onMergeChange: (val: number | null) => void;
  entityOptions: Array<{ label: string; value: number }>;
  onSearch: (query: string) => void;
  isLoading: boolean;
}

const MergeEntitiesModal: React.FC<MergeEntitiesModalProps> = ({
  open,
  onCancel,
  onOk,
  keepId,
  mergeId,
  onKeepChange,
  onMergeChange,
  entityOptions,
  onSearch,
  isLoading,
}) => {
  return (
    <Modal
      title={<><SwapOutlined /> 合併實體</>}
      open={open}
      onCancel={onCancel}
      onOk={onOk}
      okText="確定合併"
      cancelText="取消"
      confirmLoading={isLoading}
      okButtonProps={{ disabled: !keepId || !mergeId || keepId === mergeId }}
    >
      <Space vertical style={{ width: '100%' }} size={12}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          將「被合併實體」的所有別名、提及、關係轉移至「保留實體」，然後刪除被合併實體。
        </Text>
        <div>
          <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>保留實體</Text>
          <Select
            showSearch
            allowClear
            placeholder="搜尋要保留的實體"
            filterOption={false}
            onSearch={onSearch}
            onChange={(val) => onKeepChange(val ?? null)}
            options={entityOptions}
            style={{ width: '100%' }}
            notFoundContent={null}
          />
        </div>
        <div>
          <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>被合併實體</Text>
          <Select
            showSearch
            allowClear
            placeholder="搜尋要合併（刪除）的實體"
            filterOption={false}
            onSearch={onSearch}
            onChange={(val) => onMergeChange(val ?? null)}
            options={entityOptions}
            style={{ width: '100%' }}
            notFoundContent={null}
          />
        </div>
      </Space>
    </Modal>
  );
};

export default MergeEntitiesModal;
