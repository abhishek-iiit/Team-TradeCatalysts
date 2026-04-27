import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { listProducts } from '../api/products'
import { createCampaign } from '../api/campaigns'

const COUNTRIES = [
  { code: 'IN', name: 'India' }, { code: 'US', name: 'United States' },
  { code: 'CN', name: 'China' }, { code: 'DE', name: 'Germany' },
  { code: 'GB', name: 'United Kingdom' }, { code: 'JP', name: 'Japan' },
  { code: 'KR', name: 'South Korea' }, { code: 'FR', name: 'France' },
  { code: 'IT', name: 'Italy' }, { code: 'NL', name: 'Netherlands' },
  { code: 'SG', name: 'Singapore' }, { code: 'AE', name: 'UAE' },
  { code: 'BR', name: 'Brazil' }, { code: 'CA', name: 'Canada' },
  { code: 'AU', name: 'Australia' }, { code: 'MX', name: 'Mexico' },
]

export default function NewCampaignPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [selectedProducts, setSelectedProducts] = useState([])
  const [selectedCountries, setSelectedCountries] = useState([])
  const [numTransactions, setNumTransactions] = useState('')
  const [dataYear, setDataYear] = useState('2025')
  const [countrySearch, setCountrySearch] = useState('')
  const [error, setError] = useState('')

  const { data: products = [] } = useQuery({ queryKey: ['products'], queryFn: listProducts })

  const mutation = useMutation({
    mutationFn: createCampaign,
    onSuccess: (data) => navigate(`/campaigns/${data.id}/leads`),
    onError: () => setError('Failed to create campaign. Please try again.'),
  })

  function toggleProduct(id) {
    setSelectedProducts((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    )
  }

  function toggleAllProducts() {
    setSelectedProducts((prev) =>
      prev.length === products.length ? [] : products.map((p) => p.id)
    )
  }

  function toggleCountry(code) {
    setSelectedCountries((prev) =>
      prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]
    )
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!selectedProducts.length) return setError('Select at least one product.')
    if (!selectedCountries.length) return setError('Select at least one country.')
    setError('')
    mutation.mutate({
      title: title || `Campaign ${new Date().toLocaleDateString()}`,
      product_ids: selectedProducts,
      country_filters: selectedCountries,
      num_transactions_yr: parseInt(numTransactions) || 0,
      data_year: parseInt(dataYear) || 2025,
    })
  }

  const filteredCountries = COUNTRIES.filter((c) =>
    c.name.toLowerCase().includes(countrySearch.toLowerCase())
  )

  const allCountriesSelected = filteredCountries.length > 0 && filteredCountries.every((c) => selectedCountries.includes(c.code))
  const someCountriesSelected = filteredCountries.some((c) => selectedCountries.includes(c.code)) && !allCountriesSelected

  function toggleAllCountries() {
    setSelectedCountries((prev) =>
      allCountriesSelected ? prev.filter((code) => !filteredCountries.some((c) => c.code === code)) : [...new Set([...prev, ...filteredCountries.map((c) => c.code)])]
    )
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">New Campaign</h1>
      <p className="text-sm text-gray-500 mb-6">Search for buyer leads by product and target countries.</p>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Title (optional)</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. India Acetone Q2 2026" />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-gray-700">Products *</label>
              {products.length > 0 && (
                <label className="flex items-center gap-1.5 cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                  <input
                    type="checkbox"
                    checked={selectedProducts.length === products.length}
                    onChange={toggleAllProducts}
                    className="rounded border-gray-300"
                  />
                  Select all
                </label>
              )}
            </div>
            {products.length === 0 ? (
              <p className="text-sm text-yellow-600">No products found. <a href="/products" className="underline">Add one first.</a></p>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {products.map((p) => (
                  <label key={p.id} className={`flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedProducts.includes(p.id) ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:bg-gray-50'
                  }`}>
                    <input type="checkbox" checked={selectedProducts.includes(p.id)} onChange={() => toggleProduct(p.id)}
                      className="rounded border-gray-300" />
                    <span className="text-sm font-medium text-gray-800">{p.name}</span>
                    <span className="text-xs text-gray-400 ml-auto">{p.hsn_code}</span>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="flex items-end gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min. Transactions / Year</label>
              <input type="number" min="0" value={numTransactions} onChange={(e) => setNumTransactions(e.target.value)}
                className="w-40 border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="0" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Data Year</label>
              <select value={dataYear} onChange={(e) => setDataYear(e.target.value)}
                className="w-36 border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white">
                {[2025, 2024, 2023, 2022].map((y) => (
                  <option key={y} value={y}>{y}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-gray-700">Target Countries *</label>
            <label className="flex items-center gap-1.5 cursor-pointer text-xs text-gray-500 hover:text-gray-700">
              <input
                type="checkbox"
                checked={allCountriesSelected}
                ref={(el) => { if (el) el.indeterminate = someCountriesSelected }}
                onChange={toggleAllCountries}
                className="rounded border-gray-300"
              />
              {allCountriesSelected ? 'Deselect all' : 'Select all'}
            </label>
          </div>
          <input value={countrySearch} onChange={(e) => setCountrySearch(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-3"
            placeholder="Search countries…" />
          <div className="grid grid-cols-3 gap-2 max-h-52 overflow-y-auto">
            {filteredCountries.map((c) => (
              <label key={c.code} className={`flex items-center gap-2 p-2 rounded-lg border cursor-pointer transition-colors text-sm ${
                selectedCountries.includes(c.code) ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200 hover:bg-gray-50'
              }`}>
                <input type="checkbox" checked={selectedCountries.includes(c.code)} onChange={() => toggleCountry(c.code)}
                  className="rounded border-gray-300" />
                <span className="font-medium text-gray-700">{c.code}</span>
                <span className="text-gray-400 text-xs">{c.name}</span>
              </label>
            ))}
          </div>
          {selectedCountries.length > 0 && (
            <p className="text-xs text-indigo-600 mt-2">{selectedCountries.length} selected: {selectedCountries.join(', ')}</p>
          )}
        </div>

        <button type="submit" disabled={mutation.isPending}
          className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-semibold py-3 rounded-xl text-sm transition-colors">
          {mutation.isPending ? 'Starting search…' : 'Search Leads'}
        </button>
      </form>
    </div>
  )
}
