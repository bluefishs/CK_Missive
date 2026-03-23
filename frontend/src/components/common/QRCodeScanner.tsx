/**
 * QR Code 相機掃描器元件
 *
 * 使用 html5-qrcode (免費 MIT) 啟動裝置相機即時掃描 QR Code。
 * 適用於手機拍照掃描電子發票 QR Code。
 *
 * 注意：相機存取需要 HTTPS 或 localhost（瀏覽器安全策略）。
 *
 * @version 1.0.0
 * @date 2026-03-23
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Alert, Button, Space, Flex, Typography } from 'antd';
import { CameraOutlined, SwapOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface QRCodeScannerProps {
  /** 掃描成功時回呼，參數為 QR Code 解碼後的文字 */
  onScan: (decodedText: string) => void;
  /** 掃描區域寬度 (px)，預設 300 */
  width?: number;
  /** 掃描區域高度 (px)，預設 300 */
  height?: number;
}

const QRCodeScanner: React.FC<QRCodeScannerProps> = ({
  onScan,
  width = 300,
  height = 300,
}) => {
  const scannerRef = useRef<HTMLDivElement>(null);
  const html5QrCodeRef = useRef<InstanceType<typeof import('html5-qrcode').Html5Qrcode> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const scannedRef = useRef(false);

  const startScanner = useCallback(async (facing: 'environment' | 'user') => {
    if (!scannerRef.current) return;

    try {
      const { Html5Qrcode } = await import('html5-qrcode');

      // 停止已存在的掃描器
      if (html5QrCodeRef.current) {
        try {
          await html5QrCodeRef.current.stop();
        } catch {
          // ignore
        }
        html5QrCodeRef.current.clear();
      }

      const scannerId = `qr-scanner-${Date.now()}`;
      scannerRef.current.id = scannerId;

      const scanner = new Html5Qrcode(scannerId);
      html5QrCodeRef.current = scanner;
      scannedRef.current = false;

      await scanner.start(
        { facingMode: facing },
        {
          fps: 10,
          qrbox: { width: Math.min(width - 40, 250), height: Math.min(height - 40, 250) },
        },
        (decodedText) => {
          // 防止重複觸發
          if (scannedRef.current) return;
          scannedRef.current = true;

          onScan(decodedText);

          // 掃描成功後停止
          scanner.stop().catch(() => {});
          setScanning(false);
        },
        () => {
          // QR code 未偵測到 — 忽略（持續掃描）
        },
      );

      setScanning(true);
      setError(null);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : String(err);

      if (errMsg.includes('NotAllowedError') || errMsg.includes('Permission')) {
        setError('相機權限被拒絕。請在瀏覽器設定中允許相機存取。');
      } else if (errMsg.includes('NotFoundError') || errMsg.includes('no camera')) {
        setError('未找到可用相機。');
      } else if (errMsg.includes('NotReadableError')) {
        setError('相機被其他應用程式佔用。');
      } else if (errMsg.includes('insecure') || errMsg.includes('secure context')) {
        setError('相機存取需要 HTTPS 連線。請使用 HTTPS 或 localhost 開啟此頁面。');
      } else {
        setError(`相機啟動失敗: ${errMsg}`);
      }
      setScanning(false);
    }
  }, [width, height, onScan]);

  const stopScanner = useCallback(async () => {
    if (html5QrCodeRef.current) {
      try {
        await html5QrCodeRef.current.stop();
      } catch {
        // ignore
      }
      html5QrCodeRef.current.clear();
      html5QrCodeRef.current = null;
    }
    setScanning(false);
  }, []);

  const toggleCamera = useCallback(async () => {
    const newFacing = facingMode === 'environment' ? 'user' : 'environment';
    setFacingMode(newFacing);
    await stopScanner();
    await startScanner(newFacing);
  }, [facingMode, stopScanner, startScanner]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      const scanner = html5QrCodeRef.current;
      if (scanner) {
        // isScanning 為 true 才能呼叫 stop()，否則會拋 Error
        const isRunning = scanner.getState?.() === 2; // Html5QrcodeScannerState.SCANNING
        if (isRunning) {
          scanner.stop().catch(() => {});
        }
        try { scanner.clear(); } catch { /* ignore */ }
      }
    };
  }, []);

  return (
    <div style={{ textAlign: 'center' }}>
      {error && (
        <Alert
          type="error"
          title={error}
          style={{ marginBottom: 12 }}
          closable
          onClose={() => setError(null)}
        />
      )}

      <div
        ref={scannerRef}
        style={{
          width,
          height: scanning ? height : 0,
          margin: '0 auto',
          overflow: 'hidden',
          borderRadius: 8,
        }}
      />

      <Flex vertical align="center" gap={8} style={{ marginTop: 12 }}>
        {!scanning ? (
          <Button
            type="primary"
            icon={<CameraOutlined />}
            onClick={() => startScanner(facingMode)}
            size="large"
          >
            啟動相機掃描
          </Button>
        ) : (
          <Space>
            <Button onClick={stopScanner}>停止掃描</Button>
            <Button icon={<SwapOutlined />} onClick={toggleCamera}>
              切換鏡頭
            </Button>
          </Space>
        )}
        <Text type="secondary" style={{ fontSize: 12 }}>
          將電子發票 QR Code 對準掃描框
        </Text>
      </Flex>
    </div>
  );
};

export default QRCodeScanner;
