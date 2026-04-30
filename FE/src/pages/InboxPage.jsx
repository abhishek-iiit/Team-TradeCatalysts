import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listInbox, replyToMessage, togglePause, generateReply } from '../api/inbox'

const STAGE_OPTIONS = [
  { value: '', label: '— Keep current stage —' },
  { value: 'discovered',         label: 'Discovered' },
  { value: 'intro_sent',         label: 'Intro Sent' },
  { value: 'documents_sent',     label: 'Documents Sent' },
  { value: 'requirements_asked', label: 'Requirements Asked' },
  { value: 'pricing_sent',       label: 'Pricing Sent' },
  { value: 'pricing_followup',   label: 'Pricing Follow-Up' },
  { value: 'meeting_sent',       label: 'Meeting Sent' },
  { value: 'deal_sent',          label: 'Deal Sent' },
  { value: 'closed_won',         label: 'Closed Won' },
  { value: 'closed_lost',        label: 'Closed Lost' },
]

const THREAD_LABELS = {
  intro:        'Intro',
  documents:    'Documents',
  requirements: 'Requirements',
  pricing:      'Pricing',
  followup:     'Follow-Up on Pricing',
  meeting:      'Meeting',
  deal:         'Deal',
  negotiation:  'Negotiation',
}

function InboxCard({ message }) {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(true)
  const [replyText, setReplyText] = useState('')
  const [setStage, setSetStage] = useState('')
  const [pauseFlow, setPauseFlow] = useState(false)
  const [sent, setSent] = useState(false)

  const replyMutation = useMutation({
    mutationFn: () => replyToMessage(message.id, {
      reply_content: replyText,
      ...(setStage ? { set_stage: setStage } : {}),
      ...(pauseFlow ? { pause_auto_flow: true } : {}),
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['inbox'] })
      setSent(true)
      setReplyText('')
    },
  })

  const pauseMutation = useMutation({
    mutationFn: () => togglePause(message.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['inbox'] }),
  })

  const generateMutation = useMutation({
    mutationFn: () => generateReply(message.id),
    onSuccess: (data) => setReplyText(data.draft),
  })

  const threadLabel = THREAD_LABELS[message.thread_type] || message.thread_type

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Card header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100 bg-gray-50">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={() => navigate(`/leads/${message.lead_id}`)}
            className="font-semibold text-gray-900 text-sm hover:text-indigo-600 transition-colors truncate"
          >
            {message.lead_company_name}
          </button>
          <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium shrink-0">
            {threadLabel}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 ${
            message.auto_flow_paused
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-green-100 text-green-700'
          }`}>
            {message.auto_flow_paused ? 'Paused' : 'Auto-Flow On'}
          </span>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs text-gray-400">{message.contact_name} · {message.contact_email}</span>
          <span className="text-xs text-gray-300">{new Date(message.sent_at).toLocaleDateString()}</span>
          <button onClick={() => setExpanded(!expanded)} className="text-gray-400 hover:text-gray-600 text-xs">
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {/* Thread subject */}
      <div className="px-5 py-2 border-b border-gray-50 text-xs text-gray-500">
        Re: <span className="font-medium text-gray-700">{message.thread_subject}</span>
        <span className="ml-3 text-gray-400">Stage: <span className="font-medium">{message.lead_stage}</span></span>
      </div>

      {expanded && (
        <div className="px-5 py-4 space-y-4">
          {/* Received message */}
          <div>
            <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Received</p>
            <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-sm text-gray-800 whitespace-pre-wrap max-h-40 overflow-y-auto">
              {message.body_text}
            </div>
          </div>

          {sent ? (
            <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700 font-medium">
              Reply sent successfully.
            </div>
          ) : (
            <>
              {/* Reply textarea */}
              <div>
                <p className="text-xs font-semibold text-gray-500 mb-1 uppercase tracking-wide">Your Reply</p>
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  rows={5}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="Type your reply here…"
                />
              </div>

              {/* Stage + auto flow controls */}
              <div className="flex flex-wrap items-end gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">
                    Set Lead Stage after reply
                  </label>
                  <select
                    value={setStage}
                    onChange={(e) => setSetStage(e.target.value)}
                    className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white"
                  >
                    {STAGE_OPTIONS.map((s) => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>

                <label className="flex items-center gap-2 cursor-pointer mb-1">
                  <input
                    type="checkbox"
                    checked={pauseFlow}
                    onChange={(e) => setPauseFlow(e.target.checked)}
                    className="rounded border-gray-300 accent-yellow-500"
                  />
                  <span className="text-sm text-gray-600">Pause Auto-Flow after reply</span>
                </label>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={() => generateMutation.mutate()}
                  disabled={generateMutation.isPending}
                  className="bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
                >
                  {generateMutation.isPending ? 'Generating…' : '✨ Generate AI Response'}
                </button>

                <button
                  onClick={() => replyMutation.mutate()}
                  disabled={!replyText.trim() || replyMutation.isPending}
                  className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
                >
                  {replyMutation.isPending ? 'Sending…' : 'Send Reply'}
                </button>

                <button
                  onClick={() => pauseMutation.mutate()}
                  disabled={pauseMutation.isPending}
                  className={`text-sm font-semibold px-4 py-2 rounded-lg border transition-colors disabled:opacity-50 ${
                    message.auto_flow_paused
                      ? 'bg-green-50 border-green-300 text-green-700 hover:bg-green-100'
                      : 'bg-yellow-50 border-yellow-300 text-yellow-700 hover:bg-yellow-100'
                  }`}
                >
                  {pauseMutation.isPending
                    ? '…'
                    : message.auto_flow_paused
                    ? 'Resume Auto-Flow'
                    : 'Pause Auto-Flow'}
                </button>

                <button
                  onClick={() => navigate(`/leads/${message.lead_id}`)}
                  className="text-sm text-indigo-600 hover:text-indigo-800 font-medium"
                >
                  Open Lead →
                </button>

                {replyMutation.isError && (
                  <span className="text-xs text-red-600">Send failed. Try again.</span>
                )}
                {generateMutation.isError && (
                  <span className="text-xs text-red-600">AI generation failed. Try again.</span>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

export default function InboxPage() {
  const { data: messages = [], isLoading } = useQuery({
    queryKey: ['inbox'],
    queryFn: listInbox,
    refetchInterval: 20000,
  })

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Inbox</h1>
          <p className="text-sm text-gray-500 mt-1">
            Replies received from leads — review and respond.
          </p>
        </div>
        {messages.length > 0 && (
          <span className="bg-indigo-100 text-indigo-700 text-sm font-semibold px-3 py-1 rounded-full">
            {messages.length} message{messages.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-400 text-center py-12">Loading inbox…</p>
      ) : messages.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl">
          <p className="text-gray-400 text-sm">No inbound messages yet.</p>
          <p className="text-gray-300 text-xs mt-1">Replies from leads will appear here once received.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {messages.map((msg) => (
            <InboxCard key={msg.id} message={msg} />
          ))}
        </div>
      )}
    </div>
  )
}
