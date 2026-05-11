import React, { useState, useEffect, useCallback } from 'react';
import TimeChart from './components/TimeChart';
import AnomalyPanel from './components/AnomalyPanel';
import { Activity, Car, Gauge, Key, Upload, CheckCircle, Trash2 } from 'lucide-react';
import './index.css';

function App() {
  const [timeSpan, setTimeSpan] = useState('Month');
  const [selectedDate, setSelectedDate] = useState('');
  const [summary, setSummary] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState('');
  const [clearing, setClearing] = useState(false);
  const [availableDates, setAvailableDates] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);

  // Fetch available dates for the date picker helper
  const fetchDates = useCallback(() => {
    fetch('http://localhost:8080/api/dates')
      .then(res => res.json())
      .then(dates => setAvailableDates(dates))
      .catch(console.error);
  }, []);

  useEffect(() => { fetchDates(); }, [refreshKey, fetchDates]);

  // Fetch averages dynamically based on TimeSpan or Date
  useEffect(() => {
    let url = `http://localhost:8080/api/averages?group_by=${timeSpan.toLowerCase()}`;
    if (selectedDate) url += `&date=${selectedDate}`;
    fetch(url)
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(console.error);
  }, [timeSpan, selectedDate, refreshKey]);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setUploadSuccess('');
    
    try {
      const res = await fetch('http://localhost:8080/api/upload', {
        method: 'POST',
        body: formData,
      });
      const json = await res.json();
      if (res.ok) {
        setUploadSuccess(json.message);
        setTimeout(() => setUploadSuccess(''), 5000); // clear after 5s
      } else {
        alert(json.error || 'Upload failed');
      }
    } catch (err) {
      alert("Error: " + err);
    } finally {
      setUploading(false);
      e.target.value = null; // reset input
      setRefreshKey(k => k + 1); // trigger chart + dates refresh
    }
  };

  const handleClearData = async () => {
    if (!window.confirm('This will delete ALL stored OBD data. You will need to re-upload your CSV files. Continue?')) return;
    setClearing(true);
    try {
      const res = await fetch('http://localhost:8080/api/clear', { method: 'DELETE' });
      const json = await res.json();
      if (res.ok) {
        setSelectedDate('');
        setRefreshKey(k => k + 1);
        alert(json.message);
      } else {
        alert(json.error || 'Clear failed');
      }
    } catch (err) {
      alert('Error: ' + err);
    } finally {
      setClearing(false);
    }
  };

  return (
    <div className="dashboard-container">
      <header className="header">
        <div>
          <h1 className="text-gradient">Fleet Intelligence</h1>
          <p className="text-muted" style={{ margin: '0.5rem 0 0 0' }}>Real-time telemetry and behavior tracking</p>
        </div>
        
        <div className="controls-group" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.5rem' }}>
          <div className="timeline-selector" style={{display: 'flex', gap: '0.5rem', alignItems: 'center'}}>
            
            <div style={{ position: 'relative', marginRight: '1rem' }}>
              <input 
                type="file" 
                accept=".csv" 
                id="fileUpload" 
                onChange={handleFileUpload} 
                style={{ display: 'none' }}
              />
              <label htmlFor="fileUpload" className="upload-btn">
                {uploading ? (
                  <div className="spinner" style={{width: 16, height: 16, marginBottom: 0, borderWidth: 2}}></div>
                ) : uploadSuccess ? (
                  <CheckCircle size={18} style={{color: 'var(--success)'}}/>
                ) : (
                  <Upload size={18} />
                )}
                {uploading ? 'Processing ML...' : uploadSuccess ? 'Uploaded!' : 'Upload CSV'}
              </label>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginRight: '1rem' }}>
              <div style={{ position: 'relative' }}>
                <input 
                  type="date" 
                  className="upload-btn" 
                  value={selectedDate} 
                  onChange={(e) => setSelectedDate(e.target.value)} 
                  title={availableDates.length > 0 ? `Data available on: ${availableDates.slice(-5).join(', ')}${availableDates.length > 5 ? '...' : ''}` : 'No data uploaded yet'}
                  style={{ padding: '0.4rem 0.5rem' }}
                />
                {availableDates.length > 0 && (
                  <span style={{ position: 'absolute', top: '-8px', right: '-6px', background: '#6366f1', color: '#fff', borderRadius: '999px', fontSize: '0.6rem', padding: '1px 5px', fontWeight: 700 }}>
                    {availableDates.length}d
                  </span>
                )}
              </div>
              {selectedDate && (
                <button 
                  onClick={() => setSelectedDate('')} 
                  className="timeline-btn" 
                  style={{ padding: '0.4rem 0.5rem', fontSize: '0.8rem' }}
                >
                  Clear
                </button>
              )}
            </div>

            {['Hour', 'Day', 'Week', 'Month'].map(span => (
              <button 
                key={span}
                className={`timeline-btn ${(timeSpan === span && !selectedDate) ? 'active' : ''}`}
                onClick={() => { setTimeSpan(span); setSelectedDate(''); }}
              >
                {span}
              </button>
            ))}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {uploadSuccess && <span style={{fontSize: '0.8rem', color: 'var(--success)'}}>{uploadSuccess}</span>}
            <button
              onClick={handleClearData}
              disabled={clearing}
              className="timeline-btn"
              title="Delete all stored OBD data and start fresh"
              style={{ color: '#ef4444', borderColor: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px', opacity: clearing ? 0.5 : 1 }}
            >
              <Trash2 size={14} />
              {clearing ? 'Clearing...' : 'Clear Data'}
            </button>
            {availableDates.length > 0 && (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                📅 {availableDates.length} session{availableDates.length !== 1 ? 's' : ''} stored
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="widgets-grid" style={{ marginBottom: '1rem' }}>
        <div className="glass-panel widget-card" style={{ padding: '1rem', flex: 1, backgroundColor: 'rgba(59, 130, 246, 0.1)', borderColor: '#3b82f6' }}>
          <div className="widget-label">Driver Estimate</div>
          <div className="widget-value" style={{ fontSize: '1.5rem', color: '#60a5fa' }}>{summary ? summary.driver_estimate : '--'}</div>
        </div>
        <div className="glass-panel widget-card" style={{ padding: '1rem', flex: 1, backgroundColor: 'rgba(16, 185, 129, 0.1)', borderColor: '#10b981' }}>
          <div className="widget-label">Car Health Estimate</div>
          <div className="widget-value" style={{ fontSize: '1.5rem', color: '#34d399' }}>{summary ? summary.health_estimate : '--'}</div>
        </div>
      </div>

      <div className="widgets-grid">
        <div className="glass-panel widget-card">
          <div className="widget-icon green"><Activity size={24} /></div>
          <div className="widget-label">Good Behavior Ratio ({summary?.span_label})</div>
          <div className="widget-value">{summary ? summary.avg_good_behavior_ratio.toFixed(1) + '%' : '--%'}</div>
        </div>
        <div className="glass-panel widget-card">
          <div className="widget-icon orange"><Key size={24} /></div>
          <div className="widget-label">Neutral Behavior Ratio ({summary?.span_label})</div>
          <div className="widget-value">{summary ? summary.avg_neutral_behavior_ratio.toFixed(1) + '%' : '--%'}</div>
        </div>
        <div className="glass-panel widget-card">
          <div className="widget-icon blue"><Car size={24} /></div>
          <div className="widget-label">Good Health Ratio ({summary?.span_label})</div>
          <div className="widget-value">{summary ? summary.avg_good_health_ratio.toFixed(1) + '%' : '--%'}</div>
        </div>
        <div className="glass-panel widget-card">
          <div className="widget-icon purple"><Gauge size={24} /></div>
          <div className="widget-label">Readings ({summary?.span_label})</div>
          <div className="widget-value">{summary ? Math.round(summary.avg_total_readings).toLocaleString() : '--'}</div>
        </div>
      </div>

      <div className="charts-grid">
        {/* refreshKey is a numeric counter that increments after each upload or clear */}
        <TimeChart type="health" timeSpan={timeSpan} selectedDate={selectedDate} title="Car Health Events" refreshKey={refreshKey} />
        <TimeChart type="behavior" timeSpan={timeSpan} selectedDate={selectedDate} title="Driver Behavior Events" refreshKey={refreshKey} />
      </div>

      <AnomalyPanel timeSpan={timeSpan} selectedDate={selectedDate} refreshKey={refreshKey} />
    </div>
  );
}

export default App;
