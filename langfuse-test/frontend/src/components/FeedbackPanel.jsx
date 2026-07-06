import { useState } from 'react'
import axios from 'axios'

/**
 * FeedbackPanel – 👍/👎/⭐/💬 feedback form.
 *
 * HOW IT WORKS WITH LANGFUSE:
 * The `traceId` prop is the Langfuse trace ID returned in the ChatResponse.
 * When the user submits feedback, we POST to /api/feedback which calls
 * langfuse.score(trace_id, ...) to attach the feedback to the trace.
 * You can then see scores on each trace in the Langfuse dashboard and
 * use them to evaluate which prompts/models perform best.
 */
export default function FeedbackPanel({ traceId }) {
  const [label, setLabel]     = useState(null)   // 'helpful' | 'not_helpful'
  const [rating, setRating]   = useState(0)       // 1-5 stars
  const [comment, setComment] = useState('')
  const [showComment, setShowComment] = useState(false)
  const [submitted, setSubmitted]     = useState(false)
  const [loading, setLoading]         = useState(false)

  const handleSubmit = async () => {
    if (!label) return
    setLoading(true)
    try {
      await axios.post('/api/feedback', {
        trace_id: traceId,
        label,
        rating: rating || null,
        comment: comment || null,
      })
      setSubmitted(true)
    } catch (err) {
      console.error('Feedback error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (submitted) {
    return (
      <div className="feedback-success">
        ✅ Thanks for your feedback!
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div className="feedback-panel">
        {/* Thumbs up/down */}
        <button
          className={`feedback-btn ${label === 'helpful' ? 'active-helpful' : ''}`}
          onClick={() => setLabel(label === 'helpful' ? null : 'helpful')}
          title="Helpful"
        >
          👍 Helpful
        </button>
        <button
          className={`feedback-btn ${label === 'not_helpful' ? 'active-not_helpful' : ''}`}
          onClick={() => setLabel(label === 'not_helpful' ? null : 'not_helpful')}
          title="Not helpful"
        >
          👎 Not helpful
        </button>

        {/* Star rating */}
        <div className="star-rating">
          {[1,2,3,4,5].map(n => (
            <button
              key={n}
              className={`star-btn ${n <= rating ? 'active' : ''}`}
              onClick={() => setRating(rating === n ? 0 : n)}
              title={`${n} star${n > 1 ? 's' : ''}`}
            >
              ★
            </button>
          ))}
        </div>

        {/* Comment toggle */}
        <button
          className="feedback-btn"
          onClick={() => setShowComment(!showComment)}
          title="Add comment"
        >
          💬
        </button>

        {/* Submit */}
        {label && (
          <button
            className="btn btn-primary btn-sm"
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? '…' : 'Send'}
          </button>
        )}
      </div>

      {/* Comment textarea */}
      {showComment && (
        <div className="feedback-comment-area">
          <input
            className="input"
            placeholder="Optional comment…"
            value={comment}
            onChange={e => setComment(e.target.value)}
            style={{ fontSize: '0.775rem', padding: '6px 10px' }}
          />
        </div>
      )}
    </div>
  )
}
