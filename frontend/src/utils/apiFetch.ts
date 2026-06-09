/**
 * apiFetch — thin wrapper around fetch() that automatically appends the
 * X-Username and X-Role headers to every API request so the backend audit
 * middleware can identify who performed each action without requiring a JWT.
 *
 * Usage (drop-in replacement for fetch):
 *   const res = await apiFetch('/api/layer1/summary')
 *   const data = await apiFetch('/api/roles', { method: 'POST', body: JSON.stringify(payload) })
 */

function getAuthHeaders(): Record<string, string> {
  try {
    const raw = localStorage.getItem('cafe_buddy_auth')
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    if (!parsed?.username) return {}
    return {
      'X-Username': parsed.username,
      'X-Role':     parsed.role ?? '',
    }
  } catch {
    return {}
  }
}

export async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const authHeaders = getAuthHeaders()
  const merged: RequestInit = {
    ...init,
    headers: {
      ...authHeaders,
      ...(init?.headers ?? {}),
    },
  }
  return fetch(input, merged)
}

export default apiFetch
