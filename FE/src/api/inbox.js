import api from './axios'

export const listInbox = () =>
  api.get('/inbox/').then((r) => r.data)

export const replyToMessage = (messageId, data) =>
  api.post(`/inbox/${messageId}/reply/`, data).then((r) => r.data)

export const togglePause = (messageId) =>
  api.post(`/inbox/${messageId}/pause/`).then((r) => r.data)
