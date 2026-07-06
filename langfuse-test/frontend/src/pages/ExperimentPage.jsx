import { useState, useEffect } from 'react'
import axios from 'axios'
import ReactMarkdown from 'react-markdown'
import FeedbackPanel from '../components/FeedbackPanel'

const AVAILABLE_MODELS = [
  { id: 'gpt-4o-mini', label: 'GPT-4o Mini (OpenAI)', badge: 'badge-blue', desc: 'Balanced & fast' },
  { id: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku (Anthropic)', badge: 'badge-purple', desc: 'Precise and fast' },
  { id: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash (Google)', badge: 'badge-green', desc: 'Fast, multimodal' },
  { id: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Anthropic)', badge: 'badge-purple', desc: 'High capability' },
  { id: 'gpt-4.1-mini', label: 'GPT-4.1 Mini', badge: 'badge-gray', desc: 'Legacy / Simulated' }
]

export default function ExperimentPage() {
  const [prompt, setPrompt]         = useState('')
  const [results, setResults]       = useState([])
  const [loading, setLoading]       = useState(false)
  const [selectedModels, setSelectedModels] = useState(['gpt-4o-mini', 'claude-3-5-haiku-20241022', 'gemini-1.5-flash'])
  const [promptTemplate, setPromptTemplate] = useState('friendly-assistant')
  const [templates, setTemplates]   = useState([])

  useEffect(() => {
    axios.get('/api/prompts').then(r => setTemplates(r.data)).catch(() => {})
  }, [])

  const toggleModel = (id) => {
    setSelectedModels(prev =>
      prev.includes(id)
        ? prev.filter(m => m !== id)
        : [...prev, id]
    )
  }

  const runExperiment = async () => {
    if (!prompt.trim() || selectedModels.length === 0) return
    setLoading(true)
    setResults([])

    // Load custom keys from localStorage settings
    let savedSettings = {}
    try {
      savedSettings = JSON.parse(localStorage.getItem('llm_settings') || '{}')
    } catch {}

    const key = savedSettings.apiKey || null
    const provider = savedSettings.provider || null

    const payload = {
      prompt: prompt.trim(),
      models: selectedModels,
      user_id: localStorage.getItem('user_id') || 'experiment-user',
      prompt_template: promptTemplate,
      openai_key: provider === 'openai' ? key : null,
      anthropic_key: provider === 'anthropic' ? key : null,
      gemini_key: provider === 'gemini' ? key : null,
    }

    try {
      const { data } = await axios.post('/api/experiment', payload)
      setResults(data.results)
    } catch (err) {
      console.error('Experiment error:', err)
    } finally {
      setLoading(false)
    }
  }

  const fastest = results.length > 0
    ? results.filter(r => !r.error).reduce((a, b) => a.latency_ms < b.latency_ms ? a : b, results[0])?.model
    : null

  const cheapest = results.length > 0
    ? results.filter(r => !r.error).reduce((a, b) => a.estimated_cost < b.estimated_cost ? a : b, results[0])?.model
    : null

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>🧪 Model Experiment</h1>
        <p>Run the same prompt through multiple models and compare results. Each call creates a separate Langfuse trace.</p>
      </div>

      <div className="page-content">
        {/* Config */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="section-header">
            <h2>⚙️ Configuration</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* Prompt input */}
            <textarea
              className="input"
              rows={3}
              placeholder="Enter a prompt to test across all models…"
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
            />

            {/* Model selection */}
            <div>
              <label className="text-xs text-muted" style={{ display: 'block', marginBottom: 6 }}>
                Select models to compare:
              </label>
              <div style={{ display: 'flex', gap: 8 }}>
                {AVAILABLE_MODELS.map(m => (
                  <button
                    key={m.id}
                    className={`btn btn-sm ${selectedModels.includes(m.id) ? 'btn-primary' : 'btn-ghost'}`}
                    onClick={() => toggleModel(m.id)}
                    title={m.desc}
                  >
                    {selectedModels.includes(m.id) ? '✓ ' : ''}{m.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Prompt template */}
            <div>
              <label className="text-xs text-muted" style={{ display: 'block', marginBottom: 6 }}>
                System prompt template:
              </label>
              <select
                className="select"
                value={promptTemplate}
                onChange={e => setPromptTemplate(e.target.value)}
                style={{ width: 'auto' }}
              >
                {templates.map(t => (
                  <option key={t.id} value={t.id}>{t.name}</option>
                ))}
              </select>
            </div>

            <div>
              <button
                className="btn btn-primary"
                onClick={runExperiment}
                disabled={loading || !prompt.trim() || selectedModels.length === 0}
              >
                {loading ? (
                  <><div className="spinner" style={{ width: 14, height: 14 }} /> Running…</>
                ) : '🚀 Run Experiment'}
              </button>
            </div>
          </div>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <>
            {/* Winner badges */}
            {(fastest || cheapest) && (
              <div className="flex gap-2 mb-4">
                {fastest && <span className="badge badge-green">⚡ Fastest: {fastest}</span>}
                {cheapest && <span className="badge badge-blue">💰 Cheapest: {cheapest}</span>}
              </div>
            )}

            <div
              className="model-cards-grid"
              style={{
                gridTemplateColumns: `repeat(${results.length}, 1fr)`,
              }}
            >
              {results.map(result => (
                <div key={result.model} className="model-card">
                  <div className="model-card-header">
                    <span className="model-name">{result.model}</span>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {result.model === fastest && <span className="badge badge-green">Fastest ⚡</span>}
                      {result.model === cheapest && <span className="badge badge-blue">Cheapest 💰</span>}
                      {result.error && <span className="badge badge-red">Error</span>}
                    </div>
                  </div>

                  <div className="model-card-body">
                    {result.error ? (
                      <div style={{ color: 'var(--error)', fontSize: '0.8rem' }}>
                        ❌ {result.error}
                      </div>
                    ) : (
                      <>
                        <div className="model-stats">
                          <div className="model-stat-row">
                            <span className="model-stat-key">Latency</span>
                            <span className="model-stat-val">{Math.round(result.latency_ms)}ms</span>
                          </div>
                          <div className="model-stat-row">
                            <span className="model-stat-key">Prompt tokens</span>
                            <span className="model-stat-val">{result.prompt_tokens}</span>
                          </div>
                          <div className="model-stat-row">
                            <span className="model-stat-key">Completion tokens</span>
                            <span className="model-stat-val">{result.completion_tokens}</span>
                          </div>
                          <div className="model-stat-row">
                            <span className="model-stat-key">Total tokens</span>
                            <span className="model-stat-val">{result.total_tokens}</span>
                          </div>
                          <div className="model-stat-row">
                            <span className="model-stat-key">Est. cost</span>
                            <span className="model-stat-val">${result.estimated_cost?.toFixed(6)}</span>
                          </div>
                        </div>

                        <div className="model-response">
                          <ReactMarkdown>{result.response}</ReactMarkdown>
                        </div>

                        {/* Rate this model's response */}
                        {result.trace_id && result.trace_id !== 'error' && (
                          <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                            <p className="text-xs text-muted" style={{ marginBottom: 6 }}>Rate this response:</p>
                            <FeedbackPanel traceId={result.trace_id} />
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {!loading && results.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🧪</div>
            <p>Enter a prompt and click "Run Experiment" to compare models.</p>
            <p className="text-xs text-muted">Each model call creates a separate Langfuse trace tagged with "experiment".</p>
          </div>
        )}
      </div>
    </div>
  )
}
