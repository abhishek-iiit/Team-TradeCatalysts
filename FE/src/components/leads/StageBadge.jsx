const STAGE_CONFIG = {
  discovered:          { label: 'Discovered',           bg: 'bg-gray-100',    text: 'text-gray-700' },
  intro_sent:          { label: 'Intro Sent',            bg: 'bg-blue-100',    text: 'text-blue-700' },
  documents_sent:      { label: 'Documents Sent',        bg: 'bg-sky-100',     text: 'text-sky-700' },
  requirements_asked:  { label: 'Requirements Asked',    bg: 'bg-teal-100',    text: 'text-teal-700' },
  pricing_sent:        { label: 'Pricing Sent',          bg: 'bg-purple-100',  text: 'text-purple-700' },
  pricing_followup:    { label: 'Pricing Follow-Up',     bg: 'bg-yellow-100',  text: 'text-yellow-700' },
  meeting_sent:        { label: 'Meeting Sent',          bg: 'bg-indigo-100',  text: 'text-indigo-700' },
  deal_sent:           { label: 'Deal Sent',             bg: 'bg-orange-100',  text: 'text-orange-700' },
  closed_won:          { label: 'Won',                   bg: 'bg-green-100',   text: 'text-green-700' },
  closed_lost:         { label: 'Lost',                  bg: 'bg-red-100',     text: 'text-red-700' },
}

export default function StageBadge({ stage }) {
  const config = STAGE_CONFIG[stage] || { label: stage, bg: 'bg-gray-100', text: 'text-gray-600' }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}>
      {config.label}
    </span>
  )
}
