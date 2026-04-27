import { useState, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { previewPanjiva, importLeads, exploreTradeData } from '../api/tradeData'
import { listCampaigns } from '../api/campaigns'

// ─── Import Tab ──────────────────────────────────────────────────────────────

function UploadStep({ onParsed }) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef()

  const mutation = useMutation({
    mutationFn: previewPanjiva,
    onSuccess: (data) => onParsed(data),
  })

  function handleFile(file) {
    if (!file) return
    mutation.mutate(file)
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Upload a Panjiva / ex-im spreadsheet. Accepted formats: <strong>.csv</strong>, <strong>.xlsx</strong>.
        Supports both <em>shipment</em> (BUYER column) and <em>consignee</em> (Consignee column) exports.
      </p>

      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFile(e.dataTransfer.files[0])
        }}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          dragging ? 'border-indigo-400 bg-indigo-50' : 'border-gray-300 hover:border-indigo-300 hover:bg-gray-50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        <svg className="w-10 h-10 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        {mutation.isPending ? (
          <p className="text-sm text-indigo-600 font-medium">Parsing file…</p>
        ) : (
          <>
            <p className="text-sm font-medium text-gray-700">Drop file here or click to browse</p>
            <p className="text-xs text-gray-400 mt-1">CSV or Excel (.xlsx)</p>
          </>
        )}
      </div>

      {mutation.isError && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
          {mutation.error?.response?.data?.error || 'Failed to parse file.'}
        </p>
      )}
    </div>
  )
}

