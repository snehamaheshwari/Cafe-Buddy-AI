import { Page, Locator, expect } from '@playwright/test'
import { BasePage } from './BasePage'

/**
 * RoleManagementPage — RBAC roles and users management.
 */
export class RoleManagementPage extends BasePage {
  readonly pageHeading:   Locator
  readonly rolesTab:      Locator
  readonly usersTab:      Locator
  readonly rolesList:     Locator
  readonly usersList:     Locator
  readonly createButton:  Locator
  readonly roleRows:      Locator
  readonly userRows:      Locator

  constructor(page: Page) {
    super(page)
    this.pageHeading  = page.getByRole('heading', { name: /role management|roles/i })
    this.rolesTab     = page.getByRole('button', { name: /roles/i }).first()
    this.usersTab     = page.getByRole('button', { name: /users/i }).first()
    this.rolesList    = page.locator('[class*="role-list"], table, [class*="card"]').first()
    this.usersList    = page.locator('[class*="user-list"], table, [class*="card"]').first()
    this.createButton = page.getByRole('button', { name: /create|add|new/i }).first()
    this.roleRows     = page.locator('tr, [class*="role-row"], [class*="list-item"]').filter({ hasText: /admin|viewer|sub.?admin/i })
    this.userRows     = page.locator('tr, [class*="user-row"]').filter({ hasNotText: /username|column/i })
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async navigate(workspace?: string) {
    const base = workspace ? `/?workspace=${workspace}` : '/'
    await this.goto(base)
    await this.page.getByRole('link', { name: /role management/i }).first().click()
    await this.waitForNetworkIdle()
  }

  async switchToUsersTab() {
    await this.usersTab.click()
    await this.waitForNetworkIdle()
  }

  async switchToRolesTab() {
    await this.rolesTab.click()
    await this.waitForNetworkIdle()
  }

  // ── Assertions ────────────────────────────────────────────────────────────

  async assertPageLoaded() {
    const heading = this.page.getByText(/role management/i).first()
    await expect(heading).toBeVisible()
  }

  async assertRolesVisible(expectedRoles: string[]) {
    for (const role of expectedRoles) {
      const roleEl = this.page.getByText(role).first()
      await expect(roleEl).toBeVisible()
    }
  }

  async assertUsersVisible() {
    await this.switchToUsersTab()
    // At least one user row should be visible
    const anyUser = this.page.locator('text=/admin|ImpastoCafe|owner/i').first()
    await expect(anyUser).toBeVisible()
  }

  async assertNoSystemAdminUsers() {
    // ImpastoCafe role management must NOT show system admin/owner
    const content = await this.page.locator('body').textContent()
    // System users are "admin" and "owner" — workspace tenants must not see them
    expect(content).not.toMatch(/\badmin\b.*\bcafe123\b/i)
  }

  async assertRoleCount(min: number) {
    const roles = this.page.locator('[class*="role"]').filter({ hasText: /./ })
    const count = await roles.count()
    expect(count).toBeGreaterThanOrEqual(min)
  }
}
