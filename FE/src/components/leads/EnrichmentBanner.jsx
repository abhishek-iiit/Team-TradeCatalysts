export default function EnrichmentBanner({ leadCount }) {
  if (leadCount > 0) return null
  return (
    <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-200 rounded-lg px-4 py-3 mb-4">
      <svg className="animate-spin h-4 w-4 text-indigo-500" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <p className="text-sm text-indigo-700 font-medium">
        Enriching leads from Volza and LUSHA… this may take a minute.
      </p>
    </div>
  )
}
