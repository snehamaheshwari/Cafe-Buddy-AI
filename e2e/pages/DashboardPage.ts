import { Page, Locator, expect } from '@playwright/test'
import { BasePage } from './BasePage'

/**
 * DashboardPage — main landing page after login.
 */
export class DashboardPage extends BasePage {
  // ── Locators ──────────────────────────────────────────────────────────────
  readonly header:           Locator
  readonly sidebar:          Locator
  readonly logoutButton:     Locator
  readonly usernameDisplay:  Locator
  readonly cafeNameDisplay:  Locator

  // Stat tiles
  readonly statCards:        Locator

  // No-data / demo state
  readonly demoDataBanner:   Locator

  constructor(page: Page) {
    super(page)
    this.header          = page.locator('header, [class*="header"]').first()
    this.sidebar         = page.locator('nav, [class*="sidebar"]').first()
    this.logoutButton    = page.getByRole('button', { name: /logout|sign out/i })
    this.usernameDisplay = page.locator('[class*="username"], [data-testid="username"]').first()
    this.cafeNameDisplay = page.locator('[class*="cafe-name"], h1, h2').first()
    this.statCards       = page.locator('[class*="StatCard"], [class*="stat-card"], [class*="rounded"][class*="shadow"]')
    this.demoDataBanner  = page.locator('text=/demo|sample|no data/i').first()
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async navigate(workspace?: string) {
    const url = workspace ? `/?workspace=${workspace}` : '/'
    await this.goto(url)
  }

  async logout() {
    // Try sidebar logout first, fall back to any logout button
    const logoutLink = this.page.getByRole('button', { name: /logout/i }).first()
    await logoutLink.click()
    await this.page.waitForURL(/\/login/)
  }

  // ── Assertions ─────────────────────────────────────────────────────────────

  async assertLoggedIn(expectedUsername?: string) {
    // Confirm we're on the dashboard (not login)
    await expect(this.page).not.toHaveURL(/\/login/)
    await expect(this.sidebar).toBeVisible()
    if (expectedUsername) {
      await expect(this.page.locator(`text=${expectedUsername}`).first()).toBeVisible()
    }
  }

  async assertWorkspaceActive(workspaceSlug: string) {
    await expect(this.page).toHaveURL(new RegExp(`workspace=${workspaceSlug}`))
  }

  async assertStatCardsVisible(minCount = 1) {
    await expect(this.statCards.first()).toBeVisible()
    const count = await this.statCards.count()
    expect(count).toBeGreaterThanOrEqual(minCount)
  }

  async assertSidebarNavItems() {
    const expectedItems = ['Dashboard', 'Upload', 'Chatbot']
    for (const item of expectedItems) {
      const navItem = this.page.getByRole('link', { name: new RegExp(item, 'i') }).first()
      await expect(navItem).toBeVisible()
    }
  }

  async assertCafeName(name: string) {
    const nameEl = this.page.locator(`text=${name}`).first()
    await expect(nameEl).toBeVisible()
  }
}
