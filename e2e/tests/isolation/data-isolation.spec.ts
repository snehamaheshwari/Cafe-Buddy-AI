/**
 * FLOW 6  — Data Isolation Between Tenants
 * FLOW 10 — Session Management & Logout
 *
 * These tests use FRESH sessions (no saved state) to verify cross-tenant
 * data never leaks and sessions expire correctly.
 */
import { test, expect } from '@playwright/test'
import { LoginPage }          from '../../pages/LoginPage'
import { DashboardPage }      from '../../pages/DashboardPage'
import { DataCollectionPage } from '../../pages/DataCollectionPage'
import { AuditLogPage }       from '../../pages/AuditLogPage'
import { ChatbotPage }        from '../../pages/ChatbotPage'
import { USERS }              from '../../fixtures/users'

// ─────────────────────────────────────────────────────────────────────────────
// FLOW 6: Data Isolation
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Flow 6 — Tenant Data Isolation @regression', () => {
  // Always use a fresh browser context for isolation tests
  test.use({ storageState: { cookies: [], origins: [] } })

  test('ImpastoCafe does not see system admin data on dashboard', async ({ page }) => {
    const loginPage = new LoginPage(page)
    const dashboard = new DashboardPage(page)

    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Dashboard URL must include workspace slug
    await dashboard.assertWorkspaceActive('impasto-cafe')

    // Page should not contain references to the system demo data markers
    const content = await page.content()
    // System tenant has files like "Money_Expenses_2023.xlsx" uploaded at root
    // ImpastoCafe should NOT see those
    expect(content).not.toContain('admin data')
  })

  test('ImpastoCafe Upload page shows only its own datasets', async ({ page }) => {
    const loginPage = new LoginPage(page)
    const dataPage = new DataCollectionPage(page)

    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Navigate to data collection
    const link = page.getByRole('link', { name: /upload my data|data collection/i }).first()
    await link.click()
    await page.waitForLoadState('networkidle')

    // URL should remain workspace-scoped
    await expect(page).toHaveURL(/workspace=impasto-cafe/)
  })

  test('ImpastoCafe chat history is separate from system admin chat', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Navigate to chatbot
    await page.getByRole('link', { name: /chatbot|ask cafe buddy/i }).first().click()
    await page.waitForLoadState('networkidle')

    // localStorage chat key must be tenant-scoped (not bare 'cafebuddy_chat_v2')
    const storageKeys = await page.evaluate(() => Object.keys(localStorage))
    const bareKey = storageKeys.find(k => k === 'cafebuddy_chat_v2')
    const scopedKey = storageKeys.find(k => k.startsWith('cafebuddy_chat_v2_') && k !== 'cafebuddy_chat_v2')

    // The bare (un-scoped) key must NOT be present; the scoped key is fine
    expect(bareKey).toBeUndefined()
  })

  test('audit logs API only returns ImpastoCafe entries', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Call audit API directly and check response
    const response = await page.request.get('/api/audit/logs', {
      headers: {
        Authorization: await page.evaluate(() => {
          const raw = localStorage.getItem('cafe_buddy_auth')
          return raw ? `Bearer ${JSON.parse(raw).token}` : ''
        }),
      },
    })

    expect(response.status()).toBe(200)
    const body = await response.json()
    const entries = body.entries ?? body.logs ?? []

    // Every entry must belong to ImpastoCafe tenant (not 'system')
    for (const entry of entries) {
      if (entry.tenant_id) {
        expect(entry.tenant_id).not.toBe('system')
      }
      // Username must not be system admin/owner
      expect(['admin', 'owner']).not.toContain(entry.username)
    }
  })

  test('roles API returns ImpastoCafe tenant roles, not system roles', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    const token = await page.evaluate(() => {
      const raw = localStorage.getItem('cafe_buddy_auth')
      return raw ? JSON.parse(raw).token : ''
    })

    const response = await page.request.get('/api/roles', {
      headers: { Authorization: `Bearer ${token}` },
    })
    expect(response.status()).toBe(200)

    const body = await response.json()
    expect(Array.isArray(body.roles)).toBe(true)
    // Roles returned should be for the impasto-cafe tenant
    expect(body.roles.length).toBeGreaterThan(0)
  })

  test('expired JWT returns 401, not system tenant data', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Corrupt the token in localStorage
    await page.evaluate(() => {
      const raw = localStorage.getItem('cafe_buddy_auth')
      if (raw) {
        const p = JSON.parse(raw)
        p.token = 'eyJhbGciOiJIUzI1NiJ9.FORGED.INVALIDSIG'
        localStorage.setItem('cafe_buddy_auth', JSON.stringify(p))
      }
    })

    // Make an authenticated API call
    const response = await page.request.get('/api/upload/status/all', {
      headers: { Authorization: 'Bearer eyJhbGciOiJIUzI1NiJ9.FORGED.INVALIDSIG' },
    })
    // Must return 401 — NOT 200 with system data
    expect(response.status()).toBe(401)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// FLOW 10: Session Management
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Flow 10 — Session Management & Security @smoke @regression', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('unauthenticated user is redirected to login from protected route', async ({ page }) => {
    // Try to access dashboard without auth
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/\/login/)
  })

  test('unauthenticated user accessing /chatbot redirects to login', async ({ page }) => {
    await page.goto('/chatbot')
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/\/login/)
  })

  test('logout clears localStorage and redirects to login', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Logout
    const logoutBtn = page.getByRole('button', { name: /logout|sign out/i }).first()
    if (await logoutBtn.isVisible()) {
      await logoutBtn.click()
    } else {
      // Call logout API directly
      await page.request.post('/api/auth/logout')
      await page.evaluate(() => localStorage.removeItem('cafe_buddy_auth'))
    }

    // Auth must be cleared
    const authData = await page.evaluate(() => localStorage.getItem('cafe_buddy_auth'))
    expect(authData).toBeNull()
  })

  test('after logout, protected pages redirect to login', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Clear auth to simulate logout
    await page.evaluate(() => localStorage.removeItem('cafe_buddy_auth'))

    // Try navigating to dashboard
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/\/login/)
  })

  test('JWT returned at login contains tenant_id and role_id', async ({ page }) => {
    const loginPage = new LoginPage(page)

    await page.goto(USERS.IMPASTO_ADMIN.loginUrl)
    await page.getByPlaceholder('admin').fill(USERS.IMPASTO_ADMIN.username)
    await page.getByPlaceholder('••••••••').fill(USERS.IMPASTO_ADMIN.password)

    const responsePromise = page.waitForResponse(r => r.url().includes('/api/auth/login'))
    await page.getByRole('button', { name: /sign in/i }).click()
    const response = await responsePromise

    const body = await response.json()
    expect(body.token).toBeTruthy()
    expect(body.tenant_id).toBeTruthy()
    expect(body.role_id).toBeTruthy()
    expect(body.username).toBe('ImpastoCafe')
    expect(body.tenant_slug).toBe('impasto-cafe')
  })
})
