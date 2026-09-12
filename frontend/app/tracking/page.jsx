'use client';

import { useEffect, useMemo, useState } from 'react';
import MapPanel from '../../components/MapPanel';

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function TrackingPage() {
  const [plate, setPlate] = useState('MH12AB1284');
  const [segments, setSegments] = useState([]);
  const [alerts, setAlerts] = useState([]);

  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : '';

  async function search() {
    const res = await fetch(`${API}/track/${plate}/bridged`, { headers: { Authorization: 'Bearer ' + token } });
    if (!res.ok) return;
    const data = await res.json();
    setSegments(data.segments || []);
  }

  useEffect(() => {
    const id = setInterval(async () => {
      const since = new Date(Date.now() - 10_000).toISOString();
      const res = await fetch(`${API}/alerts?since=${encodeURIComponent(since)}`, { headers: { Authorization: 'Bearer ' + token } });
      if (res.ok) setAlerts(await res.json());
    }, 10000);
    return () => clearInterval(id);
  }, [token]);

  const markers = useMemo(() => segments.filter((s) => s.type === 'observed').map((s) => ({ lat: s.lat, lon: s.lon, label: `${s.camera_id} ${s.ts}`, flash: alerts.some((a) => a.camera_id === s.camera_id) })), [segments, alerts]);
  const lines = useMemo(() => segments.filter((s) => s.type === 'inferred').map((s) => ({ coords: s.path, dashed: true })), [segments]);

  return (
    <div className="container">
      <h1>Tracking</h1>
      {!!alerts.length && <div className="banner">BLACKLIST HIT detected (camera flash markers)</div>}
      <div className="row">
        <input value={plate} onChange={(e) => setPlate(e.target.value)} />
        <button onClick={search}>Track Bridged</button>
      </div>
      <MapPanel markers={markers} lines={lines} />
      <pre>{JSON.stringify(segments, null, 2)}</pre>
    </div>
  );
}
