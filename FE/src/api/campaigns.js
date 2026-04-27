import api from './axios'

export const listCampaigns = () =>
  api.get('/campaigns/').then((r) => r.data)

export const createCampaign = (data) =>
  api.post('/campaigns/', data).then((r) => r.data)

export const getCampaign = (id) =>
  api.get(`/campaigns/${id}/`).then((r) => r.data)

export const getCampaignLeads = (id, stage) =>
  api.get(`/campaigns/${id}/leads/`, { params: stage ? { stage } : {} }).then((r) => r.data)

export const exportMissingContacts = (id) =>
  api.post(`/campaigns/${id}/export-missing/`, {}, { responseType: 'blob' }).then((r) => {
    const url = window.URL.createObjectURL(new Blob([r.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `missing-contacts-${id}.csv`)
    document.body.appendChild(link)
    link.click()
    link.remove()
  })
