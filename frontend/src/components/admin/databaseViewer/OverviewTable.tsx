/**
 * 表格概覽 Table
 * @description 資料庫表格列表，含展開列、排序與操作
 */
import React from 'react';
import {
  Table, Space, Typography, Row, Col,
  Card, Tag, Tooltip, Badge, Button,
} from 'antd';
import {
  TableOutlined, EyeOutlined, ApiOutlined,
  LinkOutlined, FieldTimeOutlined, FileTextOutlined,
} from '@ant-design/icons';
import type { EnhancedTableInfo } from './types';

const { Text } = Typography;

interface OverviewTableProps {
  enhancedTables: EnhancedTableInfo[];
  loading: boolean;
  showChineseNames: boolean;
  onViewDetail: (tableName: string) => void;
}

export const OverviewTable: React.FC<OverviewTableProps> = ({
  enhancedTables,
  loading,
  showChineseNames,
  onViewDetail,
}) => {
  const columns = [
    {
      title: '表格名稱',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: EnhancedTableInfo) => (
        <Space vertical size="small">
          <Space>
            <TableOutlined style={{ color: record.color }} />
            <Text strong>
              {showChineseNames ? record.chinese_name : name}
            </Text>
            <Tag color={record.color} style={{ fontSize: '12px' }}>
              {record.category}
            </Tag>
          </Space>
          {showChineseNames && name !== record.chinese_name && (
            <Text type="secondary" style={{ fontSize: '12px' }}>{name}</Text>
          )}
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.description}
          </Text>
        </Space>
      ),
      width: '35%',
    },
    {
      title: '記錄數量',
      dataIndex: 'recordCount',
      key: 'recordCount',
      render: (count: number) => (
        <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
      ),
      sorter: (a: EnhancedTableInfo, b: EnhancedTableInfo) => a.recordCount - b.recordCount,
      width: '15%',
    },
    {
      title: '前端頁面 & API',
      key: 'integration',
      render: (_: unknown, record: EnhancedTableInfo) => (
        <Space vertical size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ fontSize: '12px', color: '#1976d2' }}>
              <LinkOutlined /> 前端頁面:
            </Text>
            <div style={{ marginTop: 4 }}>
              {record.frontend_pages.length === 0 ? (
                <Text type="secondary" style={{ fontSize: '12px' }}>無對應頁面</Text>
              ) : (
                record.frontend_pages.slice(0, 2).map((page: string, index: number) => (
                  <Tag key={index} color="blue" style={{ margin: '1px 2px', fontSize: '11px' }}>
                    {page}
                  </Tag>
                ))
              )}
              {record.frontend_pages.length > 2 && (
                <Tag style={{ fontSize: '11px' }}>+{record.frontend_pages.length - 2}</Tag>
              )}
            </div>
          </div>
          <div>
            <Text strong style={{ fontSize: '12px', color: '#52c41a' }}>
              <ApiOutlined /> API 端點:
            </Text>
            <div style={{ marginTop: 4 }}>
              {record.api_endpoints.length === 0 ? (
                <Text type="secondary" style={{ fontSize: '12px' }}>無API端點</Text>
              ) : (
                record.api_endpoints.slice(0, 2).map((api: string, index: number) => (
                  <Tag key={index} color="green" style={{ margin: '1px 2px', fontSize: '11px' }}>
                    {api.split(' ')[0]} {api.split(' ')[1]?.split('/').slice(-1)[0] || '/'}
                  </Tag>
                ))
              )}
              {record.api_endpoints.length > 2 && (
                <Tag style={{ fontSize: '11px' }}>+{record.api_endpoints.length - 2}</Tag>
              )}
            </div>
          </div>
        </Space>
      ),
      width: '35%',
    },
    {
      title: '資料大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: string) => <Tag color="green">{size}</Tag>,
      width: '12%',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: EnhancedTableInfo) => (
        <Tooltip title="檢視詳細資訊">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onViewDetail(record.name)}
            aria-label="檢視詳細資訊"
          />
        </Tooltip>
      ),
      width: '8%',
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={enhancedTables}
      size="small"
      pagination={{ pageSize: 20 }}
      rowKey="name"
      loading={loading}
      scroll={{ x: 900 }}
      expandable={{
        expandedRowRender: (record) => (
          <div style={{ padding: '16px', background: '#fafafa' }}>
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <Card size="small" title="主要欄位" styles={{ header: { background: '#e6f7ff' } }}>
                  <Space wrap>
                    {record.main_fields.map((field: string, index: number) => (
                      <Tag key={index} color="cyan" style={{ margin: '2px' }}>
                        <FieldTimeOutlined style={{ marginRight: 4 }} />
                        {field}
                      </Tag>
                    ))}
                  </Space>
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="API 端點詳情" styles={{ header: { background: '#f6ffed' } }}>
                  <Space vertical size="small" style={{ width: '100%' }}>
                    {record.api_endpoints.map((api: string, index: number) => (
                      <Tag key={index} color="green" style={{ width: '100%', textAlign: 'left' }}>
                        <ApiOutlined style={{ marginRight: 4 }} />
                        {api}
                      </Tag>
                    ))}
                  </Space>
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="關聯頁面" styles={{ header: { background: '#fff7e6' } }}>
                  <Space vertical size="small" style={{ width: '100%' }}>
                    {record.frontend_pages.map((page: string, index: number) => (
                      <Tag key={index} color="blue" style={{ width: '100%', textAlign: 'left' }}>
                        <FileTextOutlined style={{ marginRight: 4 }} />
                        {page}
                      </Tag>
                    ))}
                  </Space>
                </Card>
              </Col>
            </Row>
          </div>
        ),
        rowExpandable: (record) => record.main_fields.length > 0 || record.api_endpoints.length > 0,
      }}
    />
  );
};
