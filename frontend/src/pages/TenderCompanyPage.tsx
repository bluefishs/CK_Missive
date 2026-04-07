import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
const TenderCompanyPage = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const q = params.get('q') || '';
  useEffect(() => { navigate(`/tender/company-profile${q ? `?q=${encodeURIComponent(q)}` : ''}`, { replace: true }); }, [q, navigate]);
  return null;
};
export default TenderCompanyPage;
