import api from './axios'

export const previewPanjiva = (file) => {
  const form = new FormData()
  form.append('file', file)
  // Unset the default JSON Content-Type so the browser sets multipart/form-data with boundary
  return api.post('/trade-data/preview/', form, { headers: { 'Content-Type': undefined } }).then((r) => r.data)
}

export const importLeads = (rows, campaignId) =>
  api.post('/trade-data/import/', { rows, campaign_id: campaignId }).then((r) => r.data)

export const exploreTradeData = (q, countries = []) =>
  api
    .get('/trade-data/explore/', { params: { q, ...(countries.length && { countries }) } })
    .then((r) => r.data)
