import { useState, useEffect } from 'react';

export const usePerformance = () => {
  const [performanceMetrics, setPerformanceMetrics] = useState({
    loadTime: 0,
    renderTime: 0,
  });

  useEffect(() => {
    const loadTime = window.performance.now();
    setPerformanceMetrics(prev => ({ ...prev, loadTime }));

    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      entries.forEach((entry) => {
        if (entry.entryType === 'measure') {
          setPerformanceMetrics(prev => ({
            ...prev,
            renderTime: entry.duration,
          }));
        }
      });
    });

    observer.observe({ entryTypes: ['measure'] });
    
    return () => {
      observer.disconnect();
    };
  }, []);

  return performanceMetrics;
};
