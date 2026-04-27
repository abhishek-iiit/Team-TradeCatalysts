import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { generateDraft } from '../../api/leads'

const ELIGIBLE_STAGES = new Set(['intro_sent', 'pricing_sent', 'pricing_followup', 'meeting_set'])

export default function GenerateDraftButton({ lead }) {
  const [done, setDone] = useState(false)
  const [error, setError] = useState(null)

  const mutation = useMutation({
    mutationFn: () => generateDraft(lead.id),
    onSuccess: () => {
      setDone(true)
      setError(null)
    },
    onError: (err) => {
      setError(err.response?.data?.error || 'Could not queue draft.')
    },
  })

  if (!ELIGIBLE_STAGES.has(lead.stage)) return null

  if (done) {
    return (
      <div className="text-xs text-purple-700 bg-purple-50 border border-purple-200 rounded-lg px-3 py-2 whitespace-nowrap">
        AI draft generating…
      </div>
    )
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending}
        className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
      >
        {mutation.isPending ? 'Queuing…' : 'Generate AI Draft'}
      </button>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
