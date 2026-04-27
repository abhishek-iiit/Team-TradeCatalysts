const FORWARD_STAGES = [
  { key: 'discovered',         label: 'Discovered' },
  { key: 'intro_sent',         label: 'Intro' },
  { key: 'documents_sent',     label: 'Docs' },
  { key: 'requirements_asked', label: 'Req.' },
  { key: 'pricing_sent',       label: 'Pricing' },
  { key: 'pricing_followup',   label: 'Follow-Up' },
  { key: 'meeting_sent',       label: 'Meeting' },
  { key: 'deal_sent',          label: 'Deal' },
  { key: 'closed_won',         label: 'Won' },
]

const STAGE_INDEX = Object.fromEntries(FORWARD_STAGES.map((s, i) => [s.key, i]))

export default function StageProgressBar({ stage }) {
  if (stage === 'closed_lost') {
    return (
      <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-sm text-red-700 font-medium">
        <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
        Deal Lost
      </div>
    )
  }

  const currentIdx = STAGE_INDEX[stage] ?? 0

  return (
    <div className="flex items-center gap-0 w-full overflow-x-auto">
      {FORWARD_STAGES.map((s, idx) => {
        const done = idx < currentIdx
        const active = idx === currentIdx
        return (
          <div key={s.key} className="flex items-center flex-1 last:flex-none min-w-0">
            <div className="flex flex-col items-center min-w-0">
              <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors shrink-0 ${
                done
                  ? 'bg-indigo-600 border-indigo-600 text-white'
                  : active
                  ? 'bg-white border-indigo-600 text-indigo-600'
                  : 'bg-white border-gray-300 text-gray-400'
              }`}>
                {done ? '✓' : idx + 1}
              </div>
              <span className={`mt-1 text-xs whitespace-nowrap ${
                active ? 'text-indigo-600 font-semibold' : done ? 'text-indigo-500' : 'text-gray-400'
              }`}>
                {s.label}
              </span>
            </div>
            {idx < FORWARD_STAGES.length - 1 && (
              <div className={`flex-1 h-0.5 mx-1 mb-4 ${
                idx < currentIdx ? 'bg-indigo-600' : 'bg-gray-200'
              }`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
