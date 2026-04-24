/**
 * ADR-0032: 相容舊版 `/tender/:unitId/:jobNumber?` 格式
 *
 * 啟發式分派：
 * - 純數字 unit + 無 job → ezbid (`/tender/ezbid/:unitId`)
 * - 其他 → PCC (`/tender/pcc/:unitId/:jobNumber`)
 *
 * 2026-04-24 建立。未來若 PCC 格式完全棄用可移除此元件。
 */
import { Navigate, useParams } from 'react-router-dom';

const EZBID_ID_PATTERN = /^\d+$/;

const LegacyTenderRedirect: React.FC = () => {
  const { unitId, jobNumber } = useParams<{ unitId: string; jobNumber?: string }>();

  if (!unitId) return <Navigate to="/tender/search" replace />;

  const decodedUnit = decodeURIComponent(unitId);
  const decodedJob = jobNumber ? decodeURIComponent(jobNumber) : '';

  // 啟發式：純數字 unit 且無 job → ezbid
  if (EZBID_ID_PATTERN.test(decodedUnit) && !decodedJob) {
    return <Navigate to={`/tender/ezbid/${encodeURIComponent(decodedUnit)}`} replace />;
  }

  // 其他一律視為 PCC 複合鍵（job 可能為空也讓 PCC 頁自行處理）
  return (
    <Navigate
      to={`/tender/pcc/${encodeURIComponent(decodedUnit)}/${encodeURIComponent(decodedJob)}`}
      replace
    />
  );
};

export default LegacyTenderRedirect;
