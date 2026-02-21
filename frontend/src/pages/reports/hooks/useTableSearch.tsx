/**
 * 報表表格搜尋篩選 Hook
 *
 * 提供標準化的表格欄位搜尋功能，參照 /documents 頁面規範。
 * 支援：搜尋輸入框、篩選圖示、高亮顯示。
 *
 * @version 1.0.0
 * @date 2026-02-02
 */

import { useRef, useState, useCallback } from 'react';
import { Input, Button, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { InputRef } from 'antd';
import type { ColumnType } from 'antd/es/table';
import type { FilterConfirmProps } from 'antd/es/table/interface';
import Highlighter from 'react-highlight-words';

export interface UseTableSearchReturn<T> {
  searchText: string;
  searchedColumn: string;
  getColumnSearchProps: (dataIndex: keyof T, title: string) => Partial<ColumnType<T>>;
  resetSearch: () => void;
}

export function useTableSearch<T>(): UseTableSearchReturn<T> {
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  const handleSearch = useCallback(
    (selectedKeys: string[], confirm: (param?: FilterConfirmProps) => void, dataIndex: string) => {
      confirm();
      setSearchText(selectedKeys[0] || '');
      setSearchedColumn(dataIndex);
    },
    []
  );

  const handleReset = useCallback((clearFilters: () => void) => {
    clearFilters();
    setSearchText('');
  }, []);

  const resetSearch = useCallback(() => {
    setSearchText('');
    setSearchedColumn('');
  }, []);

  const getColumnSearchProps = useCallback(
    (dataIndex: keyof T, title: string): Partial<ColumnType<T>> => ({
      filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
        <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
          <Input
            ref={searchInput}
            placeholder={`搜尋${title}`}
            value={selectedKeys[0]}
            onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
            onPressEnter={() => handleSearch(selectedKeys as string[], confirm, dataIndex as string)}
            style={{ marginBottom: 8, display: 'block' }}
          />
          <Space>
            <Button
              type="primary"
              onClick={() => handleSearch(selectedKeys as string[], confirm, dataIndex as string)}
              icon={<SearchOutlined />}
              size="small"
              style={{ width: 90 }}
            >
              搜尋
            </Button>
            <Button
              onClick={() => clearFilters && handleReset(clearFilters)}
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
      onFilter: (value, record) => {
        const fieldValue = record[dataIndex];
        if (fieldValue === null || fieldValue === undefined) return false;
        return String(fieldValue).toLowerCase().includes((value as string).toLowerCase());
      },
      filterDropdownProps: {
        onOpenChange(open: boolean) {
          if (open) {
            setTimeout(() => searchInput.current?.select(), 100);
          }
        },
      },
      render: (text: unknown) =>
        searchedColumn === dataIndex ? (
          <Highlighter
            highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
            searchWords={[searchText]}
            autoEscape
            textToHighlight={text ? String(text) : ''}
          />
        ) : (
          String(text ?? '')
        ),
    }),
    [handleSearch, handleReset, searchText, searchedColumn]
  );

  return {
    searchText,
    searchedColumn,
    getColumnSearchProps,
    resetSearch,
  };
}
