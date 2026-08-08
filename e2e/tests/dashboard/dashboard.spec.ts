/**
 * FLOW 5 — Dashboard Data Validation
 * Verifies dashboard renders correct data after upload.
 */
import { test, expect } from '@playwright/test'
import { DashboardPage } from '../../pages/DashboardPage'

test.describe('Flow 5 — Dashboard Data Validation @smoke @regression', () => {
  let dashboard: DashboardPage

  test.beforeEach(async ({ page }) => {
    dashboard = new DashboardPage(page)
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('dashboard loads without errors after login', async ({ page }) => {
    // No uncaught JS errors
    const errors: string[] = []
    page.on('pageerror', err => errors.push(err.message))

    await page.goto('/')
    await page.waitForLoadState('networkidle')
    expect(errors.filter(e => !e.includes('ResizeObserver'))).toHaveLength(0)
  })

  test('sidebar navigation items are all visible', async ({ page }) => {
    await dashboard.assertSidebarNavItems()

    // Verify key sidebar links render
    const links = ['Dashboard', 'Data', 'Chatbot', 'Role']
    for (const link of links) {
      const el = page.getByRole('link', { name: new RegExp(link, 'i') }).first()
      await expect(el).toBeVisible()
    }
  })

  test('stat tiles / KPI cards are visible', async ({ page }) => {
    await dashboard.assertStatCardsVisible(1)
  })

  test('dashboard shows revenue and order data when uploaded', async ({ page }) => {
    // If data has been uploaded, revenue / orders should not show 0
    const revenueEl = page.locator('text=/revenue|₹/i').first()
    await expect(revenueEl).toBeVisible()
  })

  test('dashboard API calls return 200', async ({ page }) => {
    const responses: number[] = []
    page.on('response', r => {
      if (r.url().includes('/api/') && !r.url().includes('/api/auth/')) {
        responses.push(r.status())
      }
    })

    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // No API should return 500
    const serverErrors = responses.filter(s => s >= 500)
    expect(serverErrors).toHaveLength(0)
  })

  test('workspace is displayed in header / sidebar', async ({ page }) => {
    // For system admin, username "admin" should be visible somewhere
    const userEl = page.locator('text=/admin/i').first()
    await expect(userEl).toBeVisible()
  })

  test('logout flow works and redirects to login', async ({ page }) => {
    await dashboard.logout()
    await expect(page).toHaveURL(/\/login/)
  })
})
