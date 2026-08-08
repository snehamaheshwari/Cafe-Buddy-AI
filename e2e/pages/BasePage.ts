import { Page, Locator, expect } from '@playwright/test'

/**
 * BasePage — inherited by every page object.
 * Provides shared navigation helpers, wait utilities, and common assertions.
 */
export class BasePage {
  readonly page: Page

  constructor(page: Page) {
    this.page = page
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  async goto(path: string) {
    await this.page.goto(path)
    await this.page.waitForLoadState('networkidle')
  }

  async waitForNetworkIdle() {
    await this.page.waitForLoadState('networkidle')
  }

  // ── URL assertions ────────────────────────────────────────────────────────

  async assertCurrentUrl(expectedPath: string) {
    await expect(this.page).toHaveURL(new RegExp(expectedPath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
  }

  async assertUrlContains(substring: string) {
    await expect(this.page).toHaveURL(new RegExp(substring))
  }

  // ── Visibility & text helpers ─────────────────────────────────────────────

  async assertVisible(locator: Locator) {
    await expect(locator).toBeVisible()
  }

  async assertText(locator: Locator, text: string) {
    await expect(locator).toContainText(text)
  }

  async assertNotVisible(locator: Locator) {
    await expect(locator).not.toBeVisible()
  }

  // ── Toast / notification helper ───────────────────────────────────────────

  /** Wait for a success/error toast message containing the given text */
  async waitForToast(text: string, timeout = 10_000) {
    const toast = this.page.locator(`text=${text}`).first()
    await expect(toast).toBeVisible({ timeout })
    return toast
  }

  // ── Sidebar navigation ────────────────────────────────────────────────────

  async navigateTo(menuLabel: string) {
    const link = this.page.getByRole('link', { name: new RegExp(menuLabel, 'i') }).first()
    await link.click()
    await this.waitForNetworkIdle()
  }

  // ── Generic file upload ───────────────────────────────────────────────────

  async uploadFile(inputSelector: string, filePath: string) {
    const fileInput = this.page.locator(inputSelector)
    await fileInput.setInputFiles(filePath)
  }

  // ── Wait for API response ──────────────────────────────────────────────────

  async waitForAPI(urlPattern: string | RegExp, method: string = 'GET') {
    return this.page.waitForResponse(
      response =>
        (typeof urlPattern === 'string'
          ? response.url().includes(urlPattern)
          : urlPattern.test(response.url())) &&
        response.request().method() === method,
    )
  }

  // ── Screenshot for debugging ──────────────────────────────────────────────

  async screenshot(name: string) {
    await this.page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true })
  }
}
