import api from './axios'

export const closeDeal = (leadId, data) =>
  api.post(`/leads/${leadId}/close/`, data).then((r) => r.data)

export const getLeadFlow = (leadId) =>
  api.get(`/leads/${leadId}/flow/`).then((r) => r.data)

export const listDeals = () =>
  api.get('/deals/').then((r) => r.data)
