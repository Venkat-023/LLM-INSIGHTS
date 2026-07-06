/**
 * PromptSelector – chip-style selector for the three prompt templates.
 *
 * The selected template name is sent with every chat request.
 * The backend fetches the matching prompt from Langfuse Prompt Management.
 */
export default function PromptSelector({ templates, selected, onChange }) {
  const ICONS = {
    'friendly-assistant':    '😊',
    'technical-assistant':   '⚙️',
    'short-answer-assistant':'⚡',
  }

  return (
    <div className="prompt-selector">
      {templates.map(tmpl => (
        <button
          key={tmpl.id}
          className={`prompt-chip ${selected === tmpl.id ? 'active' : ''}`}
          onClick={() => onChange(tmpl.id)}
          title={tmpl.description}
        >
          {ICONS[tmpl.id] || '🤖'} {tmpl.name}
        </button>
      ))}
    </div>
  )
}
