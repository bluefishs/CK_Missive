import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
const TenderBattleRoomPage = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const uid = params.get('unit_id') || '';
  const jn = params.get('job_number') || '';
  useEffect(() => {
    if (uid && jn) navigate(`/tender/${encodeURIComponent(uid)}/${encodeURIComponent(jn)}`, { replace: true });
    else navigate('/tender/search', { replace: true });
  }, [uid, jn, navigate]);
  return null;
};
export default TenderBattleRoomPage;
