const BASE = '/api'

/**
 * Build auth headers for every outgoing API request.
 * - New tenant accounts get `Authorization: Bearer <jwt>` (token from login)
 * - System tenant demo accounts also send the JWT (now a real token)
 * - Legacy header `X-Username` is included for backward compatibility with
 *   audit middleware that reads it directly.
 *
 * Exported so other components (e.g. RoleManagement) can include the same
 * auth context in their own fetch calls.
 */
export function authHeaders(): Record<string, string> {
  try {
    const raw = localStorage.getItem('cafe_buddy_auth')
    if (!raw) return {}
    const p = JSON.parse(raw)
    if (!p?.username) return {}
    const headers: Record<string, string> = {
      'X-Username': p.username,
      'X-Role':     p.role ?? '',
    }
    // Always include JWT Bearer token when available
    if (p.token && !p.token.startsWith('demo-token-')) {
      headers['Authorization'] = `Bearer ${p.token}`
    }
    return headers
  } catch {
    return {}
  }
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `API ${res.status}`)
  }
  return res.json()
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE', headers: authHeaders() })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  auth: {
    login:  (body: { username: string; password: string; workspace?: string }) =>
              post('/auth/login', body),
    logout: () => post('/auth/logout'),
    register: (body: {
      cafe_name: string; owner_name: string; owner_email: string
      username: string; password: string
      brand_color?: string; logo_url?: string
    }) => post('/auth/register', body),
    workspace: (slug: string) => get<any>(`/auth/workspace/${slug}`),
  },
  tenant: {
    info:          () => get<any>('/tenant/info'),
    updateBranding: (body: { cafe_name?: string; brand_color?: string; logo_url?: string }) =>
                    fetch(`${BASE}/tenant/branding`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json', ...authHeaders() },
                      body: JSON.stringify(body),
                    }).then(async r => {
                      if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Update failed') }
                      return r.json()
                    }),
  },
  upload: {
    excel:  (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return fetch(`${BASE}/upload/excel`, { method: 'POST', headers: authHeaders(), body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    status: () => get('/upload/status'),
    clear:  () => del('/upload/clear'),
    statusAll: () => get('/upload/status/all'),
    financial: (file: File) => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/financial`, { method: 'POST', headers: authHeaders(), body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    pos: (file: File, mode: 'replace' | 'append' = 'replace') => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/pos?mode=${mode}`, { method: 'POST', headers: authHeaders(), body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    customer: (file: File, mode: 'replace' | 'append' = 'replace') => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/customer?mode=${mode}`, { method: 'POST', headers: authHeaders(), body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    records: (type: string, page = 1, perPage = 50, search = '') =>
      get(`/data/${type}/records?page=${page}&per_page=${perPage}&search=${encodeURIComponent(search)}`),
    clearFinancial:  () => del('/upload/financial/clear'),
    clearPos:        () => del('/upload/pos/clear'),
    clearCustomer:   () => del('/upload/customer/clear'),
    clearReviews:    () => del('/upload/reviews/clear'),
    clearMenu:       () => del('/upload/menu/clear'),
    summaryFinancial: () => get('/data/financial/summary'),
    summaryPos:       () => get('/data/pos/summary'),
    summaryCustomer:  () => get('/data/customer/summary'),
    summaryReviews:   () => get('/data/reviews/summary'),
    summaryMenu:      () => get('/data/menu/summary'),
    menu: (file: File) => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/menu`, { method: 'POST', headers: authHeaders(), body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
    reviews: (file: File) => {
      const fd = new FormData(); fd.append('file', file)
      return fetch(`${BASE}/upload/reviews`, { method: 'POST', headers: authHeaders(), body: fd }).then(async (r) => {
        if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Upload failed') }
        return r.json()
      })
    },
  },
  sentiment: {
    overview: () => get('/sentiment/overview'),
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
    insights:       () => get('/layer2/insights'),
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
  notifications: {
    /**
     * Send a WhatsApp alert via Infinito (api.goinfinito.com).
     * Only `phone` is required — token/sender are configured server-side.
     */
    sendWhatsApp: (body: { phone: string; message?: string }) =>
      post('/notifications/whatsapp/send', body),
    getSummary: () => get<{ preview: string }>('/notifications/whatsapp/summary'),
  },
  ml: {
    forecast:         () => get('/ml/forecast'),
    platformForecast: () => get('/ml/platform-forecast'),
    peakHours:        () => get('/ml/peak-hours'),
    cancellationRisk: () => get('/ml/cancellation-risk'),
    crossSell:        () => get('/ml/cross-sell'),
    dynamicPricing:   () => get('/ml/dynamic-pricing'),
    modelComparison:  () => get('/ml/model-comparison'),
  },
  templates: {
    /**
     * Trigger a browser download of the CSV template for the given dataset type.
     * Types: 'financial' | 'pos' | 'customer' | 'reviews' | 'menu'
     */
    download: (type: string): void => {
      const a = document.createElement('a')
      a.href = `/api/templates/${type}`
      a.download = `cafe_buddy_${type}_template.csv`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
    },
  },
  admin: {
    /** List all registered tenant workspaces (system admin only). */
    listTenants:  () => get<any>('/admin/tenants'),
    /** Permanently delete a tenant workspace (system admin only). */
    deleteTenant: (tenantId: string) => del<any>(`/admin/tenants/${tenantId}`),
  },
  peers: {
    cities:      ()                             => get<any>('/peers/cities'),
    areas:       (city: string)                 => get<any>(`/peers/areas?city=${encodeURIComponent(city)}`),
    competitors: (city: string, area?: string)  => get<any>(`/peers/competitors?city=${encodeURIComponent(city)}${area ? `&area=${encodeURIComponent(area)}` : ''}`),
    liveSearch:  (city: string, area: string)   => get<any>(`/peers/live-search?city=${encodeURIComponent(city)}&area=${encodeURIComponent(area)}`),
    analyze:     (city: string, area?: string)  => post<any>('/peers/analyze', { city, area }),
  },
}
