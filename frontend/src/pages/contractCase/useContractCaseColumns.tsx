/**
 * ContractCasePage 表格欄位定義 + 欄位搜尋
 *
 * 提供列表視圖的 columns 定義與欄位搜尋功能
 *
 * @version 1.0.0
 * @date 2026-03-18
 */

import { useRef, useState, useMemo } from 'react';
import type { InputRef, TableColumnType } from 'antd';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import { Button, Input, Space, Tag } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import dayjs from 'dayjs';
import type { Project } from '../../types/api';
import {
  CATEGORY_OPTIONS,
  normalizeCategory,
  getCategoryTagColor,
  getCategoryTagText,
  getStatusColor,
  getStatusLabel,
} from './contractCaseConstants';

type DataIndex = keyof Project;

export function useContractCaseColumns(
  availableYears: number[],
  availableStatuses: string[],
) {
  const [columnSearchText, setColumnSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  const handleColumnSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: DataIndex,
  ) => {
    confirm();
    setColumnSearchText(selectedKeys[0] ?? '');
    setSearchedColumn(dataIndex);
  };

  const handleColumnReset = (clearFilters: () => void) => {
    clearFilters();
    setColumnSearchText('');
  };

  const getColumnSearchProps = (dataIndex: DataIndex): TableColumnType<Project> => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          ref={searchInput}
          placeholder={`搜尋...`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            搜尋
          </Button>
          <Button
            onClick={() => clearFilters && handleColumnReset(clearFilters)}
            size="small"
            style={{ width: 90 }}
          >
            重置
          </Button>
          <Button type="link" size="small" onClick={() => close()}>關閉</Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) =>
      record[dataIndex]?.toString().toLowerCase().includes((value as string).toLowerCase()) ?? false,
    filterDropdownProps: {
      onOpenChange(open) {
        if (open) setTimeout(() => searchInput.current?.select(), 100);
      },
    },
    render: (text) =>
      searchedColumn === dataIndex ? (
        <Highlighter
          highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
          searchWords={[columnSearchText]}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      ) : text,
  });

  const columns: TableColumnType<Project>[] = useMemo(() => [
    {
      title: '成案編號',
      dataIndex: 'project_code',
      key: 'project_code',
      width: 100,
      sorter: (a, b) => (a.project_code || '').localeCompare(b.project_code || ''),
      ...getColumnSearchProps('project_code'),
      render: (text) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {searchedColumn === 'project_code' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[columnSearchText]}
              autoEscape
              textToHighlight={text || '-'}
            />
          ) : (text || '-')}
        </span>
      ),
    },
    {
      title: '案件年度',
      dataIndex: 'year',
      key: 'year',
      width: 80,
      align: 'center',
      sorter: (a, b) => (a.year || 0) - (b.year || 0),
      defaultSortOrder: 'descend',
      filters: availableYears.map(y => ({ text: `${y}年`, value: y })),
      onFilter: (value, record) => record.year === value,
    },
    {
      title: '專案名稱',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 260,
      ellipsis: true,
      sorter: (a, b) => a.project_name.localeCompare(b.project_name, 'zh-TW'),
      ...getColumnSearchProps('project_name'),
      render: (text) => (
        <strong>
          {searchedColumn === 'project_name' ? (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[columnSearchText]}
              autoEscape
              textToHighlight={text || ''}
            />
          ) : text}
        </strong>
      ),
    },
    {
      title: '委託單位',
      dataIndex: 'client_agency',
      key: 'client_agency',
      width: 160,
      ellipsis: true,
      sorter: (a, b) => (a.client_agency || '').localeCompare(b.client_agency || '', 'zh-TW'),
      ...getColumnSearchProps('client_agency'),
    },
    {
      title: '案件類別',
      dataIndex: 'category',
      key: 'category',
      width: 90,
      align: 'center',
      filters: CATEGORY_OPTIONS.map(c => ({ text: c.label, value: c.value })),
      onFilter: (value, record) => normalizeCategory(record.category) === value,
      render: (category) => (
        <Tag color={getCategoryTagColor(category)}>
          {getCategoryTagText(category)}
        </Tag>
      ),
    },
    {
      title: '案件狀態',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      align: 'center',
      filters: availableStatuses.map(s => ({ text: getStatusLabel(s), value: s })),
      onFilter: (value, record) => record.status === value,
      render: (status) => <Tag color={getStatusColor(status)}>{getStatusLabel(status)}</Tag>,
    },
    {
      title: '契約期程',
      key: 'contract_period',
      width: 120,
      render: (_, record) => {
        const startDate = record.start_date ? dayjs(record.start_date).format('YYYY/MM/DD') : '';
        const endDate = record.end_date ? dayjs(record.end_date).format('YYYY/MM/DD') : '';
        if (!startDate && !endDate) return '-';
        return `${startDate || '未定'}~${endDate || '未定'}`;
      },
    },
    {
      title: '建案案號',
      dataIndex: 'case_code',
      key: 'case_code',
      width: 120,
      render: (code) => code ? <Tag color="blue">{code}</Tag> : '-',
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [availableYears, availableStatuses, columnSearchText, searchedColumn]);

  return { columns };
}
