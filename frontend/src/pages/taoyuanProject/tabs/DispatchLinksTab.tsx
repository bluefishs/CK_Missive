/**
 * 派工關聯 Tab
 */

import React from 'react';
import {
  Select,
  Button,
  Space,
  Row,
  Col,
  Spin,
  Empty,
  Descriptions,
  Popconfirm,
  List,
  Card,
  Tag,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

import type { DispatchOrder, ProjectDispatchLink } from '../../../types/api';

interface DispatchLinksTabProps {
  isLoading: boolean;
  isEditing: boolean;
  canEdit: boolean;
  linkedDispatches: ProjectDispatchLink[];
  filteredDispatches: DispatchOrder[];
  selectedDispatchId: number | undefined;
  setSelectedDispatchId: (id: number | undefined) => void;
  handleLinkDispatch: () => void;
  linkDispatchMutation: { isPending: boolean };
  unlinkDispatchMutation: { isPending: boolean; mutate: (linkId: number) => void };
  refetch: () => void;
  message: { error: (msg: string) => void };
}

export const DispatchLinksTab: React.FC<DispatchLinksTabProps> = ({
  isLoading,
  isEditing,
  canEdit,
  linkedDispatches,
  filteredDispatches,
  selectedDispatchId,
  setSelectedDispatchId,
  handleLinkDispatch,
  linkDispatchMutation,
  unlinkDispatchMutation,
  refetch,
  message,
}) => {
  const navigate = useNavigate();

  return (
    <Spin spinning={isLoading}>
      {canEdit && isEditing && (
        <Card size="small" style={{ marginBottom: 16 }} title="新增派工關聯">
          <Row gutter={[12, 12]} align="middle">
            <Col span={16}>
              <Select
                showSearch
                allowClear
                placeholder="搜尋派工單號..."
                style={{ width: '100%' }}
                value={selectedDispatchId}
                onChange={setSelectedDispatchId}
                filterOption={(input, option) =>
                  String(option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                }
                options={filteredDispatches.map((d: DispatchOrder) => ({
                  value: d.id,
                  label: `${d.dispatch_no} - ${d.project_name || '(無工程名稱)'}`,
                }))}
                notFoundContent={
                  filteredDispatches.length === 0 ? (
                    <Empty description="無可關聯的派工紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  ) : undefined
                }
              />
            </Col>
            <Col span={8}>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleLinkDispatch}
                loading={linkDispatchMutation.isPending}
                disabled={!selectedDispatchId}
              >
                建立關聯
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {linkedDispatches.length > 0 ? (
        <List
          dataSource={linkedDispatches}
          renderItem={(dispatch: ProjectDispatchLink) => (
            <Card size="small" style={{ marginBottom: 12 }}>
              <Descriptions size="small" column={2}>
                <Descriptions.Item label="派工單號">
                  <Tag color="blue">{dispatch.dispatch_no}</Tag>
                </Descriptions.Item>
                <Descriptions.Item label="作業類別">
                  {dispatch.work_type || '-'}
                </Descriptions.Item>
                <Descriptions.Item label="工程名稱" span={2}>
                  {dispatch.project_name || '-'}
                </Descriptions.Item>
              </Descriptions>
              <Space style={{ marginTop: 8 }}>
                <Button
                  type="link"
                  size="small"
                  onClick={() => navigate(`/taoyuan/dispatch/${dispatch.dispatch_order_id}`)}
                >
                  查看派工詳情
                </Button>
                {canEdit && isEditing && dispatch.link_id !== undefined && (
                  <Popconfirm
                    title="確定要移除此關聯嗎？"
                    onConfirm={() => {
                      if (dispatch.link_id === undefined || dispatch.link_id === null) {
                        message.error('關聯資料缺少 link_id，請重新整理頁面');
                        refetch();
                        return;
                      }
                      unlinkDispatchMutation.mutate(dispatch.link_id);
                    }}
                    okText="確定"
                    cancelText="取消"
                  >
                    <Button
                      type="link"
                      size="small"
                      danger
                      loading={unlinkDispatchMutation.isPending}
                    >
                      移除關聯
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            </Card>
          )}
        />
      ) : (
        <Empty description="此工程尚無關聯派工紀錄" image={Empty.PRESENTED_IMAGE_SIMPLE}>
          {!canEdit && (
            <Button type="link" onClick={() => navigate('/taoyuan/dispatch')}>
              返回派工管理
            </Button>
          )}
        </Empty>
      )}
    </Spin>
  );
};
