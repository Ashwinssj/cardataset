import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity, Car } from 'lucide-react';

const COLORS = {
  Good: '#10b981', // Emerald
  Neutral: '#f59e0b', // Amber
  Bad: '#ef4444', // Red
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="recharts-default-tooltip">
        <p className="tooltip-label">{label}</p>
        {payload.map((entry, index) => (
          <div key={index} style={{ color: entry.color, display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: entry.color }}></span>
            <span>{entry.name}: {entry.value}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

const TimeChart = ({ type, timeSpan, title, refreshKey, selectedDate }) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        let url = `http://localhost:8080/api/${type === 'health' ? 'car_health' : 'driver_behavior'}?group_by=${timeSpan.toLowerCase()}`;
        if (selectedDate) url += `&date=${selectedDate}`;
        const res = await fetch(url);
        
        const json = await res.json();
        const formatted = json.map(item => ({
          ...item,
          time: item.time_period
        }));
        setData(formatted);
      } catch (err) {
        console.error("Error fetching chart data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [type, timeSpan, refreshKey, selectedDate]);

  return (
    <div className="glass-panel chart-card">
      <div className="chart-header">
        <h2 className="chart-title">
          {type === 'health' ? <Car className="text-gradient" /> : <Activity className="text-gradient" />}
          {title}
        </h2>
      </div>
      
      <div className="chart-container">
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <div className="spinner" style={{ width: '24px', height: '24px', borderWidth: '2px' }}></div>
          </div>
        ) : data.length === 0 ? (
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--text-muted)' }}>
            No data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`colorGood${type}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.Good} stopOpacity={0.6}/>
                  <stop offset="95%" stopColor={COLORS.Good} stopOpacity={0}/>
                </linearGradient>
                <linearGradient id={`colorNeutral${type}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.Neutral} stopOpacity={0.6}/>
                  <stop offset="95%" stopColor={COLORS.Neutral} stopOpacity={0}/>
                </linearGradient>
                <linearGradient id={`colorBad${type}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.Bad} stopOpacity={0.6}/>
                  <stop offset="95%" stopColor={COLORS.Bad} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="time_period" stroke="#efefef" opacity={0.5} tick={{ fill: '#94a3b8' }} tickMargin={10} axisLine={false} />
              <YAxis stroke="#efefef" opacity={0.5} tick={{ fill: '#94a3b8' }} tickMargin={10} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Legend verticalAlign="top" height={36} wrapperStyle={{ color: 'var(--text-muted)' }} />
              
              <Area type="monotone" dataKey="Bad" stroke={COLORS.Bad} strokeWidth={2} fillOpacity={1} fill={`url(#colorBad${type})`} />
              <Area type="monotone" dataKey="Neutral" stroke={COLORS.Neutral} strokeWidth={2} fillOpacity={1} fill={`url(#colorNeutral${type})`} />
              <Area type="monotone" dataKey="Good" stroke={COLORS.Good} strokeWidth={2} fillOpacity={1} fill={`url(#colorGood${type})`} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
};

export default TimeChart;
