const ACTION_LABELS = {
  intro_email:            'Intro Email Sent',
  follow_up_call:         'Follow-Up Call',
  pricing_email:          'Pricing Email Sent',
  pricing_followup_email: 'Pricing Follow-Up Email',
  meeting_scheduled:      'Meeting Scheduled',
  note:                   'Note Added',
  ai_draft_generated:     'AI Draft Generated',
  ai_draft_approved:      'AI Draft Approved',
  ai_draft_rejected:      'AI Draft Rejected',
  deal_closed:            'Deal Closed',
  manual_takeover:        'Manual Takeover',
}

function relativeTime(isoString) {
  const diff = Date.now() - new Date(isoString).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export default function TimelineTab({ actions }) {
  if (!actions || actions.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        No activity recorded yet.
      </p>
    )
  }

  return (
    <ol className="relative border-l border-gray-200 ml-2 space-y-4">
      {actions.map((action) => (
        <li key={action.id} className="ml-4">
          <div className="absolute -left-1.5 w-3 h-3 rounded-full border-2 border-white bg-indigo-400" />
          <div className="bg-white border border-gray-100 rounded-lg p-3 shadow-sm">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-semibold text-gray-800">
                {ACTION_LABELS[action.action_type] || action.action_type}
              </span>
              <span className="text-xs text-gray-400">{relativeTime(action.created_at)}</span>
            </div>
            {action.notes && (
              <p className="text-xs text-gray-600 whitespace-pre-wrap">{action.notes}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">
              {action.performed_by_email || 'System'}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}
