import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { closeDeal } from '../../api/deals'

export default function CloseDealModal({ lead, onClose }) {
  const qc = useQueryClient()
  const [outcome, setOutcome] = useState('won')
  const [remarks, setRemarks] = useState('')
  const [dealValue, setDealValue] = useState('')

  const mutation = useMutation({
    mutationFn: (data) => closeDeal(lead.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', lead.id] })
      qc.invalidateQueries({ queryKey: ['lead-flow', lead.id] })
      onClose()
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    mutation.mutate({
      outcome,
      remarks,
      deal_value: dealValue ? parseFloat(dealValue) : null,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Close Deal</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Outcome */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Outcome *</label>
            <div className="flex gap-3">
              <label
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border-2 cursor-pointer text-sm font-semibold transition-colors ${
                  outcome === 'won'
                    ? 'border-green-500 bg-green-50 text-green-700'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="outcome"
                  value="won"
                  checked={outcome === 'won'}
                  onChange={() => setOutcome('won')}
                  className="sr-only"
                />
                Won
              </label>
              <label
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border-2 cursor-pointer text-sm font-semibold transition-colors ${
                  outcome === 'lost'
                    ? 'border-red-400 bg-red-50 text-red-700'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300'
                }`}
              >
                <input
                  type="radio"
                  name="outcome"
                  value="lost"
                  checked={outcome === 'lost'}
                  onChange={() => setOutcome('lost')}
                  className="sr-only"
                />
                Lost
              </label>
            </div>
          </div>

          {/* Deal Value (won only) */}
          {outcome === 'won' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Deal Value (USD)
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={dealValue}
                onChange={(e) => setDealValue(e.target.value)}
                placeholder="e.g. 150000"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
              />
            </div>
          )}

          {/* Remarks */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Remarks</label>
            <textarea
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              rows={3}
              placeholder="Summary of the deal journey…"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
            />
          </div>

          {mutation.isError && (
            <p className="text-xs text-red-600">
              {mutation.error?.response?.data?.error || 'Failed to close deal. Please try again.'}
            </p>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-gray-300 text-gray-600 text-sm font-semibold px-4 py-2 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className={`flex-1 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors disabled:opacity-50 ${
                outcome === 'won'
                  ? 'bg-green-600 hover:bg-green-700'
                  : 'bg-red-500 hover:bg-red-600'
              }`}
            >
              {mutation.isPending ? 'Closing…' : `Mark as ${outcome === 'won' ? 'Won' : 'Lost'}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
