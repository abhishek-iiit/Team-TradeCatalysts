import api from './axios'

export const listProducts = () =>
  api.get('/products/').then((r) => r.data)

export const createProduct = (data) =>
  api.post('/products/', data).then((r) => r.data)

export const updateProduct = (id, data) =>
  api.patch(`/products/${id}/`, data).then((r) => r.data)

export const uploadBrochure = (id, file) => {
  const form = new FormData()
  form.append('brochure_pdf', file)
  return api.patch(`/products/${id}/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const deleteProduct = (id) =>
  api.delete(`/products/${id}/`).then((r) => r.data)
