/**
 * Agencies Page - Column definitions & search
 *
 * Extracted from AgenciesPage.tsx to reduce main file size.
 */

import { useState, useRef } from 'react';
import type { InputRef, TableColumnType } from 'antd';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import { Input, Button, Space, Tag, Typography } from 'antd';
import {
  SearchOutlined,
  BankOutlined,
  BuildOutlined,
  TeamOutlined,
  BookOutlined,
} from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import type { AgencyWithStats } from '../api';

const { Text } = Typography;

type DataIndex = keyof AgencyWithStats;

export function useAgenciesColumns(isMobile: boolean) {
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

  const getColumnSearchProps = (dataIndex: DataIndex): TableColumnType<AgencyWithStats> => ({
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
          <Button type="link" size="small" onClick={() => close()}>
            關閉
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) =>
      record[dataIndex]
        ?.toString()
        .toLowerCase()
        .includes((value as string).toLowerCase()) ?? false,
    filterDropdownProps: {
      onOpenChange(open) {
        if (open) {
          setTimeout(() => searchInput.current?.select(), 100);
        }
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
      ) : (
        text
      ),
  });

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case '政府機關': return <BankOutlined />;
      case '民間企業': return <BuildOutlined />;
      case '其他單位': return <TeamOutlined />;
      case '其他機關': return <TeamOutlined />;
      case '社會團體': return <TeamOutlined />;
      case '教育機構': return <BookOutlined />;
      default: return <TeamOutlined />;
    }
  };

  const columns: TableColumnType<AgencyWithStats>[] = isMobile
    ? [
        {
          title: '機關資訊',
          dataIndex: 'agency_name',
          key: 'agency_name',
          render: (text: string, record: AgencyWithStats) => (
            <div>
              <div style={{ fontWeight: 500 }}>{text}</div>
              {record.agency_short_name && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  簡稱: {record.agency_short_name}
                </Text>
              )}
              <div style={{ marginTop: 4 }}>
                <Tag icon={getCategoryIcon(record.category || '')} color="blue" style={{ fontSize: '11px' }}>
                  {['其他機關', '教育機構', '社會團體'].includes(record.category || '') ? '其他單位' : record.category}
                </Tag>
              </div>
            </div>
          ),
        },
      ]
    : [
        {
          title: '機關名稱',
          dataIndex: 'agency_name',
          key: 'agency_name',
          width: 280,
          sorter: (a, b) => a.agency_name.localeCompare(b.agency_name, 'zh-TW'),
          ...getColumnSearchProps('agency_name'),
          render: (text: string, record: AgencyWithStats) => (
            <div>
              <div style={{ fontWeight: 500 }}>
                {searchedColumn === 'agency_name' ? (
                  <Highlighter
                    highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
                    searchWords={[columnSearchText]}
                    autoEscape
                    textToHighlight={text || ''}
                  />
                ) : text}
              </div>
              {record.agency_short_name && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  簡稱: {record.agency_short_name}
                </Text>
              )}
            </div>
          ),
        },
        {
          title: '機關代碼',
          dataIndex: 'agency_code',
          key: 'agency_code',
          width: 120,
          align: 'center' as const,
          ...getColumnSearchProps('agency_code'),
          render: (code: string) => code || <Text type="secondary">-</Text>,
        },
        {
          title: '分類',
          dataIndex: 'category',
          key: 'category',
          width: 120,
          align: 'center' as const,
          filters: [
            { text: '政府機關', value: '政府機關' },
            { text: '民間企業', value: '民間企業' },
            { text: '其他單位', value: '其他單位' },
            { text: '其他機關', value: '其他機關' },
            { text: '教育機構', value: '教育機構' },
            { text: '社會團體', value: '社會團體' },
          ],
          onFilter: (value, record) => record.category === value,
          render: (category: string) => {
            const displayCategory = ['其他機關', '教育機構', '社會團體'].includes(category) ? '其他單位' : category;
            return (
              <Tag icon={getCategoryIcon(category)} color="blue">
                {displayCategory}
              </Tag>
            );
          },
        },
        {
          title: '建立日期',
          dataIndex: 'created_at',
          key: 'created_at',
          width: 110,
          sorter: (a, b) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime(),
          render: (date: string) =>
            date ? new Date(date).toLocaleDateString('zh-TW') : '-',
        },
      ];

  return { columns };
}
