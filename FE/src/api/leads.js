import api from './axios'

export const getLead = (id) =>
  api.get(`/leads/${id}/`).then((r) => r.data)

export const patchLead = (id, data) =>
  api.patch(`/leads/${id}/`, data).then((r) => r.data)

export const getLeadActions = (id) =>
  api.get(`/leads/${id}/actions/`).then((r) => r.data)

export const logLeadAction = (id, data) =>
  api.post(`/leads/${id}/actions/`, data).then((r) => r.data)

export const getLeadThreads = (id) =>
  api.get(`/leads/${id}/threads/`).then((r) => r.data)

export const getDashboardStats = () =>
  api.get('/dashboard/').then((r) => r.data)

export const sendIntroEmail = (id) =>
  api.post(`/leads/${id}/send-intro/`).then((r) => r.data)

export const sendPricingEmail = (id) =>
  api.post(`/leads/${id}/send-pricing/`).then((r) => r.data)

export const bulkSendIntroEmail = (leadIds) =>
  api.post('/leads/bulk-send-intro/', { lead_ids: leadIds }).then((r) => r.data)

export const generateDraft = (id) =>
  api.post(`/leads/${id}/generate-draft/`).then((r) => r.data)
