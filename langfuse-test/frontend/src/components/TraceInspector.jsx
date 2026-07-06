import { useState, useEffect } from 'react'
import axios from 'axios'

const LANGFUSE_URL = 'https://cloud.langfuse.com'

function ObservationCard({ obs }) {
  const [open, setOpen] = useState(true)
  const isGeneration = obs.type === 'GENERATION'
  const icon = isGeneration ? '⚡' : obs.type === 'SPAN' ? '📦' : '📌'

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      marginBottom: 8,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', textAlign: 'left', padding: '8px 12px',
          background: 'none', border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 8,
          color: 'var(--text-primary)',
        }}
      >
        <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>{open ? '▼' : '▶'}</span>
        <span>{icon}</span>
        <span style={{ fontWeight: 600, fontSize: '0.8rem', flex: 1 }}>{obs.name || obs.type}</span>
        {obs.model && <span className="badge badge-purple" style={{ fontSize: '0.65rem' }}>{obs.model}</span>}
        {obs.latency != null && (
          <span className="badge" style={{ fontSize: '0.65rem', background: 'rgba(6,182,212,0.15)', color: '#06b6d4', border: '1px solid #06b6d4' }}>
            {(obs.latency * 1000).toFixed(0)}ms
          </span>
        )}
      </button>

      {open && (
        <div style={{ padding: '0 12px 12px', borderTop: '1px solid var(--border)' }}>
          {/* Token & cost row */}
          {isGeneration && (
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 8, marginBottom: 8 }}>
              {[
                ['Prompt tokens', obs.promptTokens],
                ['Completion tokens', obs.completionTokens],
                ['Total tokens', obs.totalTokens],
                ['Cost', obs.calculatedTotalCost != null ? `$${Number(obs.calculatedTotalCost).toFixed(6)}` : '—'],
              ].map(([k, v]) => v != null && (
                <div key={k} style={{ fontSize: '0.72rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}: </span>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{v}</span>
                </div>
              ))}
            </div>
          )}

          {/* Input */}
          {obs.input != null && (
            <div style={{ marginTop: 8 }}>
              <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 4 }}>INPUT</p>
              <pre style={{
                background: 'rgba(0,0,0,0.25)', borderRadius: 6, padding: '8px 10px',
                fontSize: '0.72rem', color: 'var(--text-secondary)',
                overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                maxHeight: 180, overflowY: 'auto', margin: 0,
              }}>
                {typeof obs.input === 'string' ? obs.input : JSON.stringify(obs.input, null, 2)}
              </pre>
            </div>
          )}

          {/* Output */}
          {obs.output != null && (
            <div style={{ marginTop: 8 }}>
              <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 4 }}>OUTPUT</p>
              <pre style={{
                background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.15)',
                borderRadius: 6, padding: '8px 10px',
                fontSize: '0.72rem', color: 'var(--text-secondary)',
                overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                maxHeight: 180, overflowY: 'auto', margin: 0,
              }}>
                {typeof obs.output === 'string' ? obs.output : JSON.stringify(obs.output, null, 2)}
              </pre>
            </div>
          )}

          {/* Metadata */}
          {obs.metadata && Object.keys(obs.metadata).length > 0 && (
            <div style={{ marginTop: 8 }}>
              <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginBottom: 4 }}>METADATA</p>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {Object.entries(obs.metadata).map(([k, v]) => (
                  <span key={k} className="badge" style={{ fontSize: '0.65rem', background: 'rgba(139,92,246,0.1)', color: '#a78bfa', border: '1px solid rgba(139,92,246,0.25)' }}>
                    {k}: {String(v)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ScoreRow({ score }) {
  const icon = score.name === 'user-feedback'
    ? (score.value >= 1 ? '👍' : '👎')
    : score.name === 'star-rating' ? '⭐' : '📊'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, fontSize: '0.78rem' }}>
      <span>{icon}</span>
      <span style={{ color: 'var(--text-secondary)' }}>{score.name}</span>
      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{score.value}</span>
      {score.comment && <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>"{score.comment}"</span>}
    </div>
  )
}

export default function TraceInspector({ traceId, onClose }) {
  const [trace, setTrace]     = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)

  useEffect(() => {
    if (!traceId) return
    setLoading(true)
    setError(null)
    setTrace(null)
    axios.get(`/api/trace/${traceId}`)
      .then(r => {
        if (r.data.error) setError(r.data.error + ': ' + r.data.detail)
        else setTrace(r.data)
      })
      .catch(e => setError('Failed to load trace: ' + e.message))
      .finally(() => setLoading(false))
  }, [traceId])

  return (
    <div className="trace-inspector">
      {/* Header */}
      <div className="trace-inspector-header">
        <div>
          <h3>🔍 Langfuse Trace Inspector</h3>
          <p style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 2, fontFamily: 'var(--font-mono)' }}>
            {traceId?.slice(0, 24)}…
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <a
            href={`${LANGFUSE_URL}/trace/${traceId}`}
            target="_blank"
            rel="noreferrer"
            className="btn btn-ghost btn-sm"
            title="Open full trace in Langfuse"
          >
            ↗ Langfuse
          </a>
          <button className="btn btn-ghost btn-sm" onClick={onClose} title="Close">✕</button>
        </div>
      </div>

      <div className="trace-inspector-body">
        {loading && (
          <div className="empty-state" style={{ padding: 24 }}>
            <div className="spinner" style={{ width: 24, height: 24 }} />
            <p style={{ fontSize: '0.78rem' }}>Fetching from Langfuse…</p>
          </div>
        )}

        {error && (
          <div style={{ padding: 16, color: 'var(--error)', fontSize: '0.78rem' }}>
            ❌ {error}
          </div>
        )}

        {trace && (
          <>
            {/* Summary row */}
            <div className="trace-summary-grid">
              {[
                ['Name', trace.name],
                ['Latency', trace.latency ? `${(trace.latency * 1000).toFixed(0)}ms` : '—'],
                ['Cost', trace.totalCost ? `$${Number(trace.totalCost).toFixed(6)}` : '—'],
                ['User', trace.userId],
                ['Environment', trace.environment || '—'],
              ].map(([k, v]) => (
                <div key={k} className="trace-summary-cell">
                  <div className="trace-summary-label">{k}</div>
                  <div className="trace-summary-value">{v || '—'}</div>
                </div>
              ))}
            </div>

            {/* Tags */}
            {trace.tags?.length > 0 && (
              <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 12 }}>
                {trace.tags.map(t => (
                  <span key={t} className="badge badge-blue" style={{ fontSize: '0.65rem' }}>{t}</span>
                ))}
              </div>
            )}

            {/* Trace input / output */}
            <div style={{ marginBottom: 12 }}>
              <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4, fontWeight: 600 }}>TRACE INPUT</p>
              <pre className="trace-code-block">{
                typeof trace.input === 'string' ? trace.input : JSON.stringify(trace.input, null, 2)
              }</pre>
            </div>
            {trace.output && (
              <div style={{ marginBottom: 12 }}>
                <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 4, fontWeight: 600 }}>TRACE OUTPUT</p>
                <pre className="trace-code-block" style={{ borderColor: 'rgba(16,185,129,0.25)', background: 'rgba(16,185,129,0.05)' }}>{
                  typeof trace.output === 'string' ? trace.output : JSON.stringify(trace.output, null, 2)
                }</pre>
              </div>
            )}

            {/* Scores / Feedback */}
            {trace.scores?.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600 }}>
                  FEEDBACK SCORES ({trace.scores.length})
                </p>
                {trace.scores.map((s, i) => <ScoreRow key={i} score={s} />)}
              </div>
            )}

            {/* Observations */}
            <div>
              <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: 6, fontWeight: 600 }}>
                OBSERVATIONS ({trace.observations?.length || 0})
              </p>
              {trace.observations?.length === 0 && (
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  No observations yet. Langfuse may still be ingesting this trace (usually &lt;2s).
                </p>
              )}
              {trace.observations?.map(obs => <ObservationCard key={obs.id} obs={obs} />)}
            </div>

            {/* Full JSON toggle */}
            <details style={{ marginTop: 8 }}>
              <summary style={{ fontSize: '0.72rem', color: 'var(--text-muted)', cursor: 'pointer' }}>
                View raw JSON
              </summary>
              <pre className="trace-code-block" style={{ marginTop: 6, maxHeight: 300 }}>
                {JSON.stringify(trace, null, 2)}
              </pre>
            </details>
          </>
        )}
      </div>
    </div>
  )
}
