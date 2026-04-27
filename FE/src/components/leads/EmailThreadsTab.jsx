import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLeadThreads } from '../../api/leads'

const THREAD_TYPE_LABELS = {
  intro:       'Intro',
  pricing:     'Pricing',
  followup:    'Follow-Up',
  negotiation: 'Negotiation',
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

export default function EmailThreadsTab({ leadId }) {
  const [openThreadId, setOpenThreadId] = useState(null)

  const { data: threads = [], isLoading } = useQuery({
    queryKey: ['lead-threads', leadId],
    queryFn: () => getLeadThreads(leadId),
  })

  if (isLoading) return <p className="text-sm text-gray-400 py-4">Loading threads…</p>

  if (threads.length === 0) {
    return (
      <p className="text-sm text-gray-400 text-center py-8">
        No emails sent yet. Use the Send Email action in Phase 4 to send intro emails.
      </p>
    )
  }

  return (
    <div className="space-y-2">
      {threads.map((thread) => (
        <div key={thread.id} className="border border-gray-200 rounded-xl overflow-hidden">
          <button
            onClick={() => setOpenThreadId(openThreadId === thread.id ? null : thread.id)}
            className="w-full flex items-center justify-between px-4 py-3 bg-white hover:bg-gray-50 text-left"
          >
            <div>
              <span className="text-sm font-semibold text-gray-900">{thread.subject}</span>
              <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-medium">
                {THREAD_TYPE_LABELS[thread.thread_type] || thread.thread_type}
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span>{thread.messages.length} msg{thread.messages.length !== 1 ? 's' : ''}</span>
              <span>{thread.contact_name}</span>
              <span>{openThreadId === thread.id ? '▲' : '▼'}</span>
            </div>
          </button>

          {openThreadId === thread.id && (
            <div className="border-t border-gray-100 divide-y divide-gray-100">
              {thread.messages.length === 0 ? (
                <p className="px-4 py-3 text-xs text-gray-400">No messages in this thread.</p>
              ) : (
                thread.messages.map((msg) => (
                  <div key={msg.id} className={`px-4 py-3 ${msg.direction === 'inbound' ? 'bg-blue-50' : 'bg-white'}`}>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-semibold ${msg.direction === 'inbound' ? 'text-blue-700' : 'text-gray-700'}`}>
                        {msg.direction === 'inbound' ? '← Received' : '→ Sent'}
                      </span>
                      <span className="text-xs text-gray-400">{formatDate(msg.sent_at)}</span>
                    </div>
                    <p className="text-xs text-gray-700 whitespace-pre-wrap leading-relaxed line-clamp-4">
                      {msg.body_text || '(No text content)'}
                    </p>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
