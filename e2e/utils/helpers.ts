import { Page, BrowserContext } from '@playwright/test'

/**
 * Shared test helper utilities.
 */

// ── Auth helpers ──────────────────────────────────────────────────────────────

/** Read the JWT from localStorage (browser context) */
export async function getStoredToken(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const raw = localStorage.getItem('cafe_buddy_auth')
    return raw ? JSON.parse(raw).token : null
  })
}

/** Read the full auth object from localStorage */
export async function getStoredAuth(page: Page): Promise<Record<string, unknown> | null> {
  return page.evaluate(() => {
    const raw = localStorage.getItem('cafe_buddy_auth')
    return raw ? JSON.parse(raw) : null
  })
}

/** Clear all auth state (simulate logout) */
export async function clearAuth(page: Page) {
  await page.evaluate(() => {
    localStorage.removeItem('cafe_buddy_auth')
    // Also clear any tenant-scoped chat keys
    const toRemove = Object.keys(localStorage).filter(k => k.startsWith('cafebuddy_chat_v2'))
    toRemove.forEach(k => localStorage.removeItem(k))
  })
}

/** Make an authenticated API call using the stored token */
export async function apiGet(page: Page, path: string): Promise<{ status: number; body: unknown }> {
  const token = await getStoredToken(page)
  const response = await page.request.get(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  const body = await response.json().catch(() => null)
  return { status: response.status(), body }
}

// ── Wait utilities ────────────────────────────────────────────────────────────

/** Wait until a specific API path has been called at least once */
export async function waitForApiCall(page: Page, urlSubstring: string, method = 'GET', timeout = 10_000) {
  return page.waitForResponse(
    r => r.url().includes(urlSubstring) && r.request().method() === method,
    { timeout },
  )
}

// ── Assertion utilities ───────────────────────────────────────────────────────

/** Assert that no API call returned a 5xx error during the test */
export async function assertNoServerErrors(page: Page) {
  const errors: Array<{ url: string; status: number }> = []
  page.on('response', r => {
    if (r.status() >= 500 && r.url().includes('/api/')) {
      errors.push({ url: r.url(), status: r.status() })
    }
  })
  // Return cleanup function to call at end of test
  return () => {
    if (errors.length > 0) {
      throw new Error(`Server errors detected:\n${errors.map(e => `  ${e.status} ${e.url}`).join('\n')}`)
    }
  }
}

// ── Date utilities ────────────────────────────────────────────────────────────

/** Get today's date in IST as a YYYY-MM-DD string */
export function todayIST(): string {
  return new Date(
    new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' }),
  ).toISOString().split('T')[0]
}

/** Calculate expected "days away" for a given date string (YYYY-MM-DD) */
export function daysAway(dateStr: string): number {
  const today = new Date(todayIST())
  const target = new Date(dateStr)
  return Math.floor((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}
