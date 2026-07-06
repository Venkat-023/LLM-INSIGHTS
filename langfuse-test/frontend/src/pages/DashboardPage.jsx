import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

const STAT_CARDS = [
  { key: 'total_requests',        label: 'Total Requests',       icon: '📨', fmt: v => v },
  { key: 'total_tokens',          label: 'Total Tokens',         icon: '🪙', fmt: v => v?.toLocaleString() },
  { key: 'estimated_cost',        label: 'Estimated Cost',       icon: '💰', fmt: v => `$${v?.toFixed(4)}` },
  { key: 'avg_latency_ms',        label: 'Avg Latency',          icon: '⚡', fmt: v => `${Math.round(v)}ms` },
  { key: 'total_prompt_tokens',   label: 'Prompt Tokens',        icon: '📝', fmt: v => v?.toLocaleString() },
  { key: 'total_completion_tokens',label: 'Completion Tokens',   icon: '💬', fmt: v => v?.toLocaleString() },
  { key: 'error_count',           label: 'Errors',               icon: '❌', fmt: v => v },
  { key: 'error_rate',            label: 'Error Rate',           icon: '📉', fmt: v => `${v}%` },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '8px 12px', fontSize: '0.775rem',
    }}>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <strong>{p.value}</strong>
        </p>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const [stats, setStats]       = useState(null)
  const [perUser, setPerUser]   = useState([])
  const [daily, setDaily]       = useState([])
  const [loading, setLoading]   = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [s, u, d] = await Promise.all([
        axios.get('/api/dashboard/stats'),
        axios.get('/api/dashboard/per-user'),
        axios.get('/api/dashboard/daily-usage'),
      ])
      setStats(s.data)
      setPerUser(u.data)
      setDaily(d.data.reverse())   // chronological order
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1>📊 Token Usage Dashboard</h1>
            <p>Aggregated stats from every LLM call made through this app.</p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={load}>
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="page-content">
        {loading ? (
          <div className="empty-state">
            <div className="spinner" style={{ width: 32, height: 32 }} />
            <p>Loading stats…</p>
          </div>
        ) : (
          <>
            {/* Stat cards */}
            <div className="card-grid card-grid-4" style={{ marginBottom: 24 }}>
              {STAT_CARDS.map(card => (
                <div key={card.key} className="stat-card">
                  <div className="stat-label">{card.icon} {card.label}</div>
                  <div className="stat-value">
                    {stats ? card.fmt(stats[card.key]) : '–'}
                  </div>
                </div>
              ))}
            </div>

            {/* Daily usage chart */}
            {daily.length > 0 && (
              <div className="card" style={{ marginBottom: 20 }}>
                <div className="section-header">
                  <h2>📅 Daily Usage (last 30 days)</h2>
                  <p>Requests and token usage over time</p>
                </div>
                <div className="chart-container" style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={daily} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="date" tick={{ fill: '#475569', fontSize: 11 }} />
                      <YAxis tick={{ fill: '#475569', fontSize: 11 }} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="requests" name="Requests" fill="#8b5cf6" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Per-user breakdown */}
            {perUser.length > 0 && (
              <div className="card">
                <div className="section-header">
                  <h2>👥 Requests Per User</h2>
                  <p>Usage breakdown by user ID</p>
                </div>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>User ID</th>
                        <th>Requests</th>
                        <th>Total Tokens</th>
                        <th>Est. Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {perUser.map(row => (
                        <tr key={row.user_id}>
                          <td className="font-mono text-sm">{row.user_id}</td>
                          <td>{row.requests}</td>
                          <td>{row.total_tokens?.toLocaleString()}</td>
                          <td>${row.cost?.toFixed(6)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {!stats?.total_requests && (
              <div className="empty-state">
                <div className="empty-state-icon">📭</div>
                <p>No data yet. Start chatting to see stats here!</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
