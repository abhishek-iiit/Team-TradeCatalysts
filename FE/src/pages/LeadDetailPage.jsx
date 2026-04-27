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
import CloseDealModal from '../components/leads/CloseDealModal'
import FlowVisualization from '../components/leads/FlowVisualization'
import TradeReportTab from '../components/leads/TradeReportTab'

const STAGES = [
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

const DETAIL_TABS = ['Emails', 'Meetings', 'Trade Report', 'Flow', 'Call Log']
const CLOSED_STAGES = ['closed_won', 'closed_lost']

export default function LeadDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState('Trade Report')
  const [showCloseDeal, setShowCloseDeal] = useState(false)

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
    <div className="p-6 max-w-screen-2xl mx-auto">
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
        <div className="flex items-center gap-3 flex-wrap justify-end">
          {!CLOSED_STAGES.includes(lead.stage) && (
            <button
              onClick={() => setShowCloseDeal(true)}
              className="text-sm font-semibold px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Close Deal
            </button>
          )}
          {CLOSED_STAGES.includes(lead.stage) && (
            <span className={`text-xs font-semibold px-3 py-1.5 rounded-lg border ${
              lead.stage === 'closed_won'
                ? 'bg-green-50 border-green-200 text-green-700'
                : 'bg-red-50 border-red-200 text-red-600'
            }`}>
              {lead.stage === 'closed_won' ? 'Won' : 'Lost'}
            </span>
          )}
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
      <div className="my-5">
        <StageProgressBar stage={lead.stage} />
      </div>

      {/* Two-column main layout */}
      <div className="flex gap-5 mt-2 items-start">

        {/* ── Left column: Timeline + Contacts ── */}
        <div className="w-72 shrink-0 space-y-4">
          {/* Timeline */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">Timeline</h2>
            </div>
            <div className="p-4 max-h-[420px] overflow-y-auto">
              <TimelineTab actions={lead.actions || []} />
            </div>
          </div>

          {/* Contacts */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
              <h2 className="text-sm font-semibold text-gray-700">Contacts</h2>
            </div>
            <div className="p-3 space-y-2">
              {lead.contacts && lead.contacts.length > 0 ? (
                lead.contacts.map((c) => <ContactCard key={c.id} contact={c} />)
              ) : (
                <p className="text-xs text-gray-400 py-2 text-center">No contacts yet.</p>
              )}
            </div>
          </div>
        </div>

        {/* ── Right column: Detail tabs ── */}
        <div className="flex-1 min-w-0">
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            {/* Tab bar */}
            <div className="flex border-b border-gray-200 bg-gray-50 px-2 pt-2 gap-1">
              {DETAIL_TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors border-b-2 -mb-px ${
                    activeTab === tab
                      ? 'border-indigo-500 text-indigo-600 bg-white'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="p-4 min-h-[480px]">
              {activeTab === 'Call Log' && <CallLogTab leadId={id} />}
              {activeTab === 'Emails' && <EmailThreadsTab leadId={id} />}
              {activeTab === 'Meetings' && <MeetingsTab lead={lead} />}
              {activeTab === 'Trade Report' && <TradeReportTab lead={lead} />}
              {activeTab === 'Flow' && <FlowVisualization leadId={id} />}
            </div>
          </div>
        </div>
      </div>

      {showCloseDeal && (
        <CloseDealModal lead={lead} onClose={() => setShowCloseDeal(false)} />
      )}
    </div>
  )
}
