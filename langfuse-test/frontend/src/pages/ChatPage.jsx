import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import MessageBubble from '../components/MessageBubble'
import PromptSelector from '../components/PromptSelector'
import TokenLimitBanner from '../components/TokenLimitBanner'
import TraceInspector from '../components/TraceInspector'
import SettingsPanel from '../components/SettingsPanel'

const SESSION_ID = sessionStorage.getItem('session_id') || (() => {
  const id = Math.random().toString(36).slice(2)
  sessionStorage.setItem('session_id', id)
  return id
})()

const USER_ID = localStorage.getItem('user_id') || (() => {
  const id = 'user-' + Math.random().toString(36).slice(2, 8)
  localStorage.setItem('user_id', id)
  return id
})()

function loadLLMSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem('llm_settings') || '{}')
    // Default to 'free' so new users immediately get a working chatbot
    if (!saved.provider) saved.provider = 'free'
    if (!saved.model) saved.model = 'openai'
    return saved
  } catch { return { provider: 'free', model: 'openai' } }
}
function saveLLMSettings(s) { localStorage.setItem('llm_settings', JSON.stringify(s)) }

export default function ChatPage() {
  const [messages, setMessages]             = useState([])
  const [input, setInput]                   = useState('')
  const [loading, setLoading]               = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const [promptTemplate, setPromptTemplate] = useState('friendly-assistant')
  const [templates, setTemplates]           = useState([])
  const [error, setError]                   = useState(null)
  const [limits, setLimits]                 = useState(null)
  const [showSettings, setShowSettings]     = useState(false)
  const [activeTrace, setActiveTrace]       = useState(null)   // trace_id to inspect
  const [llmSettings, setLlmSettings]       = useState(loadLLMSettings)
  const bottomRef   = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    axios.get('/api/prompts')
      .then(r => setTemplates(r.data))
      .catch(() => setTemplates([
        { id: 'friendly-assistant',     name: 'Friendly Assistant',     description: '' },
        { id: 'technical-assistant',    name: 'Technical Assistant',     description: '' },
        { id: 'short-answer-assistant', name: 'Short Answer Assistant',  description: '' },
      ]))
  }, [])

  useEffect(() => {
    axios.get(`/api/dashboard/limits/${USER_ID}`).then(r => setLimits(r.data)).catch(() => {})
  }, [messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const saveLLM = (updated) => {
    setLlmSettings(updated)
    saveLLMSettings(updated)
  }

  const providerLabel = () => {
    const { provider, model } = llmSettings
    if (!provider || provider === 'mock') return '🎭 Mock'
    if (provider === 'free') return `🟢 Free: ${model || 'openai'}`
    if (provider === 'anthropic') return `🟣 ${model || 'claude-3-5-sonnet-20241022'}`
    if (provider === 'gemini') return `🔵 ${model || 'gemini-1.5-flash'}`
    return `🤖 ${model || 'gpt-4o-mini'}`
  }

  const sendMessage = useCallback(async () => {
    const text = input.trim()
    if (!text || loading) return

    setInput('')
    setError(null)
    textareaRef.current?.focus()

    const userMsg = { id: Date.now(), role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const { data } = await axios.post('/api/chat', {
        message: text,
        user_id: USER_ID,
        session_id: SESSION_ID,
        conversation_id: conversationId,
        prompt_template: promptTemplate,
        provider: llmSettings.provider || 'mock',
        api_key: llmSettings.apiKey || null,
        model: llmSettings.model || null,
      })

      setConversationId(data.conversation_id)

      const aiMsg = {
        id: Date.now() + 1,
        role: 'assistant',
        content: data.reply,
        trace_id: data.trace_id,
        meta: {
          model: data.model,
          latency_ms: data.latency_ms,
          total_tokens: data.token_usage?.total_tokens,
          estimated_cost: data.token_usage?.estimated_cost,
        },
      }
      setMessages(prev => [...prev, aiMsg])

    } catch (err) {
      const detail = err.response?.data?.detail
      const message = typeof detail === 'object' ? detail.message : detail
      setError({
        message: message || 'Something went wrong. Please try again.',
        type: err.response?.status === 429 ? 'warning' : 'error',
      })
      setMessages(prev => prev.filter(m => m.id !== userMsg.id))
      setInput(text)
    } finally {
      setLoading(false)
    }
  }, [input, loading, conversationId, promptTemplate, llmSettings])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const startNew = () => { setMessages([]); setConversationId(null); setError(null); setActiveTrace(null) }

  const hasKey = (llmSettings.apiKey && llmSettings.provider && llmSettings.provider !== 'mock') || llmSettings.provider === 'free'
  const remaining = limits ? limits.remaining : '…'

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <h1>💬 Chat</h1>
            <p>Every message is traced in Langfuse in real-time. Rate responses to submit feedback scores.</p>
          </div>
          <div className="flex items-center gap-2" style={{ flexWrap: 'wrap' }}>
            <span className="badge" style={{ background: hasKey ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)', color: hasKey ? '#10b981' : '#f59e0b', border: `1px solid ${hasKey ? '#10b981' : '#f59e0b'}` }}>
              {providerLabel()}
            </span>
            <span className="badge badge-purple">{remaining} req left</span>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowSettings(s => !s)}>⚙️ Settings</button>
            <button className="btn btn-ghost btn-sm" onClick={startNew}>+ New</button>
          </div>
        </div>

        {/* Settings panel */}
        {showSettings && (
          <SettingsPanel
            settings={llmSettings}
            onChange={saveLLM}
            onClose={() => setShowSettings(false)}
          />
        )}

        {/* Prompt selector */}
        <div style={{ marginTop: 10 }}>
          <PromptSelector templates={templates} selected={promptTemplate}
            onChange={id => { setPromptTemplate(id); startNew() }} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 0, flex: 1, overflow: 'hidden' }}>
        {/* Chat area */}
        <div className="chat-layout" style={{ flex: 1 }}>
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="chat-welcome">
                <div className="chat-welcome-icon">🤖</div>
                <h2>Start a conversation</h2>
                {!hasKey && (
                  <div className="card" style={{ margin: '12px auto', maxWidth: 480, background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.3)', padding: '12px 16px', textAlign: 'left' }}>
                    <p style={{ fontSize: '0.8rem', color: '#f59e0b', margin: 0 }}>
                      ⚙️ <strong>No API key set.</strong> Running in mock mode — set your key in <button className="btn btn-ghost btn-sm" style={{ padding: '0 4px' }} onClick={() => setShowSettings(true)}>⚙️ Settings</button> to use a real LLM.
                    </p>
                  </div>
                )}
                <p>Ask me anything. Click <strong>🔍 Trace</strong> on any response to see exactly what Langfuse recorded.</p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 8 }}>
                  {['Explain how Langfuse traces work', 'Write a Python function to reverse a string', 'What is observability in AI?'].map(s => (
                    <button key={s} className="btn btn-ghost btn-sm" onClick={() => { setInput(s); textareaRef.current?.focus() }}>{s}</button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map(msg => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  onInspectTrace={msg.trace_id ? () => setActiveTrace(msg.trace_id) : null}
                  activeTraceId={activeTrace}
                />
              ))
            )}

            {loading && (
              <div className="message-row">
                <div className="message-avatar ai">🤖</div>
                <div className="message-body">
                  <div className="message-bubble ai">
                    <div className="typing-indicator">
                      <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <div className="chat-input-area">
            <TokenLimitBanner error={error} onDismiss={() => setError(null)} />
            <div className="chat-info-bar">
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {conversationId ? `conv: ${conversationId.slice(0, 8)}…` : 'New conversation'}
              </span>
              <span>{input.length}/4000</span>
            </div>
            <div className="chat-input-row">
              <div className="chat-input-wrapper">
                <textarea
                  ref={textareaRef}
                  className="chat-textarea"
                  placeholder="Type your message… (Enter to send, Shift+Enter for newline)"
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  rows={1}
                  onInput={e => { e.target.style.height = 'auto'; e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px' }}
                />
                <button className="chat-send-btn" onClick={sendMessage} disabled={!input.trim() || loading} title="Send (Enter)">
                  {loading ? <div className="spinner" style={{ width: 16, height: 16 }} /> : '↑'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Trace Inspector side panel */}
        {activeTrace && (
          <TraceInspector traceId={activeTrace} onClose={() => setActiveTrace(null)} />
        )}
      </div>
    </div>
  )
}
