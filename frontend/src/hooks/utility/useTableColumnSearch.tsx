/**
 * 表格欄位搜尋 Hook
 *
 * 提供 Ant Design Table 欄位內搜尋功能的統一封裝
 * 支援搜尋文字高亮顯示
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import React, { useState, useRef, useCallback } from 'react';
import { Input, Button, Space } from 'antd';
import type { InputRef } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import type { ColumnType } from 'antd/es/table';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import Highlighter from 'react-highlight-words';

/**
 * 表格欄位搜尋 Hook 的回傳值型別
 */
export interface UseTableColumnSearchReturn<T> {
  /** 當前搜尋文字 */
  searchText: string;
  /** 當前被搜尋的欄位名稱 */
  searchedColumn: string;
  /** 取得欄位搜尋配置的函數 */
  getColumnSearchProps: (dataIndex: keyof T, customRender?: (text: string) => React.ReactNode) => ColumnType<T>;
  /** 重設搜尋狀態 */
  resetSearch: () => void;
}

/**
 * 表格欄位搜尋 Hook
 *
 * @example
 * ```tsx
 * const { searchText, searchedColumn, getColumnSearchProps } = useTableColumnSearch<TaoyuanProject>();
 *
 * const columns = [
 *   {
 *     title: '工程名稱',
 *     dataIndex: 'project_name',
 *     ...getColumnSearchProps('project_name'),
 *   },
 * ];
 * ```
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Record<string, any> required for Ant Design Table generic constraint
export function useTableColumnSearch<T extends Record<string, any>>(): UseTableColumnSearchReturn<T> {
  const [searchText, setSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  const handleSearch = useCallback(
    (selectedKeys: string[], confirm: () => void, dataIndex: string) => {
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
    (dataIndex: keyof T, customRender?: (text: string) => React.ReactNode): ColumnType<T> => ({
      filterDropdown: ({
        setSelectedKeys,
        selectedKeys,
        confirm,
        clearFilters,
      }: FilterDropdownProps) => (
        <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
          <Input
            ref={searchInput}
            placeholder="搜尋"
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
            >
              搜尋
            </Button>
            <Button
              onClick={() => clearFilters && handleReset(clearFilters)}
              size="small"
            >
              重設
            </Button>
          </Space>
        </div>
      ),
      filterIcon: (filtered: boolean) => (
        <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
      ),
      onFilter: (value, record) =>
        record[dataIndex]
          ?.toString()
          .toLowerCase()
          .includes((value as string).toLowerCase()) ?? false,
      filterDropdownProps: {
        onOpenChange: (visible) => {
          if (visible) {
            setTimeout(() => searchInput.current?.select(), 100);
          }
        },
      },
      render: (text) => {
        if (searchedColumn === dataIndex && searchText) {
          return (
            <Highlighter
              highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
              searchWords={[searchText]}
              autoEscape
              textToHighlight={text ? text.toString() : ''}
            />
          );
        }
        // 如果有自訂 render，使用自訂 render
        if (customRender) {
          return customRender(text);
        }
        return text;
      },
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

export default useTableColumnSearch;
