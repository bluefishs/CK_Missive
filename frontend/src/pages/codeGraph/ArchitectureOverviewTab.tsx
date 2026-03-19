import React from 'react';
import {
  Card,
  Space,
  Button,
  Alert,
  Row,
  Col,
  Statistic,
  Spin,
  Table,
  Input,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  CodeOutlined,
  DatabaseOutlined,
  SyncOutlined,
  ApartmentOutlined,
  SearchOutlined,
  DownloadOutlined,
} from '@ant-design/icons';

export interface LayerRow {
  key: string;
  layer: string;
  moduleCount: number;
  totalLines: number;
  totalFunctions: number;
  modules: Array<{
    key: string;
    name: string;
    lines: number;
    outgoing_deps: number;
    incoming_deps: number;
  }>;
}

export interface DbTableRow {
  key: string;
  name: string;
  columns: number;
  has_primary_key: boolean;
  foreign_keys: string[];
  indexes: number;
  unique_constraints: number;
}

interface ModuleOverviewSummary {
  total_modules: number;
  total_tables: number;
  total_relations: number;
}

export interface ArchitectureOverviewTabProps {
  moduleOverview: { summary: ModuleOverviewSummary } | null | undefined;
  moduleOverviewLoading: boolean;
  loadModuleOverview: () => void;
  layerTableData: LayerRow[];
  erdSearchText: string;
  setErdSearchText: (v: string) => void;
  filteredErdData: DbTableRow[];
  exportArchitectureLayers: () => void;
  exportDbErd: () => void;
}

const layerColumns: ColumnsType<LayerRow> = [
  { title: '架構層', dataIndex: 'layer', key: 'layer', width: 200 },
  { title: '模組數', dataIndex: 'moduleCount', key: 'moduleCount', width: 100, sorter: (a, b) => a.moduleCount - b.moduleCount },
  { title: '程式碼行數', dataIndex: 'totalLines', key: 'totalLines', width: 140, sorter: (a, b) => a.totalLines - b.totalLines, render: (v: number) => v.toLocaleString() },
  { title: '函數數', dataIndex: 'totalFunctions', key: 'totalFunctions', width: 100, sorter: (a, b) => a.totalFunctions - b.totalFunctions },
];

const moduleColumns: ColumnsType<LayerRow['modules'][number]> = [
  { title: '模組名稱', dataIndex: 'name', key: 'name' },
  { title: '行數', dataIndex: 'lines', key: 'lines', width: 100, sorter: (a, b) => a.lines - b.lines, render: (v: number) => v.toLocaleString() },
  { title: '出向依賴', dataIndex: 'outgoing_deps', key: 'outgoing_deps', width: 100, sorter: (a, b) => a.outgoing_deps - b.outgoing_deps },
  { title: '入向依賴', dataIndex: 'incoming_deps', key: 'incoming_deps', width: 100, sorter: (a, b) => a.incoming_deps - b.incoming_deps },
];

const erdColumns: ColumnsType<DbTableRow> = [
  { title: '資料表', dataIndex: 'name', key: 'name', width: 240, sorter: (a, b) => a.name.localeCompare(b.name) },
  { title: '欄位數', dataIndex: 'columns', key: 'columns', width: 90, sorter: (a, b) => a.columns - b.columns },
  { title: '主鍵', dataIndex: 'has_primary_key', key: 'has_primary_key', width: 70, render: (v: boolean) => (v ? '\u2713' : '\u2717'), align: 'center' },
  { title: '外鍵', dataIndex: 'foreign_keys', key: 'foreign_keys', width: 300, render: (fks: string[]) => fks.length > 0 ? fks.join(', ') : '-' },
  { title: '索引數', dataIndex: 'indexes', key: 'indexes', width: 90, sorter: (a, b) => a.indexes - b.indexes },
  { title: '唯一約束', dataIndex: 'unique_constraints', key: 'unique_constraints', width: 100, sorter: (a, b) => a.unique_constraints - b.unique_constraints },
];

const ArchitectureOverviewTab: React.FC<ArchitectureOverviewTabProps> = ({
  moduleOverview,
  moduleOverviewLoading,
  loadModuleOverview,
  layerTableData,
  erdSearchText,
  setErdSearchText,
  filteredErdData,
  exportArchitectureLayers,
  exportDbErd,
}) => {
  return (
    <div style={{ padding: 16, height: 'calc(100vh - 168px)', overflow: 'auto' }}>
      {moduleOverviewLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 200 }}>
          <Spin size="large" />
        </div>
      ) : moduleOverview ? (
        <Space vertical style={{ width: '100%' }} size={16}>
          <Row gutter={16}>
            <Col span={8}>
              <Card size="small">
                <Statistic title="總模組數" value={moduleOverview.summary.total_modules} prefix={<CodeOutlined />} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic title="資料表數" value={moduleOverview.summary.total_tables} prefix={<DatabaseOutlined />} />
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small">
                <Statistic title="關係總數" value={moduleOverview.summary.total_relations} prefix={<ApartmentOutlined />} />
              </Card>
            </Col>
          </Row>

          <Card
            title={<><ApartmentOutlined /> 架構層統計</>}
            size="small"
            extra={
              <Space size="small">
                <Button size="small" type="text" icon={<DownloadOutlined />} onClick={exportArchitectureLayers} title="匯出 Excel" />
                <Button size="small" type="text" icon={<SyncOutlined spin={moduleOverviewLoading} />} onClick={loadModuleOverview} />
              </Space>
            }
          >
            <Table<LayerRow>
              columns={layerColumns}
              dataSource={layerTableData}
              pagination={false}
              size="small"
              expandable={{
                expandedRowRender: (record) => (
                  <Table
                    columns={moduleColumns}
                    dataSource={record.modules}
                    pagination={false}
                    size="small"
                  />
                ),
                rowExpandable: (record) => record.modules.length > 0,
              }}
            />
          </Card>

          <Card
            title={<><DatabaseOutlined /> 資料庫 ERD</>}
            size="small"
            extra={
              <Space size="small">
                <Input
                  placeholder="搜尋資料表..."
                  prefix={<SearchOutlined />}
                  size="small"
                  style={{ width: 200 }}
                  value={erdSearchText}
                  onChange={(e) => setErdSearchText(e.target.value)}
                  allowClear
                />
                <Button size="small" icon={<DownloadOutlined />} onClick={exportDbErd} title="匯出 Excel" />
              </Space>
            }
          >
            <Table<DbTableRow>
              columns={erdColumns}
              dataSource={filteredErdData}
              pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 張資料表` }}
              size="small"
              scroll={{ x: 900 }}
            />
          </Card>
        </Space>
      ) : (
        <Alert type="info" title="無模組概覽資料，請先執行代碼圖譜入圖。" showIcon />
      )}
    </div>
  );
};

export default ArchitectureOverviewTab;
