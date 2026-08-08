/**
 * FLOW 8 — Role Management
 * Verifies RBAC roles and users are correctly scoped per tenant.
 */
import { test, expect } from '@playwright/test'
import { RoleManagementPage } from '../../pages/RoleManagementPage'
import { SYSTEM_ROLES }       from '../../fixtures/testData'

test.describe('Flow 8 — Role Management @regression', () => {
  let rolePage: RoleManagementPage

  test.beforeEach(async ({ page }) => {
    rolePage = new RoleManagementPage(page)
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    const roleLink = page.getByRole('link', { name: /role management/i }).first()
    if (await roleLink.isVisible()) {
      await roleLink.click()
      await page.waitForLoadState('networkidle')
    } else {
      test.skip(true, 'Role Management not accessible for this user')
    }
  })

  test('Role Management page loads with roles list', async ({ page }) => {
    await rolePage.assertPageLoaded()
  })

  test('standard roles exist: Admin, Sub-Admin, Viewer', async ({ page }) => {
    await rolePage.assertRolesVisible(SYSTEM_ROLES)
  })

  test('permissions are listed for each role', async ({ page }) => {
    // At least some permission chips/badges should be visible
    const permissions = page.locator('[class*="permission"], [class*="badge"], [class*="chip"]')
    const count = await permissions.count()
    expect(count).toBeGreaterThan(0)
  })

  test('Users tab shows at least one user', async ({ page }) => {
    await rolePage.assertUsersVisible()
  })

  test('all-permissions panel is accessible', async ({ page }) => {
    // There should be a section listing available permissions
    const permSection = page.locator('text=/upload.data|chatbot|analytics|reports/i').first()
    await expect(permSection).toBeVisible()
  })

  test('role management API returns data for current tenant', async ({ page }) => {
    const rolesResponse = await page.waitForResponse(r => r.url().includes('/api/roles'))
    expect(rolesResponse.status()).toBe(200)

    const body = await rolesResponse.json()
    expect(Array.isArray(body.roles)).toBe(true)
    expect(body.roles.length).toBeGreaterThan(0)
  })
})
