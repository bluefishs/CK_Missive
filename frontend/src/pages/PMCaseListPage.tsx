/**
 * 邀標/報價管理列表頁面
 *
 * 建案階段：邀標登錄、報價上傳、決標追蹤。
 * 成案後自動帶入 Contract Cases 與 ERP Quotations。
 *
 * @version 3.0.0 — 重新定位為邀標/報價專區
 */
import React, { useState, useMemo } from 'react';
import { FilterBar } from '../components/common/FilterBar';
import { MobileCard } from '../components/common/MobileCardList';
import { fmtMoney } from '../utils/money';
import { Typography, Input, Button, Flex, Row, Col, Tag, Select, Upload, App, Space } from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import { PlusOutlined, ReloadOutlined, FileSearchOutlined, CheckCircleOutlined, DollarOutlined, SendOutlined, DownloadOutlined, UploadOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { usePMCases, usePMCaseSummary, useAuthGuard, useResponsive } from '../hooks';
import { ClickableStatCard } from '../components/common';
import { formatPMCategory, PM_CATEGORY_OPTIONS } from '../types/pm';
import type { PMCase } from '../types/api';
import { PM_CASE_STATUS_LABELS } from '../types/pm';
import type { PMCaseStatus } from '../types/pm';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { apiClient } from '../api/client';
import { PM_ENDPOINTS } from '../api/endpoints';

const { Title } = Typography;
const { Search } = Input;

export const PMCaseListPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const { isMobile } = useResponsive();
  const { message } = App.useApp();

  const [searchText, setSearchText] = useState('');
  const [yearFilter, setYearFilter] = useState<number | undefined>(new Date().getFullYear());
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  /**
   * 是否納入**已成案**的案件（已承攬且有成案編號）。預設 false。
   *
   * owner 2026-08-31：「已承攬案件應由 /pm/cases 移轉至 /contract-cases 列管，
   * 不應該兩邊皆有紀錄。」實測兩邊皆有的精確是 136 筆，且它們在
   * `contract_projects` 全部對得上 case_code。
   *
   * ⚠️ 條件是「已承攬**且**有成案編號」，不是「已承攬」——
   * 227 件已承攬裡有 91 件還沒成案（`contract_projects` 裡也沒有），
   * 只看狀態會讓那 91 件從兩邊都消失。
   *
   * 開關留著而不是寫死：邀標階段的報價紀錄還掛在這些案件上，
   * 偶爾要回頭查。**預設不顯示＝不列管；要查得到＝不是列管。**
   */
  // 2026-09-04 owner：「含已成案」開關移除——已成案的家在 /contract-cases，這頁固定只看未成案（評估中／已結案）。
  const includeConverted = false;
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  /**
   * 表頭排序 —— **交給後端做**（2026-08-31）。
   *
   * 這一頁是伺服器分頁，前端比較器只看得到當前這 20 筆；
   * 「依案號排序」實際上只排了眼前這一頁，而畫面上完全看不出來。
   * 欄位標 `sorter: true` 只是宣告「這一欄可排」，實際排序由 `sort_by`
   * 送進 API（後端只接受真正對應到欄位的名稱，見 `repositories/sort_utils.py`）。
   */
  const [sort, setSort] = useState<{ field: string; order: 'asc' | 'desc' }>({
    field: 'year',
    order: 'desc',
  });

  // 匯出 XLSX
  const handleExportXlsx = async () => {
    try {
      message.loading({ content: '匯出中...', key: 'export' });
// ⚠️ 這裡原本用**裸 `fetch`** 打 `/api/...`：不經 apiClient 就不會帶上
      // 認證 cookie 與 X-CSRF-Token，於是這個功能一直是壞的
      // （owner 2026-08-19 回報「匯出 XLS 無法運作」）。
      // 同型掃全共 4 處：PM 案件匯出/匯入、里程碑匯出/匯入 —— 一併改用 apiClient。
      // 路徑也改用端點常數，不再硬編字串。
      const res = await apiClient.post(PM_ENDPOINTS.EXPORT_XLSX, {}, { responseType: 'blob' });
      const raw = res as unknown as { data?: Blob } | Blob;
      const blob = raw instanceof Blob ? raw : (raw.data as Blob);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pm_cases_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      message.success({ content: '匯出成功', key: 'export' });
    } catch {
      message.error({ content: '匯出失敗', key: 'export' });
    }
  };

  // 匯入 XLSX 修正 — 上傳到後端解析
  const handleImportXlsx = async (file: File) => {
    try {
      message.loading({ content: '匯入中...', key: 'import' });
      const formData = new FormData();
      formData.append('file', file);
      // 同上：裸 fetch 不帶認證，改走 apiClient
      // 匯入回應的形狀（後端 pm/cases/import-xlsx）
      type ImportResult = {
        success?: boolean; updated?: number; synced?: number; errors?: string[]; error?: string;
      };
      const res = await apiClient.post(PM_ENDPOINTS.IMPORT_XLSX, formData);
      const result = ((res as unknown as { data?: ImportResult })?.data
        ?? (res as unknown as ImportResult));

      if (result.success) {
        message.success({
          content: `匯入完成: 更新 ${result.updated} 筆, 同步 ${result.synced} 筆${result.errors?.length ? `, 錯誤 ${result.errors.length} 筆` : ''}`,
          key: 'import',
          duration: 5,
        });
        window.location.reload();
      } else {
        message.error({ content: result.error || '匯入失敗', key: 'import' });
      }
    } catch {
      message.error({ content: '匯入失敗，請確認 XLSX 格式正確', key: 'import' });
    }
    return false;
  };

  const queryParams = useMemo(() => ({
    page: currentPage,
    limit: pageSize,
    sort_by: sort.field,
    sort_order: sort.order,
    ...(searchText && { search: searchText }),
    ...(yearFilter !== undefined && { year: yearFilter }),
    ...(statusFilter && { status: statusFilter }),
    ...(categoryFilter && { category: categoryFilter }),
    include_converted: includeConverted,
  }), [currentPage, searchText, yearFilter, statusFilter, categoryFilter, sort, includeConverted]);

  const { data: casesData, isLoading, refetch } = usePMCases(queryParams);
  // 2026-09-04 owner：報價總額跟著目前點選的狀態卡／類別動態調整；各卡計數不跟（分母）。
  const { data: summary } = usePMCaseSummary({
    year: yearFilter, include_converted: includeConverted,
    status: statusFilter, category: categoryFilter,
  });

  // PaginatedResponse<PMCase> has .items and .pagination directly
  const cases = casesData?.items ?? [];
  const total = casesData?.pagination?.total ?? 0;

  const desktopColumns: ColumnsType<PMCase> = [
    {
      title: '案號',
      dataIndex: 'case_code',
      key: 'case_code',
      sorter: true,
      width: 140,
      render: (code: string) => <Typography.Text strong style={{ fontFamily: 'monospace', fontSize: 12 }}>{code}</Typography.Text>,
    },
    {
      title: '專案名稱',
      dataIndex: 'case_name',
      key: 'case_name',
      sorter: true,
      ellipsis: true,
    },
    {
      title: '委託單位',
      dataIndex: 'client_name',
      key: 'client_name',
      sorter: true,
      width: 150,
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '計畫類別',
      dataIndex: 'category',
      key: 'category',
      sorter: true,
      // 顯示代碼＋名稱（`02承攬報價`）—— owner 2026-08-31：「應顯示完整資訊」。
      // 寬度要放得下 6 個中文字＋排序箭頭，否則標題會被折成「計畫類 別」。
      width: 130,
      render: (cat: string) => formatPMCategory(cat),
    },
    {
      title: '報價金額',
      dataIndex: 'contract_amount',
      key: 'contract_amount',
      sorter: true,
      width: 120,
      align: 'right' as const,
      render: (v: number) => v ? `NT$${v.toLocaleString()}` : '-',
    },
    {
      title: '承攬狀態',
      dataIndex: 'status',
      key: 'contract_status',
      sorter: true,
      // 「已承攬・未成案」是 7 個字，96px 放不下 ⇒ 被截成「已承攬・」而看不出未成案
      //（owner 2026-08-31 回報）。這一欄的兩種值差別就在後三個字，不能截。
      width: 150,
      align: 'center' as const,
      // 2026-08-31：移除表頭的前端篩選。這一頁是伺服器分頁，
      // `onFilter` 只作用於當前這一頁 ⇒ 選了「已結案」而本頁沒有 ⇒ 整頁空白。
      // 工具列的「承攬狀態」下拉才是對的入口（它把 status 送進查詢參數）。
      render: (status: string, record: PMCase) => {
        if (status === 'contracted') {
          // 2026-08-29（M3）：「已承攬未成案」與「已承攬已成案」在列表上
          // 原本無法區分 —— 而這個缺口存量 114 筆（91 待判讀＋23 可成案），
          // 使用者只能逐筆點進詳情頁看 project_code 有無。
          return record.project_code
            ? <Tag color="blue">已承攬</Tag>
            : <Tag color="gold">已承攬・未成案</Tag>;
        }
        if (status === 'closed') return <Tag color="success">已結案</Tag>;
        return <Tag color="default">評估中</Tag>;
      },
    },
    {
      title: '成案編號',
      dataIndex: 'project_code',
      key: 'project_code',
      sorter: true,
      width: 130,
      // 已成案者列管在 /contract-cases —— 這裡給一條路過去，
      // 否則「移轉列管」對使用者就只是「東西不見了」。
      render: (code: string) => code
        ? (
          <Typography.Link
            style={{ fontFamily: 'monospace', fontSize: 12 }}
            onClick={(e) => { e.stopPropagation(); navigate(`${ROUTES.CONTRACT_CASES}?search=${encodeURIComponent(code)}`); }}
          >
            {code}
          </Typography.Link>
        )
        : <Typography.Text type="secondary">-</Typography.Text>,
    },
  ];

  // Mobile: 案號、專案名稱、是否承攬
  const mobileColumns: ColumnsType<PMCase> = [
    desktopColumns[0]!, // 案號
    desktopColumns[1]!, // 專案名稱
    desktopColumns[5]!, // 是否承攬
  ];

  const columns = isMobile ? mobileColumns : desktopColumns;

  return (
    <ResponsiveContent>
      <Flex vertical gap={8} style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}><FileSearchOutlined style={{ marginRight: 8 }} />邀標/報價管理</Title>
          </Col>
          <Col>
            <Space wrap>  {/* 2026-09-05：手機 390px 溢出 84px 的來源——四顆按鈕不換行 */}
              <Button
                icon={<DownloadOutlined />}
                onClick={handleExportXlsx}
              >
                匯出 XLSX
              </Button>
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={handleImportXlsx}
              >
                <Button icon={<UploadOutlined />}>匯入修正</Button>
              </Upload>
              {/* 2026-08-27：`projects:write` 不存在於任何地方（見 useAuthGuard 的 Permission 註解），
                  只有 superuser 看得到這個按鈕。後端 pm/cases 只有 require_auth ⇒
                  改成 projects:edit 不放寬任何 API 存取，只是停止隱藏入口。 */}
              {/* 2026-08-28 owner：「新增報價在右上角獨立按鈕，非在各案件內」＋
                  「create 仍是 mis 非 xls 樣板」——
                  範本式一頁建單（案首＋明細＋合計）：送出時自動建立邀標案件
                  （委託單位寫進 pm_cases.client_name，輸出文件才有客戶抬頭），
                  完成後直達該案件的報價單分頁（明細編輯＋輸出 PDF 都在那裡）。 */}
              {hasPermission('projects:edit') && (
                <Button
                  icon={<FileTextOutlined />}
                  onClick={() => navigate(ROUTES.ERP_QUOTATION_CREATE)}
                >
                  新增報價
                </Button>
              )}
              {hasPermission('projects:edit') && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => navigate(ROUTES.PM_CASE_CREATE)}
                >
                  新增邀標
                </Button>
              )}
            </Space>
          </Col>
        </Row>

        {summary && (
          <Row gutter={[16, 16]}>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="邀標總數"
                value={summary.total_cases}
                icon={<FileSearchOutlined />}
                active={!statusFilter}
                onClick={() => { setStatusFilter(undefined); setCurrentPage(1); }}
              />
            </Col>
            {/* 2026-08-19：標籤與取值原本對不起來 ——
                「報價中」讀的是 `in_progress`，而 PM 案件根本沒有這個狀態
                （SSOT 只有 planning/contracted/closed）⇒ 這張卡恆為 0；
                「已成案」讀的是 `closed`（已結案），於是後端回的
                `contracted: 2` 完全沒有地方顯示，畫面說「已成案 1」
                而列表列著 2 筆「已承攬」。改為直接由 SSOT 推導，
                標籤、取值、列表用同一組詞彙。 */}
            {/* 2026-09-04 owner：已承攬的案件會進 /contract-cases，這頁的統計卡改看「評估中」
                （列表預設也不含已成案，卡片與列表才是同一個分母）。 */}
            {(['planning', 'closed'] as PMCaseStatus[]).map((st) => (
              <Col xs={12} sm={6} key={st}>
                <ClickableStatCard
                  title={PM_CASE_STATUS_LABELS[st]}
                  value={summary.by_status?.[st] ?? 0}
                  icon={st === 'planning' ? <SendOutlined /> : <CheckCircleOutlined />}
                  color={st === 'planning' ? '#faad14' : '#52c41a'}
                  active={statusFilter === st}
                  onClick={() => {
                    setStatusFilter(statusFilter === st ? undefined : st);
                    setCurrentPage(1);
                  }}
                />
              </Col>
            ))}
            <Col xs={12} sm={6}>
              {/* 金額不是狀態，點它沒有對應的篩選語意 —— 不給 onClick，
                  元件就不會 hoverable（原本點了只會變色，列表不動）。 */}
              <ClickableStatCard
                title={`報價總額${statusFilter ? `（${PM_CASE_STATUS_LABELS[statusFilter as PMCaseStatus] ?? statusFilter}）` : ''}${categoryFilter ? `・${categoryFilter}` : ''}`}
                value={`NT$${Number(summary.total_contract_amount ?? 0).toLocaleString()}`}
                icon={<DollarOutlined />}
              />
            </Col>
          </Row>
        )}

        {/* 2026-09-05 owner：篩選列手機可收合——搜尋框常駐，年度／狀態／類別收進「篩選」鈕 */}
        <FilterBar
          summary={(
            <Search
                          placeholder="搜尋案號/案名..."
                          allowClear
                          onSearch={(v) => {
                            setSearchText(v);
                            setCurrentPage(1);
                          }}
                        />
          )}
          activeCount={[yearFilter, statusFilter, categoryFilter].filter(Boolean).length}
        >
          <Row gutter={[8, 8]} style={{ width: '100%' }}>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="年度"
              allowClear
              value={yearFilter}
              onChange={(v) => {
                setYearFilter(v);
                setCurrentPage(1);
              }}
              options={Array.from({ length: 5 }, (_, i) => {
                const y = new Date().getFullYear() - i;
                return { value: y, label: String(y) };
              })}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="承攬狀態"
              allowClear
              value={statusFilter}
              onChange={(v) => {
                setStatusFilter(v);
                setCurrentPage(1);
              }}
              options={[
                { value: 'planning', label: '評估中' },
                { value: 'contracted', label: '已承攬' },
                { value: 'closed', label: '已結案' },
              ]}
            />
          </Col>
          <Col xs={8} sm={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="類別"
              allowClear
              value={categoryFilter}
              onChange={(v) => {
                setCategoryFilter(v);
                setCurrentPage(1);
              }}
              options={PM_CATEGORY_OPTIONS}
            />
          </Col>
          {/* 2026-09-04 owner：原本這裡有「含已成案」開關（08-31 留的），已成案的家在 /contract-cases，這頁固定不列，開關移除。 */}
          <Col>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
          </Col>
        </Row>
        </FilterBar>

        <EnhancedTable<PMCase>
          dataSource={cases}
          columns={columns}
          rowKey="id"
          // 2026-09-05 RWD：手機改卡片
          mobileCard={(r) => (
            <MobileCard
              title={<>{r.case_code}{r.year ? <Typography.Text type="secondary" style={{ marginInlineStart: 6 }}>{r.year}</Typography.Text> : null}</>}
              subtitle={r.case_name}
              tags={[{ text: PM_CASE_STATUS_LABELS[r.status] ?? r.status, color: r.status === 'contracted' ? 'green' : r.status === 'closed' ? 'default' : 'blue' }]}
              rows={[{ label: '委託單位', value: r.client_name }, { label: '類別', value: r.category }]}
              amounts={[{ label: '合約金額（含稅）', value: fmtMoney(r.contract_amount) }]}
              onClick={() => navigate(ROUTES.PM_CASE_DETAIL.replace(':id', String(r.id)))}
            />
          )}
          loading={isLoading}
          pagination={{
            current: currentPage,
            pageSize,
            total,
            onChange: setCurrentPage,
            showSizeChanger: false,
            showTotal: (t) => `共 ${t} 筆`,
          }}
          // 表頭排序轉成 API 參數（2026-08-31）。取消排序時回到預設的年度新→舊，
          // 不留空 —— `sort_by` 空字串在後端會退回 `id`，那不是使用者要的順序。
          onChange={(_pagination, _filters, sorter) => {
            const s = Array.isArray(sorter) ? sorter[0] : sorter;
            const field = typeof s?.field === 'string' ? s.field : undefined;
            if (!field || !s?.order) {
              setSort({ field: 'year', order: 'desc' });
            } else {
              setSort({ field, order: s.order === 'ascend' ? 'asc' : 'desc' });
            }
            setCurrentPage(1);
          }}
          onRow={(record) => ({
            onClick: () => navigate(`/pm/cases/${record.id}`),
            style: { cursor: 'pointer' },
          })}
          size={isMobile ? 'small' : 'middle'}
          scroll={{ x: 800 }}
        />
      </Flex>
    </ResponsiveContent>
  );
};

export default PMCaseListPage;
