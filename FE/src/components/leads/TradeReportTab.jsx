const TREND_CONFIG = {
  rising:  { label: 'Rising',  cls: 'text-green-600 bg-green-50' },
  falling: { label: 'Falling', cls: 'text-red-600 bg-red-50' },
  stable:  { label: 'Stable',  cls: 'text-blue-600 bg-blue-50' },
}

function fmt(n) {
  return n?.toLocaleString('en-US') ?? '—'
}

export default function TradeReportTab({ lead }) {
  const records = lead?.volza_data?.trade_records || []
  const trend = lead?.pricing_trend || {}
  const trendCfg = TREND_CONFIG[trend.direction] || { label: trend.direction, cls: 'text-gray-600 bg-gray-50' }

  return (
    <div className="space-y-4">
      {/* Pricing trend summary */}
      {trend.avg_usd_per_mt && (
        <div className="flex items-center gap-4 bg-white border border-gray-200 rounded-xl p-4">
          <div>
            <p className="text-xs text-gray-500">Avg. Unit Price</p>
            <p className="text-lg font-bold text-gray-900">${fmt(trend.avg_usd_per_mt)} / MT</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">YoY Change</p>
            <p className={`text-sm font-semibold ${trend.yoy_change_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {trend.yoy_change_pct >= 0 ? '+' : ''}{trend.yoy_change_pct}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Trend</p>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${trendCfg.cls}`}>
              {trendCfg.label}
            </span>
          </div>
          <div className="ml-auto">
            <p className="text-xs text-gray-500">Total Transactions</p>
            <p className="text-sm font-bold text-gray-700">{lead.volza_data?.num_transactions ?? '—'}</p>
          </div>
        </div>
      )}

      {/* Shipment records table */}
      {records.length === 0 ? (
        <p className="text-sm text-gray-400 py-6 text-center">No trade records available.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-gray-200">
          <table className="min-w-full text-xs bg-white">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {[
                  'Date',
                  'Buyer Country',
                  'Destination Port',
                  'Seller Country',
                  'Seller Origin',
                  'Port of Loading',
                  'Seller',
                  'Unit',
                  'Quantity',
                  'Value (USD)',
                  'Unit Price',
                ].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left font-semibold text-gray-600 whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {records.map((r, i) => (
                <tr key={i} className="hover:bg-gray-50">
                  <td className="px-3 py-2 text-gray-700 whitespace-nowrap">{r.date}</td>
                  <td className="px-3 py-2 text-gray-700">{r.buyer_country}</td>
                  <td className="px-3 py-2 text-gray-700 whitespace-nowrap">{r.destination_port}</td>
                  <td className="px-3 py-2 text-gray-700">{r.seller_country}</td>
                  <td className="px-3 py-2 text-gray-700">{r.seller_origin}</td>
                  <td className="px-3 py-2 text-gray-700 whitespace-nowrap">{r.port_of_loading}</td>
                  <td className="px-3 py-2 text-gray-600 whitespace-nowrap">{r.seller_name}</td>
                  <td className="px-3 py-2 text-gray-700 text-center">{r.unit}</td>
                  <td className="px-3 py-2 text-gray-700 text-right font-medium">{fmt(r.quantity)}</td>
                  <td className="px-3 py-2 text-gray-700 text-right font-medium">${fmt(r.value_usd)}</td>
                  <td className="px-3 py-2 text-gray-700 text-right font-medium">${fmt(r.unit_price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
