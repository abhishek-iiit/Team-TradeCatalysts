import api from './axios'

export async function login(email, password) {
  const { data } = await api.post('/auth/login/', { email, password })
  localStorage.setItem('access_token', data.access)
  localStorage.setItem('refresh_token', data.refresh)
  return data.user
}

export async function logout() {
  const refresh = localStorage.getItem('refresh_token')
  try {
    await api.post('/auth/logout/', { refresh })
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }
}

export async function getMe() {
  const { data } = await api.get('/auth/me/')
  return data
}

export const getEmailSettings = () =>
  api.get('/auth/email-settings/').then((r) => r.data)

export const saveEmailSettings = (data) =>
  api.patch('/auth/email-settings/', data).then((r) => r.data)
