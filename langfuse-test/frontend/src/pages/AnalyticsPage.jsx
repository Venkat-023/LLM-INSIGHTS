import { useState, useEffect } from 'react'
import axios from 'axios'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
      borderRadius: 8, padding: '8px 12px', fontSize: '0.775rem',
    }}>
      <p style={{ color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.color || 'var(--accent-light)' }}>
          {p.name}: <strong>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</strong>
        </p>
      ))}
    </div>
  )
}

const objectToChartData = (obj) =>
  Object.entries(obj || {}).map(([name, value]) => ({ name, value }))

export default function AnalyticsPage() {
  const [data, setData]   = useState(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const { data: d } = await axios.get('/api/analytics')
      setData(d)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header"><h1>📈 Analytics</h1></div>
        <div className="page-content">
          <div className="empty-state">
            <div className="spinner" style={{ width: 32, height: 32 }} />
            <p>Loading analytics…</p>
          </div>
        </div>
      </div>
    )
  }

  const hasData = data && Object.values(data.requests_by_model || {}).some(v => v > 0)

  const latencyData = objectToChartData(data?.avg_latency_by_model)
  const costData    = objectToChartData(data?.cost_by_model)
  const tokenData   = objectToChartData(data?.avg_tokens_by_model)
  const tmplData    = objectToChartData(data?.requests_by_template)

  return (
    <div className="page-container">
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1>📈 Analytics</h1>
            <p>Performance comparison across models and prompt templates. Data sourced from local usage stats.</p>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={load}>🔄 Refresh</button>
        </div>
      </div>

      <div className="page-content">
        {!hasData ? (
          <div className="empty-state">
            <div className="empty-state-icon">📈</div>
            <p>No data yet. Use the Chat and Experiment pages to generate analytics.</p>
          </div>
        ) : (
          <>
            {/* Winner summary */}
            <div className="card-grid card-grid-3" style={{ marginBottom: 24 }}>
              <div className="stat-card">
                <div className="stat-label">⚡ Fastest Model</div>
                <div className="stat-value" style={{ fontSize: '1.25rem' }}>
                  {data?.fastest_model || '–'}
                </div>
                <div className="stat-sub">
                  {data?.avg_latency_by_model?.[data?.fastest_model]?.toFixed(0)}ms avg
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">💰 Cheapest Model</div>
                <div className="stat-value" style={{ fontSize: '1.25rem' }}>
                  {data?.cheapest_model || '–'}
                </div>
                <div className="stat-sub">
                  ${data?.cost_by_model?.[data?.cheapest_model]?.toFixed(6)} total
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-label">🏆 Most Used Template</div>
                <div className="stat-value" style={{ fontSize: '1.25rem' }}>
                  {data?.most_used_template?.replace(/-/g, ' ') || '–'}
                </div>
                <div className="stat-sub">
                  {data?.requests_by_template?.[data?.most_used_template]} requests
                </div>
              </div>
            </div>

            <div className="card-grid card-grid-2">
              {/* Avg latency by model */}
              {latencyData.length > 0 && (
                <div className="card">
                  <div className="section-header">
                    <h2>⚡ Avg Latency by Model (ms)</h2>
                    <p>Lower is better</p>
                  </div>
                  <div style={{ height: 180 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={latencyData} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" tick={{ fill: '#475569', fontSize: 11 }} />
                        <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={100} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="value" name="Latency (ms)" fill="#8b5cf6" radius={[0,4,4,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Cost by model */}
              {costData.length > 0 && (
                <div className="card">
                  <div className="section-header">
                    <h2>💰 Total Cost by Model (USD)</h2>
                    <p>Lower is better</p>
                  </div>
                  <div style={{ height: 180 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={costData} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" tick={{ fill: '#475569', fontSize: 11 }} />
                        <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={100} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="value" name="Cost ($)" fill="#06b6d4" radius={[0,4,4,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Avg tokens by model */}
              {tokenData.length > 0 && (
                <div className="card">
                  <div className="section-header">
                    <h2>🪙 Avg Tokens per Request by Model</h2>
                  </div>
                  <div style={{ height: 180 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={tokenData} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" tick={{ fill: '#475569', fontSize: 11 }} />
                        <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={100} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="value" name="Avg tokens" fill="#f59e0b" radius={[0,4,4,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Requests by template */}
              {tmplData.length > 0 && (
                <div className="card">
                  <div className="section-header">
                    <h2>📝 Requests by Prompt Template</h2>
                  </div>
                  <div style={{ height: 180 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={tmplData} layout="vertical" margin={{ left: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                        <XAxis type="number" tick={{ fill: '#475569', fontSize: 11 }} />
                        <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} width={130} />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar dataKey="value" name="Requests" fill="#10b981" radius={[0,4,4,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>

            {/* Error rates table */}
            {Object.keys(data?.error_rate_by_model || {}).length > 0 && (
              <div className="card" style={{ marginTop: 20 }}>
                <div className="section-header">
                  <h2>❌ Error Rate by Model</h2>
                </div>
                <div className="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>Model</th>
                        <th>Requests</th>
                        <th>Avg Latency</th>
                        <th>Avg Tokens</th>
                        <th>Error Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(data.requests_by_model || {}).map(model => (
                        <tr key={model}>
                          <td className="font-mono text-sm">{model}</td>
                          <td>{data.requests_by_model[model]}</td>
                          <td>{data.avg_latency_by_model?.[model]?.toFixed(0)}ms</td>
                          <td>{data.avg_tokens_by_model?.[model]?.toFixed(0)}</td>
                          <td>
                            <span className={`badge ${
                              (data.error_rate_by_model?.[model] || 0) > 10
                                ? 'badge-red' : 'badge-green'
                            }`}>
                              {data.error_rate_by_model?.[model] || 0}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
