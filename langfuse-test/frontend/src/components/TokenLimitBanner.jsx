/**
 * TokenLimitBanner – shows a friendly error when a limit is exceeded.
 * Renders nothing if there's no error.
 */
export default function TokenLimitBanner({ error, onDismiss }) {
  if (!error) return null

  const isWarning = error.type === 'warning'

  return (
    <div className={isWarning ? 'info-banner' : 'limit-banner'}>
      <span style={{ fontSize: '1rem' }}>{isWarning ? 'ℹ️' : '⚠️'}</span>
      <span style={{ flex: 1 }}>{error.message}</span>
      {onDismiss && (
        <button
          onClick={onDismiss}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'inherit', fontSize: '1rem', padding: 0,
          }}
        >
          ✕
        </button>
      )}
    </div>
  )
}
