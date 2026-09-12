'use client';

import { useEffect, useState } from 'react';
import MapPanel from '../../components/MapPanel';

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([]);
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : '';

  useEffect(() => {
    const poll = async () => {
      const since = new Date(Date.now() - 10_000).toISOString();
      const res = await fetch(`${API}/alerts?since=${encodeURIComponent(since)}`, { headers: { Authorization: 'Bearer ' + token } });
      if (res.ok) setAlerts(await res.json());
    };
    poll();
    const id = setInterval(poll, 10000);
    return () => clearInterval(id);
  }, [token]);

  const markers = alerts.map((a) => ({ lat: 28.6139, lon: 77.2090, label: `${a.type} ${a.camera_id}`, flash: true }));

  return (
    <div className="container">
      <h1>Alert Console</h1>
      {!!alerts.length && <div className="banner">BLACKLIST HIT: immediate attention required</div>}
      <MapPanel markers={markers} lines={[]} />
      <pre>{JSON.stringify(alerts, null, 2)}</pre>
    </div>
  );
}
