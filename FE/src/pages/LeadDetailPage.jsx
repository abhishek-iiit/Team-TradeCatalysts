import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getLead, patchLead } from '../api/leads'
import StageBadge from '../components/leads/StageBadge'
import StageProgressBar from '../components/leads/StageProgressBar'
import ContactCard from '../components/leads/ContactCard'
import TimelineTab from '../components/leads/TimelineTab'
import CallLogTab from '../components/leads/CallLogTab'
import EmailThreadsTab from '../components/leads/EmailThreadsTab'
import SendEmailPanel from '../components/leads/SendEmailPanel'
import GenerateDraftButton from '../components/leads/GenerateDraftButton'
import MeetingsTab from '../components/leads/MeetingsTab'

const STAGES = [
  { value: 'discovered',       label: 'Discovered' },
  { value: 'intro_sent',       label: 'Intro Sent' },
  { value: 'pricing_sent',     label: 'Pricing Sent' },
  { value: 'pricing_followup', label: 'Pricing Follow-Up' },
  { value: 'meeting_set',      label: 'Meeting Set' },
  { value: 'closed_won',       label: 'Closed Won' },
  { value: 'closed_lost',      label: 'Closed Lost' },
]

const TABS = ['Timeline', 'Call Log', 'Emails', 'Meetings']

export default function LeadDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState('Timeline')

  const { data: lead, isLoading, isError } = useQuery({
    queryKey: ['lead', id],
    queryFn: () => getLead(id),
  })

  const patchMutation = useMutation({
    mutationFn: (data) => patchLead(id, data),
    onSuccess: (updated) => {
      qc.setQueryData(['lead', id], updated)
    },
  })

  if (isLoading) return <div className="p-8 text-gray-400">Loading lead…</div>
  if (isError || !lead) return <div className="p-8 text-red-500">Lead not found.</div>

  function handleStageChange(e) {
    patchMutation.mutate({ stage: e.target.value })
  }

  function togglePause() {
    patchMutation.mutate({ auto_flow_paused: !lead.auto_flow_paused })
  }

  return (
    <div className="p-8 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-gray-400 hover:text-gray-600 mb-4 block"
      >
        ← Back
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{lead.company_name}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {lead.company_country}
            {lead.company_website && (
              <>
                {' · '}
                <a
                  href={lead.company_website}
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-600 hover:underline"
                >
                  {lead.company_website}
                </a>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <GenerateDraftButton lead={lead} />
          <SendEmailPanel lead={lead} />
          <select
            value={lead.stage}
            onChange={handleStageChange}
            disabled={patchMutation.isPending}
            className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm bg-white disabled:opacity-60"
          >
            {STAGES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>

          <button
            onClick={togglePause}
            disabled={patchMutation.isPending}
            className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-colors disabled:opacity-60 ${
              lead.auto_flow_paused
                ? 'bg-yellow-100 border-yellow-300 text-yellow-800 hover:bg-yellow-200'
                : 'bg-gray-100 border-gray-300 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {lead.auto_flow_paused ? 'Paused' : 'Auto-Flow On'}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="my-6">
        <StageProgressBar stage={lead.stage} />
      </div>

      {/* Main layout: content + sidebar */}
      <div className="flex gap-6 mt-4">
        {/* Left: tabs */}
        <div className="flex-1 min-w-0">
          <div className="flex gap-1 border-b border-gray-200 mb-4">
            {TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  activeTab === tab
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === 'Timeline' && (
            <TimelineTab actions={lead.actions || []} />
          )}
          {activeTab === 'Call Log' && (
            <CallLogTab leadId={id} />
          )}
          {activeTab === 'Emails' && (
            <EmailThreadsTab leadId={id} />
          )}
          {activeTab === 'Meetings' && (
            <MeetingsTab lead={lead} />
          )}
        </div>

        {/* Right: contacts sidebar */}
        <div className="w-72 shrink-0 space-y-3">
          <h2 className="text-sm font-semibold text-gray-700">Contacts</h2>
          {lead.contacts && lead.contacts.length > 0 ? (
            lead.contacts.map((c) => <ContactCard key={c.id} contact={c} />)
          ) : (
            <p className="text-xs text-gray-400">No contacts yet.</p>
          )}
        </div>
      </div>
    </div>
  )
}
