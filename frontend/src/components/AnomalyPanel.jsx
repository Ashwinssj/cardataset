import React, { useState, useEffect } from 'react';
import { AlertTriangle, Activity } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const AnomalyPanel = ({ timeSpan, selectedDate, refreshKey }) => {
  const [anomalies, setAnomalies] = useState([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuth();

  useEffect(() => {
    const fetchAnomalies = async () => {
      setLoading(true);
      try {
        let url = `http://localhost:8080/api/anomalies/?group_by=${timeSpan.toLowerCase()}`;
        if (selectedDate) url += `&date=${selectedDate}`;
        const res = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await res.json();
        setAnomalies(data);
      } catch (err) {
        console.error("Error fetching anomalies:", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) {
      fetchAnomalies();
    }
  }, [timeSpan, selectedDate, refreshKey, token]);

  return (
    <div className="glass-panel chart-card" style={{ marginTop: '1rem' }}>
      <div className="chart-header">
        <h2 className="chart-title">
          <AlertTriangle className="text-gradient" style={{ color: '#ef4444' }} />
          System Anomalies & Spikes
        </h2>
      </div>

      <div style={{ padding: '0 1.5rem 1.5rem 1.5rem', maxHeight: '300px', overflowY: 'auto' }}>
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem' }}>
            <div className="spinner" style={{ width: '24px', height: '24px', borderWidth: '2px' }}></div>
          </div>
        ) : anomalies.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
            <Activity size={18} style={{ marginRight: '8px' }} />
            No significant spikes detected for this period.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '0.75rem 0.5rem' }}>Time</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>System / Feature</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Event</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Value</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Expected Avg</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>Severity</th>
              </tr>
            </thead>
            <tbody>
              {anomalies.map((anomaly, idx) => (
                <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                  <td style={{ padding: '0.75rem 0.5rem', color: '#cbd5e1' }}>{anomaly.timestamp.split(' ')[1] || anomaly.timestamp}</td>
                  <td style={{ padding: '0.75rem 0.5rem', fontWeight: '500', color: '#f8fafc' }}>{anomaly.system}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>
                    <span style={{ 
                      padding: '2px 6px', 
                      borderRadius: '4px', 
                      fontSize: '0.75rem', 
                      fontWeight: 'bold',
                      backgroundColor: anomaly.type === 'Spike' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(59, 130, 246, 0.2)',
                      color: anomaly.type === 'Spike' ? '#ef4444' : '#60a5fa'
                    }}>
                      {anomaly.type}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem 0.5rem', color: '#f8fafc' }}>{anomaly.value}</td>
                  <td style={{ padding: '0.75rem 0.5rem', color: '#94a3b8' }}>{anomaly.average}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{ width: '40px', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px', overflow: 'hidden' }}>
                        <div style={{ 
                          width: `${Math.min(100, (anomaly.severity / 10) * 100)}%`, 
                          height: '100%', 
                          background: anomaly.severity > 5 ? '#ef4444' : '#f59e0b'
                        }}></div>
                      </div>
                      <span style={{ color: anomaly.severity > 5 ? '#ef4444' : '#f59e0b' }}>
                        {anomaly.severity}z
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AnomalyPanel;
