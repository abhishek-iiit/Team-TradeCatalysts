import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { listCampaigns } from '../api/campaigns'

export default function CampaignsListPage() {
  const navigate = useNavigate()
  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: listCampaigns,
  })

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
        <button
          onClick={() => navigate('/campaigns/new')}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-lg"
        >
          + New Campaign
        </button>
      </div>
      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <div
              key={c.id}
              onClick={() => navigate(`/campaigns/${c.id}/leads`)}
              className="bg-white border border-gray-200 rounded-xl p-5 flex items-center justify-between cursor-pointer hover:border-indigo-300 transition-colors"
            >
              <div>
                <p className="font-semibold text-gray-900">{c.title}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {c.products?.map((p) => p.name).join(', ')} · {c.country_filters?.join(', ')}
                </p>
              </div>
              <div className="flex items-center gap-3">
                {c.created_by_email && (
                  <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                    {c.created_by_email}
                  </span>
                )}
                <span className="text-sm font-semibold text-indigo-600">{c.lead_count} leads</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  c.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                }`}>{c.status}</span>
              </div>
            </div>
          ))}
          {campaigns.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-12">No campaigns yet. Create your first one.</p>
          )}
        </div>
      )}
    </div>
  )
}
