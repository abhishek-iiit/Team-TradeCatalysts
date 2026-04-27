import StageBadge from './StageBadge'

export default function LeadTable({ leads, selected, onToggle, onToggleAll }) {
  const allSelected = leads.length > 0 && selected.size === leads.length

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 w-10">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() => onToggleAll()}
                className="rounded border-gray-300"
              />
            </th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Company</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Country</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Stage</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Primary Contact</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Email</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Phone</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Auto Flow</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {leads.map((lead) => {
            const primary = lead.contacts?.find((c) => c.is_primary) || lead.contacts?.[0]
            const missingContact = lead.has_missing_contact
            return (
              <tr
                key={lead.id}
                className={`hover:bg-gray-50 cursor-pointer ${selected.has(lead.id) ? 'bg-indigo-50' : ''}`}
              >
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selected.has(lead.id)}
                    onChange={() => onToggle(lead.id)}
                    className="rounded border-gray-300"
                  />
                </td>
                <td className="px-4 py-3">
                  <span className="font-medium text-gray-900">{lead.company_name}</span>
                  {lead.created_by_email && (
                    <span className="block text-xs text-gray-400 mt-0.5">{lead.created_by_email}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-500">{lead.company_country}</td>
                <td className="px-4 py-3"><StageBadge stage={lead.stage} /></td>
                <td className="px-4 py-3 text-gray-700">
                  {primary ? `${primary.first_name} ${primary.last_name}`.trim() : '—'}
                  {primary?.designation && (
                    <span className="block text-xs text-gray-400">{primary.designation}</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {primary?.email ? (
                    <span className="text-gray-600 text-xs">{primary.email}</span>
                  ) : (
                    <span className="text-xs text-gray-300">—</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {primary?.phone ? (
                    <span className="text-gray-600 text-xs">{primary.phone}</span>
                  ) : missingContact ? (
                    <span className="inline-flex items-center text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                      Missing
                    </span>
                  ) : (
                    <span className="text-xs text-gray-300">—</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {lead.auto_flow_paused ? (
                    <span className="inline-flex items-center text-xs font-medium text-yellow-700 bg-yellow-50 border border-yellow-200 px-2 py-0.5 rounded-full">
                      Paused
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">
                      On
                    </span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {leads.length === 0 && (
        <p className="text-center text-gray-400 text-sm py-8">No leads yet.</p>
      )}
    </div>
  )
}
