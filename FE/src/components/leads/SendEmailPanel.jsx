import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { sendIntroEmail, sendPricingEmail } from '../../api/leads'

export default function SendEmailPanel({ lead }) {
  const qc = useQueryClient()
  const [queued, setQueued] = useState(false)

  const primaryContact =
    lead.contacts?.find((c) => c.is_primary && c.email) ||
    lead.contacts?.find((c) => c.email)

  const introMutation = useMutation({
    mutationFn: () => sendIntroEmail(lead.id),
    onSuccess: () => {
      setQueued(true)
      qc.invalidateQueries({ queryKey: ['lead', lead.id] })
    },
  })

  const pricingMutation = useMutation({
    mutationFn: () => sendPricingEmail(lead.id),
    onSuccess: () => {
      setQueued(true)
      qc.invalidateQueries({ queryKey: ['lead', lead.id] })
    },
  })

  const canSendIntro = lead.stage === 'discovered'
  const canSendPricing = lead.stage === 'intro_sent'

  if (!primaryContact || (!canSendIntro && !canSendPricing)) return null

  if (queued) {
    return (
      <div className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2 whitespace-nowrap">
        Email queued → {primaryContact.email}
      </div>
    )
  }

  const mutation = canSendIntro ? introMutation : pricingMutation
  const label = canSendIntro ? 'Send Intro Email' : 'Send Pricing Email'

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={() => mutation.mutate()}
        disabled={mutation.isPending || lead.auto_flow_paused}
        className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors whitespace-nowrap"
      >
        {mutation.isPending ? 'Queuing…' : label}
      </button>
      {lead.auto_flow_paused && (
        <p className="text-xs text-yellow-700">Auto-flow paused</p>
      )}
    </div>
  )
}
