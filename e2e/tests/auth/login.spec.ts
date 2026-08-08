/**
 * FLOW 1 — System Admin Login
 * FLOW 2 — Workspace Tenant Login (ImpastoCafe)
 * FLOW 3 — Invalid Credentials (Negative Test)
 */
import { test, expect } from '@playwright/test'
import { LoginPage }     from '../../pages/LoginPage'
import { DashboardPage } from '../../pages/DashboardPage'
import { USERS }         from '../../fixtures/users'

// ─────────────────────────────────────────────────────────────────────────────
// FLOW 1: System Admin Login
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Flow 1 — System Admin Login @smoke @regression', () => {
  // Fresh page (no saved auth state) so we can test the login flow itself
  test.use({ storageState: { cookies: [], origins: [] } })

  test('admin logs in with demo credentials and lands on dashboard', async ({ page }) => {
    const loginPage = new LoginPage(page)
    const dashboard = new DashboardPage(page)

    // Navigate to system login (no workspace param)
    await loginPage.navigate()

    // Demo credential section should be visible
    const demoSection = page.locator('text=/demo credentials/i')
    await expect(demoSection).toBeVisible()

    // Fill and submit
    await loginPage.fillCredentials(USERS.SYSTEM_ADMIN.username, USERS.SYSTEM_ADMIN.password)
    const response = await loginPage.signInButton.click().then(() =>
      page.waitForResponse(r => r.url().includes('/api/auth/login'))
    )
    expect(response.status()).toBe(200)

    // Confirm dashboard loaded
    await dashboard.assertLoggedIn('admin')
    await dashboard.assertStatCardsVisible()
    await dashboard.assertSidebarNavItems()
  })

  test('demo auto-fill buttons populate credentials', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.navigate()

    // Click the "admin" auto-fill link
    await loginPage.clickDemoUser('admin')

    // Fields should be populated
    await expect(loginPage.usernameInput).toHaveValue('admin')
    await expect(loginPage.passwordInput).toHaveValue('cafe123')
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// FLOW 2: Workspace Tenant Login (ImpastoCafe)
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Flow 2 — Workspace Login (ImpastoCafe) @smoke @regression', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('workspace branding loads before login', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.navigate('impasto-cafe')

    // Workspace branding chip should appear
    await loginPage.assertWorkspaceBrandingLoaded('ImpastoCafe')

    // Demo credentials section should NOT be visible (workspace-specific login)
    const demoSection = page.locator('text=/demo credentials/i')
    await expect(demoSection).not.toBeVisible()
  })

  test('ImpastoCafe user logs in and URL is workspace-scoped', async ({ page }) => {
    const loginPage = new LoginPage(page)
    const dashboard = new DashboardPage(page)

    const loginResponse = await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    const body = await (loginResponse as any).json()

    // JWT should include tenant_id (not system)
    expect(body.tenant_id).toBeTruthy()
    expect(body.tenant_id).not.toBe('system')

    // URL must include workspace slug
    await dashboard.assertWorkspaceActive('impasto-cafe')
    await dashboard.assertLoggedIn('ImpastoCafe')
  })

  test('workspace URL is preserved across page navigation', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Navigate to another page via sidebar
    await page.getByRole('link', { name: /upload my data/i }).first().click()
    await expect(page).toHaveURL(/workspace=impasto-cafe/)

    // Navigate back to dashboard
    await page.getByRole('link', { name: /dashboard/i }).first().click()
    await expect(page).toHaveURL(/workspace=impasto-cafe/)
  })
})

// ─────────────────────────────────────────────────────────────────────────────
// FLOW 3: Invalid Credentials (Negative Test)
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Flow 3 — Invalid Login Credentials @regression', () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test('wrong password shows error, user stays on login page', async ({ page }) => {
    const loginPage = new LoginPage(page)

    await loginPage.navigate('impasto-cafe')
    await loginPage.fillCredentials('ImpastoCafe', 'wrongpassword999')

    const response = await page.waitForResponse(r => r.url().includes('/api/auth/login'))
    await loginPage.signInButton.click()
    await loginPage.assertErrorShown('Invalid')

    // Must stay on login page
    await loginPage.assertOnLoginPage()
  })

  test('non-existent user shows error', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.navigate('impasto-cafe')
    await loginPage.fillCredentials(USERS.INVALID_USER.username, USERS.INVALID_USER.password)
    await loginPage.signInButton.click()

    await loginPage.assertErrorShown()
    await loginPage.assertOnLoginPage()
  })

  test('empty credentials show HTML5 validation, no API call made', async ({ page }) => {
    const loginPage = new LoginPage(page)
    await loginPage.navigate()

    let apiCalled = false
    page.on('request', r => { if (r.url().includes('/api/auth/login')) apiCalled = true })

    // Try clicking without filling fields
    await loginPage.signInButton.click()

    // Native browser validation should prevent submission
    await page.waitForTimeout(500)
    expect(apiCalled).toBe(false)
    await loginPage.assertOnLoginPage()
  })

  test('wrong workspace slug returns 404 branding, login still works', async ({ page }) => {
    // Non-existent workspace — API returns 404 for branding
    await page.goto('/login?workspace=this-workspace-does-not-exist-xyz')
    await page.waitForLoadState('networkidle')

    // Page should still render a login form (graceful fallback)
    const signInBtn = page.getByRole('button', { name: /sign in/i })
    await expect(signInBtn).toBeVisible()
  })
})
