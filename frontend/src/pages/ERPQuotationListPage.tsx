/**
 * ERP 報價/成本管理列表頁面
 */
import React, { useState } from 'react';
import { Card, Button, Space, Input, Typography, Row, Col, Alert, App, Upload, Tag } from 'antd';
import { EnhancedTable } from '../components/common/EnhancedTable';
import { PlusOutlined, ReloadOutlined, DownloadOutlined, UploadOutlined, FileExcelOutlined, DollarOutlined, FundOutlined, BankOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { erpQuotationsApi } from '../api/erp';
import { useNavigate } from 'react-router-dom';
import { useERPQuotations, useERPProfitSummary, useAuthGuard } from '../hooks';
import type { ERPQuotation, ERPQuotationListParams } from '../types/erp';
import { erpQuotationStatusLabel, erpQuotationStatusColor } from '../types/erp';
import type { ResponsiveColumn } from '../components/common/EnhancedTable';
import { ROUTES } from '../router/types';
import { ClickableStatCard } from '../components/common';

const { Title } = Typography;

export const ERPQuotationListPage: React.FC = () => {
  const navigate = useNavigate();
  const { message, modal } = App.useApp();
  const { hasPermission } = useAuthGuard();
  const canWrite = hasPermission('projects:write');
  const [statFilter, setStatFilter] = useState<string | null>(null);
  const [params, setParams] = useState<ERPQuotationListParams>({ page: 1, limit: 20, sort_by: 'year', sort_order: 'desc' });
  const { data, isLoading, isError, refetch } = useERPQuotations(params);
  const { data: profitSummary } = useERPProfitSummary();
  // 2026-08-15：刪除改由詳情頁提供（對照 /documents 的導航設計），
  // 列表不再持有刪除能力，故 useDeleteERPQuotation 與 handleDelete 一併移除。

  // 前端過濾：僅顯示已承攬

  const columns: ResponsiveColumn<ERPQuotation>[] = [
    { title: '案號', key: 'project_code', width: 160, render: (_: unknown, r: ERPQuotation) => r.project_code || r.case_code },
    {
      title: '案名',
      dataIndex: 'case_name',
      key: 'case_name',
      ellipsis: true,
      render: (text: string | null) => <strong>{text ?? '-'}</strong>,
    },
    // 2026-08-19 owner：「報價單要能對應填報者」。
    //
    // `created_by` 一直存在於資料表，但**77 張全是 NULL**（端點建立時
    // 沒把使用者傳進去，08-19 已修 ⇒ 之後新建的才有），而且它只是一個
    // user id —— 就算顯示也只是個數字。後端補了 `created_by_name`，
    // 這裡才看得到人。
    //
    // 舊資料顯示「—」是誠實的：那些是修法之前建立的，系統當時沒有記錄
    // 是誰填的，寫任何名字上去都是編的。
    {
      title: '填報者',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
      width: 110,
      render: (v: string | null) => v || <span style={{ color: '#999' }}>—</span>,
    },
    // 舊案號（個人管理時期，B114-B002）—— 與紙本、回簽 PDF 檔名對得起來的那組編號
    {
      title: '舊案號',
      dataIndex: 'legacy_quotation_no',
      key: 'legacy_quotation_no',
      width: 130,
      render: (v: string | null) => v || <span style={{ color: '#999' }}>—</span>,
    },
    // 2026-08-15：補上「狀態」欄。
    // owner 回報「表格無提供篩選」—— 實測排序圖示 12 個、篩選漏斗 **0 個**。
    // 真因不是 enhanceColumns 沒生效，是**列表根本沒有狀態欄**：
    // enhanceColumns 只對 STATUS_KEYS 類欄位自動加篩選，沒有那個欄位就沒有篩選。
    // 而狀態（草稿／已確認／修訂中／已結案）是主要業務屬性，看不到本來就不合理。
    {
      title: '狀態', dataIndex: 'status', key: 'status', width: 100, align: 'center',
      render: (v?: string) => <Tag color={erpQuotationStatusColor(v)}>{erpQuotationStatusLabel(v)}</Tag>,
    },
    { title: '年度', hideOnMobile: true, dataIndex: 'year', key: 'year', width: 80, align: 'center', render: (v?: number) => v ? (v < 1911 ? v + 1911 : v) : '-' },
    {
      title: '總價',
      dataIndex: 'total_price',
      key: 'total_price',
      width: 120,
      align: 'right',
      render: (v: string | null) => v ? Number(v).toLocaleString() : '-',
    },
    {
      title: '毛利',
      hideOnMobile: true, dataIndex: 'gross_profit',
      key: 'gross_profit',
      width: 120,
      align: 'right',
      render: (v: string) => {
        const num = Number(v);
        return <span style={{ color: num >= 0 ? '#52c41a' : '#ff4d4f' }}>{num.toLocaleString()}</span>;
      },
    },
    {
      title: '毛利率',
      hideOnMobile: true, dataIndex: 'gross_margin',
      key: 'gross_margin',
      width: 90,
      align: 'right',
      render: (v: string | null) => v ? `${Number(v).toFixed(1)}%` : '-',
    },
    // 2026-08-15 移除「操作」欄（詳情／編輯／刪除）。
    // 對照 `/documents` 列表：它沒有操作欄 —— 點列進詳情，所有操作在詳情頁。
    // 這三顆在報價詳情頁本來就有，列表這一欄是重複的；
    // 而且每一顆都要 stopPropagation 才不會和點列進詳情打架，
    // 那個 stopPropagation 本身就是「這一欄不該在這裡」的訊號。
    // 點列進詳情由下方 onRow 提供。
  ];

  const grossProfit = profitSummary ? Number(profitSummary.total_gross_profit) : 0;

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col><Title level={3} style={{ margin: 0 }}>財務管理 (ERP)</Title></Col>
          <Col>
            {canWrite && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate(ROUTES.ERP_QUOTATION_CREATE)}>
                新增報價
              </Button>
            )}
          </Col>
        </Row>
        {profitSummary && (
          <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="營收總額"
                value={Number(profitSummary.total_revenue).toLocaleString()}
                icon={<DollarOutlined />}
                color="#1890ff"
                active={statFilter === 'revenue'}
                onClick={() => setStatFilter(statFilter === 'revenue' ? null : 'revenue')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="成本總額"
                value={Number(profitSummary.total_cost).toLocaleString()}
                icon={<BankOutlined />}
                color="#faad14"
                active={statFilter === 'cost'}
                onClick={() => setStatFilter(statFilter === 'cost' ? null : 'cost')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="毛利"
                value={grossProfit.toLocaleString()}
                icon={<FundOutlined />}
                color={grossProfit >= 0 ? '#3f8600' : '#cf1322'}
                active={statFilter === 'profit'}
                onClick={() => setStatFilter(statFilter === 'profit' ? null : 'profit')}
              />
            </Col>
            <Col xs={12} sm={6}>
              <ClickableStatCard
                title="應收未收"
                value={Number(profitSummary.total_outstanding).toLocaleString()}
                icon={<ExclamationCircleOutlined />}
                color="#ff4d4f"
                active={statFilter === 'outstanding'}
                onClick={() => setStatFilter(statFilter === 'outstanding' ? null : 'outstanding')}
              />
            </Col>
          </Row>
        )}
      </Card>

      {isError && <Alert type="error" message="載入失敗，請稍後重試" showIcon style={{ marginBottom: 16 }} />}

      <Card>
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="搜尋案號/案名"
            allowClear
            onSearch={(v) => setParams((p) => ({ ...p, search: v || undefined, page: 1 }))}
            style={{ width: 240 }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>重新整理</Button>
          <Button
            icon={<FileExcelOutlined />}
            onClick={async () => {
              try {
                const blob = await erpQuotationsApi.exportExcel({ year: params.year });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'erp_quotations.xlsx';
                a.click();
                URL.revokeObjectURL(url);
                message.success('匯出成功');
              } catch { message.error('匯出失敗'); }
            }}
          >匯出 Excel</Button>
          {canWrite && (
            <>
              <Upload
                accept=".xlsx,.xls"
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    const result = await erpQuotationsApi.importExcel(file);
                    message.success(`匯入完成: 新增 ${result.created} 筆, 更新 ${result.updated} 筆`);
                    if (result.errors?.length) {
                      message.warning(`${result.errors.length} 筆匯入失敗`);
                    }
                    refetch();
                  } catch { message.error('匯入失敗'); }
                  return false;
                }}
              >
                <Button icon={<UploadOutlined />}>匯入 Excel</Button>
              </Upload>
              {/* owner 2026-08-19：「若線上產出報價單未完全上線前，如何匯入與管理
                  既有 XLS 為目前階段重點」「新增與更新整合為一個按鍵鈕」。
                  依舊案號（B114-B002）upsert —— 有就更新、沒有就新增，
                  使用者不需要先知道 277 列裡哪些已在系統。
                  按下去**先預覽再確認**：這是第一次把數百筆業務資料寫進系統。 */}
              <Upload
                accept=".xlsx"
                showUploadList={false}
                beforeUpload={async (file) => {
                  try {
                    message.loading({ content: '解析中...', key: 'legacy' });
                    const p = await erpQuotationsApi.importLegacy(file, true);
                    message.destroy('legacy');
                    modal.confirm({
                      title: '匯入既有報價單彙整',
                      width: 560,
                      content: (
                        <div>
                          <p>共讀到 <b>{p.total_rows}</b> 列：</p>
                          <ul>
                            <li>將<b>新增 {p.will_create}</b> 筆</li>
                            <li>將<b>更新 {p.will_update}</b> 筆（依舊案號比對到既有資料）</li>
                            {p.skipped > 0 && <li>略過 {p.skipped} 筆（檔案內重複或缺案名）</li>}
                          </ul>
                          {(p.skipped_detail?.length ?? 0) > 0 && (
                            <Alert type="warning" showIcon message="略過明細"
                              description={p.skipped_detail!.slice(0, 5)
                                .map(x => `${x.legacy_no}：${x.reason}`).join('；')} />
                          )}
                        </div>
                      ),
                      okText: '確認寫入', cancelText: '取消',
                      onOk: async () => {
                        const r = await erpQuotationsApi.importLegacy(file, false);
                        message.success(`匯入完成：新增 ${r.created} 筆、更新 ${r.updated} 筆`);
                        refetch();
                      },
                    });
                  } catch {
                    message.destroy('legacy');
                    message.error('彙整表解析失敗');
                  }
                  return false;
                }}
              >
                <Button icon={<FileExcelOutlined />}>匯入彙整表（舊案號）</Button>
              </Upload>
              {/* owner 2026-08-19：「產生報價單只是步驟一，其需將客戶回簽檔案
                  上傳確認才正式完成邀標報價承攬」。
                  檔名就是對應關係：回簽報價單_<舊案號>_<客戶>_<標的>_<項目>.pdf
                  ⚠️ 相依：要先匯入彙整表（系統才有舊案號可比對），
                  否則會全部回報「找不到舊案號」—— 訊息會講清楚，不會靜靜跳過。 */}
              <Upload
                accept=".pdf"
                multiple
                showUploadList={false}
                beforeUpload={() => false}
                onChange={async (info) => {
                  // AntD 的 originFileObj 型別是 RcFile（File 的子型別，多了 uid），
                  // 這裡只需要當成 File 傳給 FormData
                  const files: File[] = info.fileList
                    .map((f) => f.originFileObj)
                    .filter(Boolean) as unknown as File[];
                  if (files.length !== info.fileList.length) return;
                  try {
                    message.loading({ content: '比對中...', key: 'signed' });
                    const p = await erpQuotationsApi.importSigned(files, true);
                    message.destroy('signed');
                    modal.confirm({
                      title: '匯入客戶回簽報價單',
                      width: 620,
                      content: (
                        <div>
                          <p>共 <b>{p.total_files}</b> 個檔案：</p>
                          <ul>
                            <li>可掛回 <b>{p.will_attach}</b> 份</li>
                            {p.unmatched > 0 && <li>對不上 {p.unmatched} 份</li>}
                          </ul>
                          {(p.unmatched_detail?.length ?? 0) > 0 && (
                            <Alert type="warning" showIcon message="對不上的檔案"
                              description={
                                <ul style={{ margin: 0, paddingLeft: 18 }}>
                                  {p.unmatched_detail!.slice(0, 5).map((u) => (
                                    <li key={u.file_name}>{u.file_name}：{u.reason}</li>
                                  ))}
                                </ul>
                              } />
                          )}
                        </div>
                      ),
                      okText: '確認掛回', cancelText: '取消',
                      okButtonProps: { disabled: p.will_attach === 0 },
                      onOk: async () => {
                        const r = await erpQuotationsApi.importSigned(files, false);
                        message.success(`回簽掛回完成：${r.attached} 份`);
                        refetch();
                      },
                    });
                  } catch {
                    message.destroy('signed');
                    message.error('回簽檔解析失敗');
                  }
                }}
              >
                <Button icon={<UploadOutlined />}>匯入客戶回簽</Button>
              </Upload>
              <Button
                icon={<DownloadOutlined />}
                onClick={async () => {
                  try {
                    const blob = await erpQuotationsApi.downloadTemplate();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'erp_quotation_template.xlsx';
                    a.click();
                    URL.revokeObjectURL(url);
                  } catch { message.error('下載範本失敗'); }
                }}
              >下載範本</Button>
            </>
          )}
        </Space>

        <EnhancedTable<ERPQuotation>
          columns={columns}
          dataSource={data?.items ?? []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: params.page,
            pageSize: params.limit,
            total: data?.pagination?.total ?? 0,
            onChange: (page, pageSize) => setParams((p) => ({ ...p, page, limit: pageSize })),
            showSizeChanger: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
          }}
          onRow={(record) => ({
            onClick: () => navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(record.id))),
            style: { cursor: 'pointer' },
          })}
          size="middle"
          scroll={{ x: 1000 }}
        />
      </Card>
    </ResponsiveContent>
  );
};

export default ERPQuotationListPage;
