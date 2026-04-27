import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getCampaign, getCampaignLeads, exportMissingContacts } from '../api/campaigns'
import { bulkSendIntroEmail } from '../api/leads'
import LeadTable from '../components/leads/LeadTable'
import EnrichmentBanner from '../components/leads/EnrichmentBanner'

const STAGES = [
  { key: '', label: 'All' },
  { key: 'discovered', label: 'Discovered' },
  { key: 'intro_sent', label: 'Intro Sent' },
  { key: 'pricing_sent', label: 'Pricing Sent' },
  { key: 'meeting_set', label: 'Meeting Set' },
  { key: 'closed_won', label: 'Won' },
  { key: 'closed_lost', label: 'Lost' },
]

export default function CampaignLeadsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [activeStage, setActiveStage] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [bulkResult, setBulkResult] = useState(null)

  const bulkMutation = useMutation({
    mutationFn: () => bulkSendIntroEmail([...selected]),
    onSuccess: (data) => {
      setBulkResult(data)
      setSelected(new Set())
      setTimeout(() => setBulkResult(null), 4000)
    },
  })

  const { data: campaign } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => getCampaign(id),
    refetchInterval: (query) => (query.state.data?.lead_count === 0 ? 5000 : false),
  })

  const { data: leads = [], isLoading } = useQuery({
    queryKey: ['campaign-leads', id, activeStage],
    queryFn: () => getCampaignLeads(id, activeStage),
    refetchInterval: (query) => (query.state.data?.length === 0 ? 5000 : false),
  })

  function toggleLead(leadId) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(leadId) ? next.delete(leadId) : next.add(leadId)
      return next
    })
  }

  function toggleAll() {
    if (selected.size === leads.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(leads.map((l) => l.id)))
    }
  }

  const missingCount = leads.filter((l) => l.has_missing_contact).length

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-2">
        <button onClick={() => navigate('/campaigns')} className="text-sm text-gray-400 hover:text-gray-600">← Campaigns</button>
      </div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{campaign?.title || 'Campaign Leads'}</h1>
          <p className="text-sm text-gray-500 mt-0.5">{leads.length} leads found</p>
        </div>
        {missingCount > 0 && (
          <button
            onClick={() => exportMissingContacts(id)}
            className="text-sm bg-yellow-100 text-yellow-800 hover:bg-yellow-200 font-semibold px-4 py-2 rounded-lg transition-colors"
          >
            Export {missingCount} Missing Contacts CSV
          </button>
        )}
      </div>

      <EnrichmentBanner leadCount={leads.length} />

      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {STAGES.map((s) => (
          <button
            key={s.key}
            onClick={() => { setActiveStage(s.key); setSelected(new Set()) }}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
              activeStage === s.key
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {selected.size > 0 && (
        <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 mb-4">
          <span className="text-sm font-medium text-indigo-700">{selected.size} selected</span>
          <button
            onClick={() => navigate(`/leads/${[...selected][0]}`)}
            className="text-sm bg-indigo-600 text-white px-3 py-1.5 rounded-lg font-medium hover:bg-indigo-700"
          >
            View Lead
          </button>
          <button
            onClick={() => bulkMutation.mutate()}
            disabled={bulkMutation.isPending}
            className="text-sm bg-emerald-600 text-white px-3 py-1.5 rounded-lg font-medium hover:bg-emerald-700 disabled:opacity-50"
          >
            {bulkMutation.isPending ? 'Sending…' : 'Send Intro Email'}
          </button>
          {bulkResult && (
            <span className="text-xs text-green-700 font-medium">{bulkResult.queued} emails queued</span>
          )}
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm text-center py-8">Loading leads…</p>
      ) : (
        <LeadTable
          leads={leads}
          selected={selected}
          onToggle={toggleLead}
          onToggleAll={toggleAll}
        />
      )}
    </div>
  )
}
