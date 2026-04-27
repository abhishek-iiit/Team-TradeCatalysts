import api from './axios'

export const getStageConfigs = (productId) =>
  api.get(`/products/${productId}/stage-configs/`).then((r) => r.data)

export const saveStageConfig = (id, productId, stage, formData) => {
  if (id) {
    return api.patch(`/stage-configs/${id}/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then((r) => r.data)
  }
  formData.append('product', productId)
  formData.append('stage', stage)
  return api.post('/stage-configs/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}

export const deleteStageConfigDoc = (id) => {
  const form = new FormData()
  form.append('document', '')
  return api.patch(`/stage-configs/${id}/`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)
}
