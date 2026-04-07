import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
const TenderPriceAnalysisPage = () => {
  const navigate = useNavigate();
  useEffect(() => { navigate('/tender/search', { replace: true }); }, [navigate]);
  return null;
};
export default TenderPriceAnalysisPage;
