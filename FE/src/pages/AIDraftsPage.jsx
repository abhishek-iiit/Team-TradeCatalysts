import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listAIDrafts, approveDraft, rejectDraft } from '../api/aiDrafts'

const THREAD_TYPE_LABELS = {
  intro:       'Intro',
  pricing:     'Pricing',
  followup:    'Follow-Up',
  negotiation: 'Negotiation',
}

function DraftCard({ draft }) {
  const qc = useQueryClient()
  const [expanded, setExpanded] = useState(true)
  const [content, setContent] = useState(draft.draft_content)
  const [file, setFile] = useState(null)

  const approveMutation = useMutation({
    mutationFn: () => approveDraft(draft.id, { content, file }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ai-drafts'] })
      setFile(null)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectDraft(draft.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ai-drafts'] }),
  })

  const isPending = approveMutation.isPending || rejectMutation.isPending

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-gray-900 text-sm">{draft.lead_company_name}</span>
          <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded font-medium">
            {THREAD_TYPE_LABELS[draft.thread_type] || draft.thread_type}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 truncate max-w-48">{draft.thread_subject}</span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600 text-xs w-5"
          >
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-5 py-4 space-y-3">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={10}
            className="w-full border border-gray-300 rounded-lg px-4 py-3 text-sm font-mono text-gray-700 leading-relaxed resize-y focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />

          {draft.context_summary && (
            <p className="text-xs text-gray-400 italic">{draft.context_summary}</p>
          )}

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Attachment (optional)</label>
            <label className="inline-flex items-center gap-2 cursor-pointer border border-gray-300 rounded-md px-3 py-1.5 text-sm text-gray-600 bg-white hover:bg-gray-50 transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              {file ? file.name : 'Choose file'}
              <input
                type="file"
                accept=".pdf,.doc,.docx,.png,.jpg"
                className="hidden"
                onChange={(e) => setFile(e.target.files[0] || null)}
              />
            </label>
            {file && (
              <span className="ml-2 text-xs text-indigo-600">{file.name}</span>
            )}
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={() => approveMutation.mutate()}
              disabled={isPending}
              className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {approveMutation.isPending ? 'Sending…' : 'Approve & Send'}
            </button>
            <button
              onClick={() => rejectMutation.mutate()}
              disabled={isPending}
              className="bg-red-50 hover:bg-red-100 disabled:opacity-50 text-red-700 border border-red-200 text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {rejectMutation.isPending ? 'Rejecting…' : 'Reject'}
            </button>
          </div>

          {approveMutation.isError && (
            <p className="text-xs text-red-600">Failed to send. Please try again.</p>
          )}
          {rejectMutation.isError && (
            <p className="text-xs text-red-600">Rejection failed. Please try again.</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function AIDraftsPage() {
  const { data: drafts = [], isLoading } = useQuery({
    queryKey: ['ai-drafts'],
    queryFn: listAIDrafts,
    refetchInterval: 15000,
  })

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">AI Draft Queue</h1>
        <p className="text-sm text-gray-500 mt-1">
          Review and approve AI-generated emails before they are sent to leads.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-400 text-center py-12">Loading drafts…</p>
      ) : drafts.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-gray-200 rounded-xl">
          <p className="text-gray-400 text-sm">No drafts pending review.</p>
          <p className="text-gray-300 text-xs mt-1">
            Open a lead in intro_sent or later stage and click "Generate AI Draft".
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {drafts.map((draft) => (
            <DraftCard key={draft.id} draft={draft} />
          ))}
        </div>
      )}
    </div>
  )
}
