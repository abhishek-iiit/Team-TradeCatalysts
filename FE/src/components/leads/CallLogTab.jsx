import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { logLeadAction } from '../../api/leads'

const ACTION_TYPES = [
  { value: 'follow_up_call',  label: 'Follow-Up Call' },
  { value: 'note',            label: 'Note' },
  { value: 'manual_takeover', label: 'Manual Takeover' },
]

export default function CallLogTab({ leadId }) {
  const qc = useQueryClient()
  const [actionType, setActionType] = useState('follow_up_call')
  const [notes, setNotes] = useState('')
  const [success, setSuccess] = useState(false)

  const mutation = useMutation({
    mutationFn: (data) => logLeadAction(leadId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', leadId] })
      setNotes('')
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    if (!notes.trim()) return
    mutation.mutate({ action_type: actionType, notes: notes.trim() })
  }

  return (
    <div className="max-w-lg">
      {success && (
        <div className="mb-3 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
          Action logged successfully.
        </div>
      )}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Action Type</label>
          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
          >
            {ACTION_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes *</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            required
            rows={4}
            placeholder="What happened? Key points from the call…"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
          />
        </div>
        <button
          type="submit"
          disabled={mutation.isPending || !notes.trim()}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          {mutation.isPending ? 'Saving…' : 'Log Action'}
        </button>
      </form>
    </div>
  )
}
