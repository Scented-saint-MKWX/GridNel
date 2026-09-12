'use client';

import { useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export default function LoginPage() {
  const [username, setUsername] = useState('tracker');
  const [password, setPassword] = useState('track123');
  const [err, setErr] = useState('');

  async function login(e) {
    e.preventDefault();
    const res = await fetch(`${API}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) return setErr('Login failed');
    const data = await res.json();
    localStorage.setItem('token', data.token);
    localStorage.setItem('role', data.role);
    window.location.href = data.role === 'tracker' ? '/tracking' : '/analytics';
  }

  return (
    <div className="container">
      <h1>SentinelGrid Login</h1>
      <form onSubmit={login} className="row">
        <select value={username} onChange={(e) => setUsername(e.target.value)}>
          <option value="tracker">tracker</option>
          <option value="analyst">analyst</option>
        </select>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <button type="submit">Login</button>
      </form>
      <p>Demo passwords: tracker/track123 and analyst/analytics123</p>
      {err && <p>{err}</p>}
    </div>
  );
}
