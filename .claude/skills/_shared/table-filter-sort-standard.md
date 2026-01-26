# 表格篩選排序設計規範

> **版本**: 1.0.0
> **更新日期**: 2026-01-21
> **適用範圍**: 所有資料列表表格

---

## 設計原則

遵循 [Ant Design Table 最佳實踐](https://ant.design/components/table)，所有資料表格應具備：

1. **欄位篩選** - 使用 `filters` 和 `onFilter` 屬性
2. **欄位排序** - 使用 `sorter` 屬性
3. **搜尋功能** - 使用 `filterDropdown` 自定義搜尋

---

## 標準實作模式

### 1. 基本篩選排序欄位

```typescript
import type { ColumnsType, ColumnType } from 'antd/es/table';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';

const columns: ColumnsType<DataType> = [
  {
    title: '名稱',
    dataIndex: 'name',
    key: 'name',
    // 排序
    sorter: (a, b) => a.name.localeCompare(b.name),
    sortDirections: ['ascend', 'descend'],
    // 篩選
    filters: [
      { text: '選項A', value: 'A' },
      { text: '選項B', value: 'B' },
    ],
    onFilter: (value, record) => record.name.includes(value as string),
  },
];
```

### 2. 搜尋型篩選（推薦用於文字欄位）

```typescript
import { SearchOutlined } from '@ant-design/icons';
import { Input, Button, Space } from 'antd';
import type { InputRef } from 'antd';
import Highlighter from 'react-highlight-words';

// 搜尋狀態
const [searchText, setSearchText] = useState('');
const [searchedColumn, setSearchedColumn] = useState('');
const searchInput = useRef<InputRef>(null);

// 搜尋處理
const handleSearch = (
  selectedKeys: string[],
  confirm: () => void,
  dataIndex: string,
) => {
  confirm();
  setSearchText(selectedKeys[0]);
  setSearchedColumn(dataIndex);
};

const handleReset = (clearFilters: () => void) => {
  clearFilters();
  setSearchText('');
};

// 取得欄位搜尋配置
const getColumnSearchProps = (dataIndex: string): ColumnType<DataType> => ({
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
      <Input
        ref={searchInput}
        placeholder={`搜尋 ${dataIndex}`}
        value={selectedKeys[0]}
        onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
        onPressEnter={() => handleSearch(selectedKeys as string[], confirm, dataIndex)}
        style={{ marginBottom: 8, display: 'block' }}
      />
      <Space>
        <Button
          type="primary"
          onClick={() => handleSearch(selectedKeys as string[], confirm, dataIndex)}
          icon={<SearchOutlined />}
          size="small"
        >
          搜尋
        </Button>
        <Button onClick={() => clearFilters && handleReset(clearFilters)} size="small">
          重設
        </Button>
      </Space>
    </div>
  ),
  filterIcon: (filtered: boolean) => (
    <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
  ),
  onFilter: (value, record) =>
    record[dataIndex]?.toString().toLowerCase().includes((value as string).toLowerCase()),
  onFilterDropdownOpenChange: (visible) => {
    if (visible) {
      setTimeout(() => searchInput.current?.select(), 100);
    }
  },
  render: (text) =>
    searchedColumn === dataIndex ? (
      <Highlighter
        highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
        searchWords={[searchText]}
        autoEscape
        textToHighlight={text ? text.toString() : ''}
      />
    ) : (
      text
    ),
});
```

### 3. 日期範圍篩選

```typescript
import { DatePicker } from 'antd';
import dayjs from 'dayjs';

const getDateRangeFilterProps = (dataIndex: string): ColumnType<DataType> => ({
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }}>
      <DatePicker.RangePicker
        value={selectedKeys[0] as any}
        onChange={(dates) => setSelectedKeys(dates ? [dates] : [])}
        style={{ marginBottom: 8 }}
      />
      <div>
        <Button type="primary" onClick={() => confirm()} size="small" style={{ marginRight: 8 }}>
          確定
        </Button>
        <Button onClick={() => clearFilters?.()} size="small">
          重設
        </Button>
      </div>
    </div>
  ),
  onFilter: (value, record) => {
    const [start, end] = value as [dayjs.Dayjs, dayjs.Dayjs];
    const date = dayjs(record[dataIndex]);
    return date.isAfter(start) && date.isBefore(end);
  },
});
```

---

## 桃園派工頁面適用欄位

### TaoyuanDispatchPage - 派工單列表

| 欄位 | 篩選類型 | 排序 |
|------|---------|------|
| dispatch_no (派工單號) | 搜尋 | ✓ |
| project_name (工程名稱) | 搜尋 | ✓ |
| work_type (作業類別) | 下拉篩選 | - |
| case_handler (案件承辦) | 下拉篩選 | ✓ |
| survey_unit (查估單位) | 下拉篩選 | - |
| deadline (履約期限) | 日期範圍 | ✓ |
| created_at (建立時間) | 日期範圍 | ✓ |

### TaoyuanDispatchPage - 工程列表

| 欄位 | 篩選類型 | 排序 |
|------|---------|------|
| project_name (工程名稱) | 搜尋 | ✓ |
| district (行政區) | 下拉篩選 | ✓ |
| case_type (案件類型) | 下拉篩選 | - |
| case_handler (案件承辦) | 下拉篩選 | ✓ |
| review_year (審議年度) | 下拉篩選 | ✓ |
| created_at (建立時間) | 日期範圍 | ✓ |

---

## 受控表格狀態管理

```typescript
// 表格狀態
const [tableParams, setTableParams] = useState<{
  pagination: TablePaginationConfig;
  sortField?: string;
  sortOrder?: 'ascend' | 'descend';
  filters?: Record<string, FilterValue | null>;
}>({
  pagination: { current: 1, pageSize: 20 },
});

// 表格變更處理
const handleTableChange = (
  pagination: TablePaginationConfig,
  filters: Record<string, FilterValue | null>,
  sorter: SorterResult<DataType> | SorterResult<DataType>[],
) => {
  setTableParams({
    pagination,
    filters,
    sortField: (sorter as SorterResult<DataType>).field as string,
    sortOrder: (sorter as SorterResult<DataType>).order,
  });
};

// 表格元件
<Table
  columns={columns}
  dataSource={data}
  pagination={tableParams.pagination}
  onChange={handleTableChange}
/>
```

---

## 必須遵守事項

1. **所有列表表格必須支援**：
   - 至少一個可排序欄位
   - 主要欄位的搜尋或篩選功能

2. **使用者體驗**：
   - 篩選/排序狀態應可重設
   - 篩選圖示應顯示啟用狀態
   - 搜尋應支援即時篩選

3. **效能考量**：
   - 大量資料使用後端分頁排序
   - 前端篩選僅用於小型資料集 (<500筆)

---

*規範維護: Claude Code Assistant*
