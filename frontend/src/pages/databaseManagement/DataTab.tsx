import React from 'react';
import {
  Table, Button, Space, Typography, Row, Col, Card, Tag, Alert, Tooltip, Input,
} from 'antd';
import type { ColumnType } from 'antd/es/table';
import {
  TableOutlined, ReloadOutlined, DownloadOutlined, SearchOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import type { TableInfo, TableDataResponse } from '../../types/api';

const { Title } = Typography;

interface DataTabProps {
  selectedTable: string;
  tableData: TableDataResponse;
  tables: TableInfo[];
  loading: boolean;
  onFetchTableData: (tableName: string, limit?: number, offset?: number) => void;
  onExportTableData: (tableName: string) => void;
}

export const DataTab: React.FC<DataTabProps> = ({
  selectedTable,
  tableData,
  tables,
  loading,
  onFetchTableData,
  onExportTableData,
}) => {
  if (!selectedTable) {
    return <Alert title="請點擊表格名稱查看詳細數據" type="info" showIcon />;
  }

  const table = tables.find(t => t.name === selectedTable);
  if (!table) return null;

  const columns = table.columns.map(col => {
    const baseColumn: ColumnType<Record<string, unknown>> = {
      title: (
        <Space>
          {col.name}
          {col.primaryKey && <Tag color="gold" style={{ fontSize: '10px' }}>PK</Tag>}
          <Tooltip title={`${col.type}${!col.nullable ? ' (NOT NULL)' : ''}`}>
            <InfoCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
          </Tooltip>
        </Space>
      ),
      dataIndex: col.name,
      key: col.name,
      ellipsis: {
        showTitle: false,
      },
      width: col.type.includes('TEXT') ? 200 : 120,
      render: (text: unknown) => (
        <Tooltip placement="topLeft" title={String(text)}>
          {String(text)}
        </Tooltip>
      ),
    };

    if (col.type.includes('INTEGER') || col.type.includes('REAL')) {
      baseColumn.sorter = (a: Record<string, unknown>, b: Record<string, unknown>) => {
        const aVal = parseFloat(String(a[col.name])) || 0;
        const bVal = parseFloat(String(b[col.name])) || 0;
        return aVal - bVal;
      };
    } else {
      baseColumn.sorter = (a: Record<string, unknown>, b: Record<string, unknown>) => {
        const aVal = a[col.name] || '';
        const bVal = b[col.name] || '';
        return String(aVal).localeCompare(String(bVal));
      };
    }

    if (col.name === 'status' || col.name === 'doc_type' || col.name === 'category') {
      const uniqueValues = [...new Set(tableData.rows.map((row: unknown[]) => {
        const colIndex = table.columns.findIndex(c => c.name === col.name);
        return row[colIndex];
      }))].filter(Boolean);

      baseColumn.filters = uniqueValues.map(value => ({
        text: String(value),
        value: value as React.Key,
      }));

      baseColumn.onFilter = (value: React.Key | boolean, record: Record<string, unknown>) => record[col.name] === value;
    }

    if (col.type.includes('TEXT') || col.type.includes('VARCHAR')) {
      baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
        <div style={{ padding: 8 }}>
          <Input
            placeholder={`搜尋 ${col.name}`}
            value={selectedKeys[0] as string}
            onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
            onPressEnter={() => confirm()}
            style={{ marginBottom: 8, display: 'block' }}
          />
          <Space>
            <Button
              type="primary"
              onClick={() => confirm()}
              icon={<SearchOutlined />}
              size="small"
              style={{ width: 90 }}
            >
              搜尋
            </Button>
            <Button onClick={() => clearFilters?.()} size="small" style={{ width: 90 }}>
              重置
            </Button>
          </Space>
        </div>
      );
      baseColumn.filterIcon = (filtered: boolean) => (
        <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
      );
      baseColumn.onFilter = (value: React.Key | boolean, record: Record<string, unknown>) => {
        const cellValue = record[col.name];
        return cellValue ? String(cellValue).toLowerCase().includes(String(value).toLowerCase()) : false;
      };
    }

    return baseColumn;
  });

  const dataSource = tableData.rows.map((row: unknown[], index: number) => {
    const obj: Record<string, unknown> = { key: index };
    table.columns.forEach((col, colIndex) => {
      obj[col.name] = row[colIndex];
    });
    return obj;
  });

  return (
    <div>
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Title level={4} style={{ margin: 0 }}>
            <TableOutlined /> {selectedTable}
          </Title>
          <Tag color="green">{tableData.total || tableData.totalRows} 條記錄</Tag>
          <Tag color="blue">{table.columns.length} 個欄位</Tag>
        </Space>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => onFetchTableData(selectedTable)}
            loading={loading}
          >
            重新整理
          </Button>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={() => onExportTableData(selectedTable)}
          >
            匯出 CSV
          </Button>
        </Space>
      </Space>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5}>表格結構</Title>
        <Row gutter={[8, 8]}>
          {table.columns.map((col) => (
            <Col key={col.name}>
              <Tag color={col.primaryKey ? 'gold' : col.nullable ? 'default' : 'blue'}>
                {col.name}: {col.type}
                {col.primaryKey && ' (PK)'}
                {!col.nullable && !col.primaryKey && ' (NOT NULL)'}
              </Tag>
            </Col>
          ))}
        </Row>
      </Card>

      <Table
        columns={columns}
        dataSource={dataSource}
        size="small"
        scroll={{ x: 'max-content' }}
        pagination={{
          current: tableData.page,
          pageSize: tableData.pageSize || 50,
          total: tableData.total || tableData.totalRows,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => `第 ${range[0]}-${range[1]} 條，共 ${total} 條記錄`,
          onChange: (page, pageSize) => {
            const offset = (page - 1) * pageSize;
            onFetchTableData(selectedTable, pageSize, offset);
          },
          onShowSizeChange: (_current, size) => {
            onFetchTableData(selectedTable, size, 0);
          }
        }}
        loading={loading}
      />
    </div>
  );
};
