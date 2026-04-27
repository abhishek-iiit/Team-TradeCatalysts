import api from './axios'

export const listAIDrafts = () => api.get('/ai-drafts/').then((r) => r.data)
export const approveDraft = (id) => api.post(`/ai-drafts/${id}/approve/`).then((r) => r.data)
export const rejectDraft = (id) => api.post(`/ai-drafts/${id}/reject/`).then((r) => r.data)
