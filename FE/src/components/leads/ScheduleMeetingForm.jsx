import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { scheduleMeeting } from '../../api/meetings'

export default function ScheduleMeetingForm({ lead, onScheduled }) {
  const qc = useQueryClient()
  const [scheduledAt, setScheduledAt] = useState('')
  const [contactId, setContactId] = useState('')
  const [notes, setNotes] = useState('')

  const eligibleContacts = lead.contacts?.filter((c) => c.email) || []
  const defaultContactId = eligibleContacts.find((c) => c.is_primary)?.id
    || eligibleContacts[0]?.id
    || ''

  const mutation = useMutation({
    mutationFn: (data) => scheduleMeeting(lead.id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', lead.id] })
      qc.invalidateQueries({ queryKey: ['lead-meetings', lead.id] })
      onScheduled?.()
    },
  })

  function handleSubmit(e) {
    e.preventDefault()
    mutation.mutate({
      scheduled_at: new Date(scheduledAt).toISOString(),
      contact_id: contactId || defaultContactId,
      notes,
    })
  }

  if (eligibleContacts.length === 0) {
    return (
      <p className="text-xs text-gray-400">
        No contacts with email — add a contact to schedule a meeting.
      </p>
    )
  }

  if (mutation.isSuccess) {
    return (
      <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3">
        Meeting scheduled. A calendar invite with the meeting link has been sent to the contact.
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Date & Time *</label>
        <input
          type="datetime-local"
          value={scheduledAt}
          onChange={(e) => setScheduledAt(e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Contact *</label>
        <select
          value={contactId || defaultContactId}
          onChange={(e) => setContactId(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        >
          {eligibleContacts.map((c) => (
            <option key={c.id} value={c.id}>
              {c.first_name} {c.last_name} — {c.email}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Agenda, topics to cover…"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm resize-none"
        />
      </div>
      <button
        type="submit"
        disabled={mutation.isPending || !scheduledAt}
        className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
      >
        {mutation.isPending ? 'Scheduling…' : 'Schedule Meeting'}
      </button>
      {mutation.isError && (
        <p className="text-xs text-red-600">
          {mutation.error?.response?.data?.error || 'Failed to schedule. Please try again.'}
        </p>
      )}
    </form>
  )
}
