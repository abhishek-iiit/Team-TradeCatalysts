import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getDashboardStats } from '../api/leads'
import { listCampaigns } from '../api/campaigns'

const STAGE_ORDER = [
  { key: 'discovered',       label: 'Discovered',       color: 'bg-gray-400' },
  { key: 'intro_sent',       label: 'Intro Sent',        color: 'bg-blue-400' },
  { key: 'pricing_sent',     label: 'Pricing Sent',      color: 'bg-purple-400' },
  { key: 'pricing_followup', label: 'Pricing Follow-Up', color: 'bg-yellow-400' },
  { key: 'meeting_set',      label: 'Meeting Set',       color: 'bg-indigo-400' },
  { key: 'closed_won',       label: 'Won',               color: 'bg-green-500' },
  { key: 'closed_lost',      label: 'Lost',              color: 'bg-red-400' },
]

function StatCard({ label, value, sub, accent }) {
  return (
    <div className={`bg-white border rounded-xl p-5 ${accent ? 'border-indigo-200' : 'border-gray-200'}`}>
      <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
      <p className={`text-3xl font-bold mt-1 ${accent ? 'text-indigo-600' : 'text-gray-900'}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()

  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
    refetchInterval: 30000,
  })

  const { data: campaigns = [] } = useQuery({
    queryKey: ['campaigns'],
    queryFn: listCampaigns,
  })

  const totalLeads = stats?.total_leads ?? '—'
  const activeCampaigns = stats?.active_campaigns ?? '—'
  const missingContacts = stats?.missing_contact_count ?? '—'
  const wonLeads = stats?.leads_by_stage?.closed_won ?? 0
  const lostLeads = stats?.leads_by_stage?.closed_lost ?? 0

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Dashboard</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Leads" value={totalLeads} accent />
        <StatCard label="Active Campaigns" value={activeCampaigns} />
        <StatCard
          label="Deals Won"
          value={wonLeads}
          sub={lostLeads > 0 ? `${lostLeads} lost` : undefined}
        />
        <StatCard
          label="Missing Contacts"
          value={missingContacts}
          sub="No email or phone"
        />
      </div>

      {/* Stage breakdown */}
      {stats && (
        <div className="bg-white border border-gray-200 rounded-xl p-6 mb-8">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Pipeline Breakdown</h2>
          <div className="space-y-2">
            {STAGE_ORDER.map((s) => {
              const count = stats.leads_by_stage?.[s.key] ?? 0
              const pct = totalLeads > 0 ? Math.round((count / totalLeads) * 100) : 0
              return (
                <div key={s.key} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-36 shrink-0">{s.label}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div
                      className={`${s.color} h-2 rounded-full transition-all`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-600 font-semibold w-8 text-right">{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Recent campaigns */}
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-700">Recent Campaigns</h2>
          <button
            onClick={() => navigate('/campaigns')}
            className="text-xs text-indigo-600 hover:underline"
          >
            View all →
          </button>
        </div>
        {campaigns.length === 0 ? (
          <p className="text-sm text-gray-400">No campaigns yet.</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {campaigns.slice(0, 5).map((c) => (
              <div
                key={c.id}
                onClick={() => navigate(`/campaigns/${c.id}/leads`)}
                className="py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 -mx-2 px-2 rounded"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900">{c.title}</p>
                  <p className="text-xs text-gray-400">{c.country_filters?.join(', ')}</p>
                </div>
                <span className="text-sm font-semibold text-indigo-600">{c.lead_count} leads</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
