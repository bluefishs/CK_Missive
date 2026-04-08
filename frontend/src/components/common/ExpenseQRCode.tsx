/**
 * 案件核銷 QR Code — 手機掃描即可開啟核銷頁面
 *
 * 用法：
 *   <ExpenseQRCode caseCode="B114-B034" />
 *   <ExpenseQRCode caseCode="B114-B034" caseName="XX 工程" compact />
 *
 * 產生的 QR Code 包含完整 URL: {origin}/erp/expenses/create?case_code=B114-B034
 * 工地人員用手機掃描即可直接進入該案件的核銷建立頁面。
 */
import React, { useRef } from 'react';
import { QRCodeCanvas } from 'qrcode.react';
import { Button, Space, Typography, Tooltip, App } from 'antd';
import { QrcodeOutlined, DownloadOutlined, CopyOutlined, PrinterOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface ExpenseQRCodeProps {
  caseCode: string;
  caseName?: string;
  /** 精簡模式 — 只顯示 QR 圖 + 下載按鈕 */
  compact?: boolean;
  /** QR 圖大小 (px)，預設 180 */
  size?: number;
}

const ExpenseQRCode: React.FC<ExpenseQRCodeProps> = ({
  caseCode, caseName, compact = false, size = 180,
}) => {
  const { message } = App.useApp();
  const canvasRef = useRef<HTMLDivElement>(null);

  const url = `${window.location.origin}/erp/expenses/create?case_code=${encodeURIComponent(caseCode)}`;

  const handleDownload = () => {
    const canvas = canvasRef.current?.querySelector('canvas');
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `核銷QR_${caseCode}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
    message.success('QR Code 已下載');
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      message.success('連結已複製');
    } catch {
      message.error('複製失敗');
    }
  };

  const handlePrint = () => {
    const canvas = canvasRef.current?.querySelector('canvas');
    if (!canvas) return;
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(`
      <html><head><title>核銷 QR — ${caseCode}</title>
      <style>body{text-align:center;font-family:sans-serif;padding:40px}
      h2{margin:0 0 8px}p{color:#666;margin:0 0 20px}img{margin:20px 0}
      .footer{margin-top:20px;font-size:12px;color:#999}</style></head>
      <body>
        <h2>${caseName || caseCode}</h2>
        <p>掃描下方 QR Code 開啟核銷頁面</p>
        <img src="${canvas.toDataURL('image/png')}" width="${size}" />
        <p style="font-size:11px;color:#aaa;word-break:break-all">${url}</p>
        <div class="footer">CK Missive 公文管理系統</div>
        <script>setTimeout(()=>window.print(),300)</script>
      </body></html>
    `);
    win.document.close();
  };

  if (compact) {
    return (
      <Tooltip title={`掃描開啟 ${caseCode} 核銷頁面`}>
        <div ref={canvasRef} style={{ display: 'inline-block', cursor: 'pointer' }} onClick={handleDownload}>
          <QRCodeCanvas value={url} size={size} level="M" includeMargin />
        </div>
      </Tooltip>
    );
  }

  return (
    <div style={{ textAlign: 'center', padding: '12px 0' }}>
      <div ref={canvasRef}>
        <QRCodeCanvas value={url} size={size} level="M" includeMargin />
      </div>
      <div style={{ margin: '8px 0' }}>
        <Text type="secondary" style={{ fontSize: 12 }}>
          掃描 QR Code 開啟 <Text strong>{caseCode}</Text> 核銷頁面
        </Text>
      </div>
      <Space>
        <Button size="small" icon={<DownloadOutlined />} onClick={handleDownload}>下載</Button>
        <Button size="small" icon={<CopyOutlined />} onClick={handleCopy}>複製連結</Button>
        <Button size="small" icon={<PrinterOutlined />} onClick={handlePrint}>列印</Button>
      </Space>
    </div>
  );
};

/** 按鈕觸發 Popover 顯示 QR Code */
export const ExpenseQRButton: React.FC<{ caseCode: string; caseName?: string }> = ({ caseCode, caseName }) => {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <Tooltip title="產生核銷 QR Code">
        <Button icon={<QrcodeOutlined />} onClick={() => setOpen(true)}>核銷 QR</Button>
      </Tooltip>
      {open && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.45)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }} onClick={() => setOpen(false)}>
          <div style={{
            backgroundColor: '#fff', borderRadius: 12, padding: 24,
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)', maxWidth: 320,
          }} onClick={(e) => e.stopPropagation()}>
            <ExpenseQRCode caseCode={caseCode} caseName={caseName} />
          </div>
        </div>
      )}
    </>
  );
};

export default ExpenseQRCode;
