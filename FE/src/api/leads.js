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
