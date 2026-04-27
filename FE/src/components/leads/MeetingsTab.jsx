import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listLeadMeetings, updateMeeting } from '../../api/meetings'
import ScheduleMeetingForm from './ScheduleMeetingForm'

const STATUS_STYLES = {
  proposed:  'bg-yellow-100 text-yellow-700',
  confirmed: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  cancelled: 'bg-red-100 text-red-700',
}

function formatMeetingDate(isoString) {
  return new Date(isoString).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function MeetingCard({ meeting, leadId }) {
  const qc = useQueryClient()

  const updateMutation = useMutation({
    mutationFn: (newStatus) => updateMeeting(meeting.id, { status: newStatus }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lead-meetings', leadId] }),
  })

  const badgeClass = STATUS_STYLES[meeting.status] || 'bg-gray-100 text-gray-600'
  const statusLabel = meeting.status.charAt(0).toUpperCase() + meeting.status.slice(1)

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="text-sm font-semibold text-gray-900">
            {formatMeetingDate(meeting.scheduled_at)}
          </span>
          <span className={`ml-2 text-xs px-1.5 py-0.5 rounded font-medium ${badgeClass}`}>
            {statusLabel}
          </span>
        </div>
        <span className="text-xs text-gray-400">{meeting.contact_name}</span>
      </div>

      {/^https?:\/\//.test(meeting.meeting_link) && (
        <a
          href={meeting.meeting_link}
          target="_blank"
          rel="noreferrer"
          className="text-xs text-indigo-600 hover:underline block mb-2 truncate"
        >
          {meeting.meeting_link}
        </a>
      )}

      {meeting.notes && (
        <p className="text-xs text-gray-500 mb-3 whitespace-pre-wrap">{meeting.notes}</p>
      )}

      <div className="flex gap-2">
        {meeting.status === 'proposed' && (
          <>
            <button
              onClick={() => updateMutation.mutate('confirmed')}
              disabled={updateMutation.isPending}
              className="text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 px-2.5 py-1 rounded-lg font-medium disabled:opacity-50"
            >
              Confirm
            </button>
            <button
              onClick={() => updateMutation.mutate('cancelled')}
              disabled={updateMutation.isPending}
              className="text-xs bg-red-50 text-red-600 hover:bg-red-100 px-2.5 py-1 rounded-lg font-medium disabled:opacity-50"
            >
              Cancel
            </button>
          </>
        )}
        {meeting.status === 'confirmed' && (
          <button
            onClick={() => updateMutation.mutate('completed')}
            disabled={updateMutation.isPending}
            className="text-xs bg-green-100 text-green-700 hover:bg-green-200 px-2.5 py-1 rounded-lg font-medium disabled:opacity-50"
          >
            Mark Completed
          </button>
        )}
      </div>
    </div>
  )
}

export default function MeetingsTab({ lead }) {
  const [showForm, setShowForm] = useState(false)

  const { data: meetings = [], isLoading } = useQuery({
    queryKey: ['lead-meetings', lead.id],
    queryFn: () => listLeadMeetings(lead.id),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">
          {meetings.length} meeting{meetings.length !== 1 ? 's' : ''}
        </span>
        <button
          onClick={() => setShowForm(!showForm)}
          className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-3 py-1.5 rounded-lg transition-colors"
        >
          {showForm ? 'Cancel' : '+ Schedule Meeting'}
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
          <ScheduleMeetingForm lead={lead} onScheduled={() => setShowForm(false)} />
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400 text-center py-4">Loading meetings…</p>
      ) : meetings.length === 0 && !showForm ? (
        <p className="text-sm text-gray-400 text-center py-8">
          No meetings scheduled yet.
        </p>
      ) : (
        <div className="space-y-3">
          {meetings.map((m) => (
            <MeetingCard key={m.id} meeting={m} leadId={lead.id} />
          ))}
        </div>
      )}
    </div>
  )
}
