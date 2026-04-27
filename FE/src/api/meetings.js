import api from './axios'

export const scheduleMeeting = (leadId, data) =>
  api.post(`/leads/${leadId}/schedule-meeting/`, data).then((r) => r.data)

export const listLeadMeetings = (leadId) =>
  api.get(`/leads/${leadId}/meetings/`).then((r) => r.data)

export const updateMeeting = (meetingId, data) =>
  api.patch(`/meetings/${meetingId}/`, data).then((r) => r.data)
