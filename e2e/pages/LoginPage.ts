import { Page, Locator, expect } from '@playwright/test'
import { BasePage } from './BasePage'
import type { TestUser } from '../fixtures/users'

/**
 * LoginPage — covers both system login and workspace-scoped login.
 */
export class LoginPage extends BasePage {
  // ── Locators ──────────────────────────────────────────────────────────────
  readonly usernameInput:     Locator
  readonly passwordInput:     Locator
  readonly signInButton:      Locator
  readonly errorMessage:      Locator
  readonly workspaceBadge:    Locator
  readonly signInTab:         Locator
  readonly registerTab:       Locator
  readonly pageTitle:         Locator

  constructor(page: Page) {
    super(page)
    this.usernameInput   = page.getByPlaceholder('admin')
    this.passwordInput   = page.getByPlaceholder('••••••••')
    this.signInButton    = page.getByRole('button', { name: /sign in/i })
    this.errorMessage    = page.locator('.text-red-600, [class*="text-red"]').first()
    this.workspaceBadge  = page.locator('text=Logging into')
    this.signInTab       = page.getByRole('button', { name: /sign in/i }).first()
    this.registerTab     = page.getByRole('button', { name: /new cafe setup/i })
    this.pageTitle       = page.locator('h1')
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  /** Navigate to the login page (with optional workspace slug) */
  async navigate(workspace?: string) {
    const url = workspace ? `/login?workspace=${workspace}` : '/login'
    await this.goto(url)
  }

  /** Fill credentials and submit */
  async fillCredentials(username: string, password: string) {
    await this.usernameInput.fill(username)
    await this.passwordInput.fill(password)
  }

  /** Complete full login flow for a TestUser */
  async loginAs(user: TestUser) {
    await this.navigate(user.workspace)
    await this.fillCredentials(user.username, user.password)

    // Intercept the login API call so we can assert on it
    const loginResponse = this.page.waitForResponse(
      r => r.url().includes('/api/auth/login') && r.request().method() === 'POST',
    )
    await this.signInButton.click()
    return loginResponse
  }

  /** Click auto-fill demo credential button in system login */
  async clickDemoUser(username: string) {
    await this.page.getByRole('button', { name: username }).click()
  }

  // ── Assertions ────────────────────────────────────────────────────────────

  async assertOnLoginPage() {
    await expect(this.page).toHaveURL(/\/login/)
    await expect(this.signInButton).toBeVisible()
  }

  async assertWorkspaceBrandingLoaded(cafeName: string) {
    await expect(this.workspaceBadge).toBeVisible()
    await expect(this.workspaceBadge).toContainText(cafeName)
  }

  async assertErrorShown(message?: string) {
    await expect(this.errorMessage).toBeVisible()
    if (message) {
      await expect(this.errorMessage).toContainText(message)
    }
  }

  async assertNoError() {
    await expect(this.errorMessage).not.toBeVisible()
  }
}
