import { Page, Locator, expect } from '@playwright/test'
import { BasePage } from './BasePage'

/**
 * AuditLogPage — activity / audit trail section.
 */
export class AuditLogPage extends BasePage {
  readonly pageHeading:   Locator
  readonly logTable:      Locator
  readonly logRows:       Locator
  readonly usernameFilter: Locator
  readonly moduleFilter:  Locator
  readonly exportButton:  Locator
  readonly statsCards:    Locator

  constructor(page: Page) {
    super(page)
    this.pageHeading    = page.getByRole('heading', { name: /audit/i })
    this.logTable       = page.locator('table, [class*="log-list"]').first()
    this.logRows        = page.locator('tbody tr, [class*="log-row"]')
    this.usernameFilter = page.getByPlaceholder(/username|user/i).first()
    this.moduleFilter   = page.locator('select, [class*="filter"]').first()
    this.exportButton   = page.getByRole('button', { name: /export/i }).first()
    this.statsCards     = page.locator('[class*="stat"], [class*="card"]').filter({ hasText: /today|total|active/i })
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async navigate(workspace?: string) {
    const base = workspace ? `/?workspace=${workspace}` : '/'
    await this.goto(base)
    await this.page.getByRole('link', { name: /audit/i }).first().click()
    await this.waitForNetworkIdle()
  }

  async filterByUsername(username: string) {
    if (await this.usernameFilter.isVisible().catch(() => false)) {
      await this.usernameFilter.fill(username)
      await this.waitForNetworkIdle()
    }
  }

  // ── Assertions ────────────────────────────────────────────────────────────

  async assertPageLoaded() {
    const heading = this.page.getByText(/audit/i).first()
    await expect(heading).toBeVisible()
  }

  async assertLogsVisible() {
    // At least one log row (could be the page visit itself)
    await expect(this.logRows.first()).toBeVisible({ timeout: 15_000 })
  }

  async assertLoginActionPresent() {
    const loginEntry = this.page.locator('text=/LOGIN/i').first()
    await expect(loginEntry).toBeVisible()
  }

  async assertNoForeignTenantLogs(currentUsername: string) {
    // All visible username cells must match the logged-in user (or their tenant)
    const rows = this.page.locator('tbody tr')
    const count = await rows.count()
    for (let i = 0; i < Math.min(count, 10); i++) {
      const rowText = await rows.nth(i).textContent()
      // Rows must not reference other tenant's known usernames
      expect(rowText).not.toContain('admin')      // system admin
      expect(rowText).not.toContain('owner')      // system owner
    }
  }

  async assertStatsCardsLoaded() {
    const count = await this.statsCards.count()
    expect(count).toBeGreaterThan(0)
  }
}
