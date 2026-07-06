import { useState } from 'react'

const PROVIDERS = [
  {
    id: 'openai', label: 'OpenAI', icon: '🤖',
    models: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo', 'gpt-4.1-mini'],
    placeholder: 'your-openai-api-key',
    hint: 'Get your key at platform.openai.com/api-keys',
    docsUrl: 'https://platform.openai.com/api-keys',
  },
  {
    id: 'anthropic', label: 'Anthropic (Claude)', icon: '🟣',
    models: ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-haiku-20240307'],
    placeholder: 'your-anthropic-api-key',
    hint: 'Get your key at console.anthropic.com/settings/keys',
    docsUrl: 'https://console.anthropic.com/settings/keys',
  },
  {
    id: 'gemini', label: 'Google Gemini', icon: '🔵',
    models: ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash', 'gemini-2.5-flash-preview-05-20'],
    placeholder: 'AIza…',
    hint: 'Get your key at aistudio.google.com/app/apikey',
    docsUrl: 'https://aistudio.google.com/app/apikey',
  },
  {
    id: 'free', label: 'Free AI (No Key)', icon: '🟢',
    models: ['openai', 'llama', 'mistral', 'qwen', 'searchgpt'],
    placeholder: '',
    hint: 'No key required! Connects to real open LLMs for free.',
    docsUrl: null,
  },
  {
    id: 'mock', label: 'Simulation (no key needed)', icon: '🎭',
    models: ['mock-model'],
    placeholder: '',
    hint: 'No key required. Responses are simulated but fully traced in Langfuse.',
    docsUrl: null,
  },
]

export default function SettingsPanel({ settings, onChange, onClose }) {
  const [local, setLocal] = useState({
    provider: settings.provider || 'free', // default to free
    apiKey: settings.apiKey || '',
    model: settings.model || '',
  })
  const [showKey, setShowKey] = useState(false)

  const provider = PROVIDERS.find(p => p.id === local.provider) || PROVIDERS[0]

  const update = (key, val) => {
    const next = { ...local, [key]: val }
    if (key === 'provider') {
      const p = PROVIDERS.find(x => x.id === val)
      next.model = p?.models[0] || ''
      next.apiKey = ''
    }
    setLocal(next)
  }

  const save = () => {
    onChange(local)
    onClose()
  }

  return (
    <div className="settings-panel card" style={{ marginTop: 12, padding: '16px 20px', position: 'relative' }}>
      <button
        className="btn btn-ghost btn-sm"
        style={{ position: 'absolute', top: 10, right: 10 }}
        onClick={onClose}
        title="Close settings"
      >✕</button>

      <h3 style={{ margin: '0 0 12px', fontSize: '0.9rem', color: 'var(--text-primary)' }}>
        ⚙️ LLM Provider Settings
      </h3>

      {/* Provider selection */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
        {PROVIDERS.map(p => (
          <button
            key={p.id}
            className={`btn btn-sm ${local.provider === p.id ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => update('provider', p.id)}
          >
            {p.icon} {p.label}
          </button>
        ))}
      </div>

      {/* API Key input */}
      {local.provider !== 'mock' && local.provider !== 'free' && (
        <div style={{ marginBottom: 10 }}>
          <label className="text-xs text-muted" style={{ display: 'block', marginBottom: 4 }}>
            API Key
          </label>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              type={showKey ? 'text' : 'password'}
              className="input"
              style={{ flex: 1, fontSize: '0.82rem' }}
              placeholder={provider.placeholder}
              value={local.apiKey}
              onChange={e => update('apiKey', e.target.value)}
              autoComplete="off"
            />
            <button className="btn btn-ghost btn-sm" onClick={() => setShowKey(v => !v)}>
              {showKey ? '🙈' : '👁️'}
            </button>
          </div>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
            {provider.hint}{' '}
            {provider.docsUrl && (
              <a href={provider.docsUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)' }}>
                Open ↗
              </a>
            )}
          </p>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 2 }}>
            🔒 Your key is stored only in your browser's localStorage and sent securely to your local backend.
          </p>
        </div>
      )}

      {/* Model selection */}
      <div style={{ marginBottom: 12 }}>
        <label className="text-xs text-muted" style={{ display: 'block', marginBottom: 4 }}>
          Model
        </label>
        <select
          className="select"
          value={local.model}
          onChange={e => update('model', e.target.value)}
          style={{ width: '100%' }}
        >
          {provider.models.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary" onClick={save}>✓ Save & Apply</button>
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
      </div>

      {local.provider === 'mock' && (
        <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 10 }}>
          In simulation mode, all interactions are still traced in Langfuse with realistic token counts, latency metrics, and your prompt template version.
        </p>
      )}
      {local.provider === 'free' && (
        <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 10 }}>
          🟢 Connects to real, keyless LLMs (GPT-4o Mini, Llama 3.1, Qwen, etc.) for free. All calls are fully instrumented and traced live in Langfuse!
        </p>
      )}
    </div>
  )
}
