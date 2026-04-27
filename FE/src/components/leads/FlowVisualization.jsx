import { useQuery } from '@tanstack/react-query'
import { getLeadFlow } from '../../api/deals'

const ACTION_LABELS = {
  intro_email: 'Intro Email Sent',
  follow_up_call: 'Follow-Up Call',
  pricing_email: 'Pricing Email Sent',
  pricing_followup_email: 'Pricing Follow-Up Email',
  meeting_scheduled: 'Meeting Scheduled',
  note: 'Note Added',
  ai_draft_generated: 'AI Draft Generated',
  ai_draft_approved: 'AI Draft Approved',
  ai_draft_rejected: 'AI Draft Rejected',
  deal_closed: 'Deal Closed',
  manual_takeover: 'Manual Takeover',
}

const ACTION_COLORS = {
  intro_email: 'bg-blue-100 text-blue-700 border-blue-200',
  follow_up_call: 'bg-purple-100 text-purple-700 border-purple-200',
  pricing_email: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  pricing_followup_email: 'bg-violet-100 text-violet-700 border-violet-200',
  meeting_scheduled: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  note: 'bg-gray-100 text-gray-600 border-gray-200',
  ai_draft_generated: 'bg-orange-100 text-orange-700 border-orange-200',
  ai_draft_approved: 'bg-green-100 text-green-700 border-green-200',
  ai_draft_rejected: 'bg-red-100 text-red-600 border-red-200',
  deal_closed: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  manual_takeover: 'bg-yellow-100 text-yellow-700 border-yellow-200',
}

const STAGE_COLORS = {
  completed: 'bg-indigo-600 border-indigo-600 text-white',
  current: 'bg-white border-indigo-500 text-indigo-600 ring-2 ring-indigo-200',
  pending: 'bg-white border-gray-300 text-gray-400',
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function FlowVisualization({ leadId }) {
  const { data: flow, isLoading, isError } = useQuery({
    queryKey: ['lead-flow', leadId],
    queryFn: () => getLeadFlow(leadId),
  })

  if (isLoading) {
    return <p className="text-sm text-gray-400 text-center py-8">Loading flow…</p>
  }
  if (isError || !flow) {
    return <p className="text-sm text-red-500 text-center py-8">Failed to load flow data.</p>
  }

  const isClosedWon = flow.current_stage === 'closed_won'
  const isClosedLost = flow.current_stage === 'closed_lost'

  return (
    <div className="space-y-8">
      {/* Stage Pipeline */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Pipeline Progress</h3>
        <div className="flex items-center gap-0 overflow-x-auto pb-2">
          {flow.stages.map((stage, idx) => {
            const isLast = idx === flow.stages.length - 1
            let colorClass = STAGE_COLORS.pending
            if (stage.current) colorClass = STAGE_COLORS.current
            else if (stage.completed) colorClass = STAGE_COLORS.completed

            const isWon = stage.key === 'closed_won'
            const isLost = stage.key === 'closed_lost'

            return (
              <div key={stage.key} className="flex items-center shrink-0">
                {/* Node */}
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors ${colorClass} ${
                      isWon && stage.completed ? '!bg-green-600 !border-green-600 !text-white' : ''
                    } ${
                      isLost && stage.completed ? '!bg-red-500 !border-red-500 !text-white' : ''
                    }`}
                  >
                    {stage.completed && !stage.current ? '✓' : idx + 1}
                  </div>
                  <span
                    className={`text-xs text-center max-w-[72px] leading-tight ${
                      stage.current ? 'font-semibold text-indigo-600' : 'text-gray-500'
                    }`}
                  >
                    {stage.label}
                  </span>
                </div>
                {/* Connector */}
                {!isLast && (
                  <div
                    className={`h-0.5 w-8 mx-1 shrink-0 ${
                      stage.completed && !stage.current ? 'bg-indigo-400' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>

        {/* Paused warning */}
        {flow.auto_flow_paused && (
          <div className="mt-3 text-xs bg-yellow-50 border border-yellow-200 text-yellow-800 rounded-lg px-3 py-2">
            Auto-flow is paused for this lead — automated emails and follow-ups are suspended.
          </div>
        )}

        {/* Closed banner */}
        {(isClosedWon || isClosedLost) && (
          <div
            className={`mt-3 text-sm font-semibold rounded-xl px-4 py-3 text-center ${
              isClosedWon
                ? 'bg-green-50 border border-green-200 text-green-700'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}
          >
            {isClosedWon ? 'Deal Closed — Won' : 'Deal Closed — Lost'}
          </div>
        )}
      </div>

      {/* Timeline */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-4">
          Journey Timeline
          <span className="ml-2 text-xs font-normal text-gray-400">
            ({flow.timeline.length} action{flow.timeline.length !== 1 ? 's' : ''})
          </span>
        </h3>

        {flow.timeline.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">
            No actions recorded yet.
          </p>
        ) : (
          <ol className="relative border-l-2 border-gray-200 ml-3 space-y-5">
            {flow.timeline.map((item) => {
              const colorClass = ACTION_COLORS[item.action_type] || 'bg-gray-100 text-gray-600 border-gray-200'
              const label = ACTION_LABELS[item.action_type] || item.action_type

              return (
                <li key={item.id} className="ml-5">
                  {/* Dot */}
                  <span className="absolute -left-2 flex items-center justify-center w-4 h-4 rounded-full bg-white border-2 border-gray-300" />

                  <div className="bg-white border border-gray-100 rounded-xl px-4 py-3 shadow-sm">
                    <div className="flex items-center justify-between flex-wrap gap-2 mb-1">
                      <span
                        className={`text-xs font-semibold px-2 py-0.5 rounded border ${colorClass}`}
                      >
                        {label}
                      </span>
                      <span className="text-xs text-gray-400">{formatDate(item.created_at)}</span>
                    </div>
                    {item.notes && (
                      <p className="text-xs text-gray-600 mt-1 whitespace-pre-wrap">{item.notes}</p>
                    )}
                    <p className="text-xs text-gray-400 mt-1">
                      {item.is_automated ? 'System (automated)' : item.performed_by || 'Unknown'}
                    </p>
                  </div>
                </li>
              )
            })}
          </ol>
        )}
      </div>
    </div>
  )
}
