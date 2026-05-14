const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `API ${res.status}`)
  }
  return res.json()
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  auth: {
    login:  (body: { username: string; password: string }) => post('/auth/login', body),
    logout: () => post('/auth/logout'),
  },
  upload: {
    excel:  (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return fetch(`${BASE}/upload/excel`, { method: 'POST', body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    status: () => get('/upload/status'),
    clear:  () => del('/upload/clear'),
    statusAll: () => get('/upload/status/all'),
    financial: (file: File) => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/financial`, { method: 'POST', body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    pos: (file: File) => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/pos`, { method: 'POST', body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    customer: (file: File) => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/customer`, { method: 'POST', body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    clearFinancial:  () => del('/upload/financial/clear'),
    clearPos:        () => del('/upload/pos/clear'),
    clearCustomer:   () => del('/upload/customer/clear'),
    summaryFinancial: () => get('/data/financial/summary'),
    summaryPos:       () => get('/data/pos/summary'),
    summaryCustomer:  () => get('/data/customer/summary'),
  },
  dashboard: {
    overview: () => get('/dashboard/overview'),
  },
  layer1: {
    summary:  () => get('/layer1/summary'),
    platforms: () => get('/layer1/platforms'),
    addSales: (data: unknown) => post('/layer1/sales', data),
  },
  layer2: {
    pipelineStatus: () => get('/layer2/pipeline-status'),
    processedData:  () => get('/layer2/processed-data'),
  },
  layer3: {
    forecast:        () => get('/layer3/forecast'),
    recommendations: () => get('/layer3/recommendations'),
    segmentation:    () => get('/layer3/segmentation'),
  },
  layer4: {
    decisions: () => get('/layer4/decisions'),
    approve:   (id: number) => post(`/layer4/decisions/${id}/approve`),
    reject:    (id: number) => post(`/layer4/decisions/${id}/reject`),
  },
  layer5: {
    autonomousActions: () => get('/layer5/autonomous-actions'),
    kpis:              () => get('/layer5/kpis'),
  },
}
