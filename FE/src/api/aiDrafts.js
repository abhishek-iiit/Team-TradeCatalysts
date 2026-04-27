import api from './axios'

export const listAIDrafts = () => api.get('/ai-drafts/').then((r) => r.data)

export const approveDraft = (id, { content, file } = {}) => {
  const form = new FormData()
  if (content !== undefined) form.append('reply_content', content)
  if (file) form.append('attachment', file)
  return api.post(`/ai-drafts/${id}/approve/`, form).then((r) => r.data)
}

export const rejectDraft = (id) => api.post(`/ai-drafts/${id}/reject/`).then((r) => r.data)
