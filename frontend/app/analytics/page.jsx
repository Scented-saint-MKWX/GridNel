'use client';

import { useEffect, useState } from 'react';
import MapPanel from '../../components/MapPanel';

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function AnalyticsPage() {
  const [mode, setMode] = useState('density');
  const [data, setData] = useState([]);
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : '';

  useEffect(() => {
    (async () => {
      const endpoint = mode === 'corridor' ? '/analytics/corridor-speeds' : `/analytics/${mode}?hours=1`;
      const res = await fetch(`${API}${endpoint}`, { headers: { Authorization: 'Bearer ' + token } });
      if (res.ok) setData(await res.json());
    })();
  }, [mode, token]);

  const markers = mode === 'heatmap' ? data.map((x) => ({ lat: x.lat, lon: x.lon, label: `weight=${x.weight}` })) : [];

  return (
    <div className="container">
      <h1>Analytics</h1>
      <select value={mode} onChange={(e) => setMode(e.target.value)}>
        <option value="density">Traffic Density</option>
        <option value="heatmap">Heatmap</option>
        <option value="corridor">Corridor Speeds</option>
      </select>
      <MapPanel markers={markers} lines={[]} />
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}
