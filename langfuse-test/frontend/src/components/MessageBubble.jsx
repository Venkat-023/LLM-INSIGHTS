import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import FeedbackPanel from './FeedbackPanel'

export default function MessageBubble({ message, onInspectTrace, activeTraceId }) {
  const isUser = message.role === 'user'
  const isActive = activeTraceId && activeTraceId === message.trace_id

  return (
    <div className={`message-row ${isUser ? 'user' : ''}`} style={{
      outline: isActive ? '2px solid var(--accent)' : 'none',
      borderRadius: 12,
      transition: 'outline 0.2s',
    }}>
      {/* Avatar */}
      <div className={`message-avatar ${isUser ? 'user' : 'ai'}`}>
        {isUser ? '👤' : '🤖'}
      </div>

      {/* Body */}
      <div className="message-body">
        <div className={`message-bubble ${isUser ? 'user' : 'ai'}`}>
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}
        </div>

        {/* Meta row */}
        {message.meta && (
          <div className="message-meta">
            {message.meta.model && (
              <span style={{ fontFamily: 'var(--font-mono)', opacity: 0.7 }}>
                {message.meta.model}
              </span>
            )}
            {message.meta.latency_ms && (
              <span>⚡ {Math.round(message.meta.latency_ms)}ms</span>
            )}
            {message.meta.total_tokens && (
              <span>🪙 {message.meta.total_tokens} tokens</span>
            )}
            {message.meta.estimated_cost != null && (
              <span>💰 ${message.meta.estimated_cost.toFixed(6)}</span>
            )}
            {/* 🔍 Inspect trace button */}
            {onInspectTrace && (
              <button
                onClick={onInspectTrace}
                className="btn btn-ghost btn-sm"
                style={{
                  padding: '1px 8px',
                  fontSize: '0.68rem',
                  color: isActive ? 'var(--accent)' : 'var(--text-muted)',
                  border: isActive ? '1px solid var(--accent)' : '1px solid var(--border)',
                }}
                title="Open Langfuse Trace Inspector"
              >
                🔍 Trace
              </button>
            )}
          </div>
        )}

        {/* Feedback */}
        {!isUser && message.trace_id && (
          <FeedbackPanel traceId={message.trace_id} />
        )}
      </div>
    </div>
  )
}