function PreviewStep({ parsed, onBack, onImported }) {
  const { data: campaigns, isLoading: loadingCampaigns } = useQuery({
    queryKey: ['campaigns'],
    queryFn: listCampaigns,
  })

  const [campaignId, setCampaignId] = useState('')
  const [result, setResult] = useState(null)

  const mutation = useMutation({
    mutationFn: () => importLeads(parsed.rows, campaignId),
    onSuccess: (data) => {
      setResult(data)
      onImported(data)
    },
  })

  const preview = parsed.preview || []

  const hasContacts = preview.some((r) => r.contacts?.length > 0)
  const hasHistory = preview.some((r) => r.purchase_history?.length > 0)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-800">
            {parsed.count} lead{parsed.count !== 1 ? 's' : ''} extracted
          </p>
          <p className="text-xs text-gray-500">Showing first {preview.length} rows below</p>
        </div>
        <button onClick={onBack} className="text-xs text-gray-500 hover:text-gray-700 underline">
          ← Upload different file
        </button>
      </div>

      {/* Preview table */}
      <div className="overflow-x-auto rounded-xl border border-gray-200">
        <table className="min-w-full text-xs bg-white">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-3 py-2.5 text-left font-semibold text-gray-600 whitespace-nowrap">Company</th>
              <th className="px-3 py-2.5 text-left font-semibold text-gray-600">Country</th>
              <th className="px-3 py-2.5 text-left font-semibold text-gray-600">Website</th>
              {hasContacts && <th className="px-3 py-2.5 text-left font-semibold text-gray-600">Contacts</th>}
              {hasHistory && <th className="px-3 py-2.5 text-left font-semibold text-gray-600">Shipments</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {preview.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-3 py-2 font-medium text-gray-800 whitespace-nowrap">{row.company_name}</td>
                <td className="px-3 py-2 text-gray-600">{row.company_country || '—'}</td>
                <td className="px-3 py-2 text-gray-600 max-w-[160px] truncate">{row.company_website || '—'}</td>
                {hasContacts && (
                  <td className="px-3 py-2 text-gray-600">
                    {row.contacts?.length
                      ? row.contacts.slice(0, 2).map((c, j) => (
                          <span key={j} className="block truncate max-w-[200px]">{c.email || c.phone}</span>
                        ))
                      : '—'}
                  </td>
                )}
                {hasHistory && (
                  <td className="px-3 py-2 text-gray-600 text-center">{row.purchase_history?.length || 0}</td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Campaign selector + import */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
        <p className="text-sm font-semibold text-gray-700">Select target campaign</p>
        <select
          value={campaignId}
          onChange={(e) => setCampaignId(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          disabled={loadingCampaigns}
        >
          <option value="">— choose campaign —</option>
          {(campaigns?.results || campaigns || []).map((c) => (
            <option key={c.id} value={c.id}>{c.title}</option>
          ))}
        </select>

        {result ? (
          <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-700">
            Import complete — <strong>{result.created}</strong> leads created
            {result.skipped > 0 && `, ${result.skipped} skipped (already in campaign)`}.
          </div>
        ) : (
          <button
            onClick={() => mutation.mutate()}
            disabled={!campaignId || mutation.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
          >
            {mutation.isPending ? 'Importing…' : `Import ${parsed.count} leads`}
          </button>
        )}

        {mutation.isError && (
          <p className="text-xs text-red-600">{mutation.error?.response?.data?.error || 'Import failed.'}</p>
        )}
      </div>
    </div>
  )
}

function ImportTab() {
  const [parsed, setParsed] = useState(null)
  const [imported, setImported] = useState(false)

  if (imported) {
    return (
      <div className="py-16 text-center space-y-3">
        <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto">
          <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-sm font-semibold text-gray-700">Leads imported successfully</p>
        <button
          onClick={() => { setParsed(null); setImported(false) }}
          className="text-sm text-indigo-600 hover:underline"
        >
          Import another file
        </button>
      </div>
    )
  }

  if (parsed) {
    return (
      <PreviewStep
        parsed={parsed}
        onBack={() => setParsed(null)}
        onImported={() => setImported(true)}
      />
    )
  }

  return <UploadStep onParsed={(data) => setParsed(data)} />
}

// ─── Explore Tab ─────────────────────────────────────────────────────────────

function ExploreTab() {
  const [q, setQ] = useState('')
  const [submitted, setSubmitted] = useState('')

  const { data, isFetching, isError } = useQuery({
    queryKey: ['trade-explore', submitted],
    queryFn: () => exploreTradeData(submitted),
    enabled: Boolean(submitted),
  })

  function handleSearch(e) {
    e.preventDefault()
    setSubmitted(q.trim())
  }

  return (
    <div className="space-y-5">
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by product name or HS code…"
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={!q.trim() || isFetching}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          {isFetching ? 'Searching…' : 'Search'}
        </button>
      </form>

      {isError && (
        <p className="text-sm text-red-600">Search failed. Try again.</p>
      )}

      {data && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* Pipeline leads */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Pipeline Leads
              <span className="ml-2 text-xs font-normal text-gray-400">
                ({data.leads?.length ?? 0} found)
              </span>
            </h3>
            {data.leads?.length === 0 ? (
              <p className="text-sm text-gray-400">No leads in pipeline for this product.</p>
            ) : (
              <div className="space-y-2">
                {data.leads.map((lead) => (
                  <div key={lead.id} className="bg-white border border-gray-200 rounded-xl p-3 flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-800 truncate">{lead.company_name}</p>
                      <p className="text-xs text-gray-500">{lead.company_country}</p>
                      {lead.contacts?.length > 0 && (
                        <p className="text-xs text-gray-400 truncate mt-0.5">
                          {lead.contacts[0].email || lead.contacts[0].phone}
                        </p>
                      )}
                    </div>
                    <span className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full ${
                      lead.stage === 'closed_won'
                        ? 'bg-green-100 text-green-700'
                        : lead.stage === 'closed_lost'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-indigo-100 text-indigo-700'
                    }`}>
                      {lead.stage?.replace(/_/g, ' ')}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Volza importers */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">
              Volza Importers
              <span className="ml-2 text-xs font-normal text-gray-400">
                ({data.volza?.length ?? 0} found)
              </span>
            </h3>
            {data.volza?.length === 0 ? (
              <p className="text-sm text-gray-400">No Volza results for this product.</p>
            ) : (
              <div className="space-y-2">
                {data.volza.map((v, i) => (
                  <div key={i} className="bg-white border border-gray-200 rounded-xl p-3">
                    <p className="text-sm font-semibold text-gray-800">{v.company_name}</p>
                    <p className="text-xs text-gray-500">{v.country}</p>
                    {v.contact_email && (
                      <p className="text-xs text-gray-400 mt-0.5">{v.contact_email}</p>
                    )}
                    {v.num_transactions != null && (
                      <p className="text-xs text-gray-400">{v.num_transactions} transactions</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {!submitted && (
        <p className="text-sm text-gray-400 py-8 text-center">
          Enter a product name to see matching leads from your pipeline alongside Volza importer data.
        </p>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

const TABS = ['Import', 'Explore']

export default function TradeDataPage() {
  const [tab, setTab] = useState('Import')

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Trade Data</h1>
      <p className="text-sm text-gray-500 mb-6">
        Import Panjiva / ex-im spreadsheets as leads, or explore product-level data combined with Volza.
      </p>

      {/* Tab switcher */}
      <div className="flex gap-1 bg-gray-100 rounded-lg p-1 w-fit mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
              tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6">
        {tab === 'Import' ? <ImportTab /> : <ExploreTab />}
      </div>
    </div>
  )
}
