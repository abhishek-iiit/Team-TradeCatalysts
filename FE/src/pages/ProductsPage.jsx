import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listProducts, createProduct, deleteProduct } from '../api/products'
import StageConfigPanel from '../components/products/StageConfigPanel'

export default function ProductsPage() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', hsn_code: '', cas_number: '', description: '' })
  const [error, setError] = useState('')
  const [expandedProduct, setExpandedProduct] = useState(null)

  const { data: products = [], isLoading } = useQuery({
    queryKey: ['products'],
    queryFn: listProducts,
  })

  const createMutation = useMutation({
    mutationFn: createProduct,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] })
      setShowForm(false)
      setForm({ name: '', hsn_code: '', cas_number: '', description: '' })
      setError('')
    },
    onError: (err) => setError(err.response?.data?.name?.[0] || 'Failed to create product'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })

  function handleSubmit(e) {
    e.preventDefault()
    createMutation.mutate(form)
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Products</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold px-4 py-2 rounded-lg transition-colors"
        >
          {showForm ? 'Cancel' : '+ Add Product'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white border border-gray-200 rounded-xl p-6 mb-6 space-y-4">
          <h2 className="font-semibold text-gray-800">New Product</h2>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Product Name *</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="Acetone" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">HSN Code *</label>
              <input required value={form.hsn_code} onChange={(e) => setForm({ ...form, hsn_code: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="29141100" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">CAS Number</label>
              <input value={form.cas_number} onChange={(e) => setForm({ ...form, cas_number: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" placeholder="67-64-1" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <button type="submit" disabled={createMutation.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-sm font-semibold px-4 py-2 rounded-lg">
            {createMutation.isPending ? 'Saving…' : 'Save Product'}
          </button>
        </form>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="space-y-3">
          {products.map((product) => (
            <div key={product.id} className="bg-white border border-gray-200 rounded-xl overflow-hidden">
              <div className="p-5 flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">{product.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">HSN: {product.hsn_code} · CAS: {product.cas_number}</p>
                </div>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => setExpandedProduct(expandedProduct === product.id ? null : product.id)}
                    className="text-xs bg-indigo-50 text-indigo-700 hover:bg-indigo-100 px-2 py-0.5 rounded-full font-medium transition-colors"
                  >
                    {expandedProduct === product.id ? 'Hide Stages ▲' : 'Email Stages ▼'}
                  </button>
                  <button onClick={() => {
                    if (window.confirm(`Delete "${product.name}"?`)) deleteMutation.mutate(product.id)
                  }} className="text-xs text-red-500 hover:text-red-700">Delete</button>
                </div>
              </div>
              {expandedProduct === product.id && (
                <div className="border-t border-gray-100 px-5 pb-5">
                  <StageConfigPanel productId={product.id} />
                </div>
              )}
            </div>
          ))}
          {products.length === 0 && (
            <p className="text-center text-gray-400 text-sm py-12">No products yet. Add your first product above.</p>
          )}
        </div>
      )}
    </div>
  )
}
