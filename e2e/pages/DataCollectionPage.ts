import { Page, Locator, expect } from '@playwright/test'
import { BasePage } from './BasePage'
import { DATASET_LABELS } from '../fixtures/testData'

type DatasetType = 'financial' | 'pos' | 'customer' | 'reviews' | 'menu'

/**
 * DataCollectionPage — Upload My Data section.
 * Handles file upload, status checks, and record count assertions.
 */
export class DataCollectionPage extends BasePage {
  // ── Locators ──────────────────────────────────────────────────────────────
  readonly pageHeading:   Locator
  readonly datasetTabs:   Locator
  readonly uploadArea:    Locator
  readonly fileInput:     Locator
  readonly uploadStatus:  Locator
  readonly clearButton:   Locator
  readonly recordCount:   Locator
  readonly successIcon:   Locator

  constructor(page: Page) {
    super(page)
    this.pageHeading  = page.getByRole('heading', { name: /upload my data|data collection/i })
    this.datasetTabs  = page.locator('[class*="tab"], button').filter({ hasText: /financial|sales|customer|reviews|menu/i })
    this.uploadArea   = page.locator('[class*="dropzone"], [class*="upload-area"], label[class*="cursor"]').first()
    this.fileInput    = page.locator('input[type="file"]').first()
    this.uploadStatus = page.locator('[class*="status"], [class*="badge"]').first()
    this.clearButton  = page.getByRole('button', { name: /clear|delete|remove/i }).first()
    this.recordCount  = page.locator('text=/\\d+ record/').first()
    this.successIcon  = page.locator('[data-lucide="check-circle"], [class*="check"], [class*="success"]').first()
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async navigate(workspace?: string) {
    const base = workspace ? `/?workspace=${workspace}` : '/'
    await this.goto(base)
    await this.page.getByRole('link', { name: /upload my data|data collection/i }).first().click()
    await this.waitForNetworkIdle()
  }

  /** Click on a specific dataset tab (e.g. 'financial', 'pos') */
  async selectDataset(type: DatasetType) {
    const label = DATASET_LABELS[type]
    const tab = this.page.getByRole('button', { name: new RegExp(label, 'i') }).first()
    await tab.click()
    await this.waitForNetworkIdle()
  }

  /** Upload a file to the currently active dataset card */
  async uploadFile(filePath: string) {
    // Set files directly on the hidden input (works across drag-drop zones)
    const fileInputs = this.page.locator('input[type="file"]')
    const count = await fileInputs.count()
    // Use the first visible or the first input
    const input = count > 0 ? fileInputs.first() : this.fileInput
    await input.setInputFiles(filePath)
    // Wait for upload API call to complete
    await this.waitForAPI('/api/upload/', 'POST')
    await this.waitForNetworkIdle()
  }

  /** Upload file to a specific dataset type */
  async uploadToDataset(type: DatasetType, filePath: string) {
    await this.selectDataset(type)
    await this.uploadFile(filePath)
  }

  /** Get the displayed record count text for current dataset */
  async getRecordCount(): Promise<number> {
    const text = await this.page.locator('text=/\\d+ record/').first().textContent()
    const match = text?.match(/(\d[\d,]*)/)
    return match ? parseInt(match[1].replace(/,/g, ''), 10) : 0
  }

  async clearDataset() {
    await this.clearButton.click()
    // Confirm dialog if present
    const confirmBtn = this.page.getByRole('button', { name: /confirm|yes|ok/i }).first()
    if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmBtn.click()
    }
    await this.waitForNetworkIdle()
  }

  // ── Assertions ────────────────────────────────────────────────────────────

  async assertPageLoaded() {
    // The heading or at least the upload area should be visible
    const heading = this.page.getByText(/upload my data|data collection/i).first()
    await expect(heading).toBeVisible()
  }

  async assertUploadSuccess() {
    // Look for green badge / success text
    const success = this.page.locator('text=/uploaded|success|\\d+ records/i').first()
    await expect(success).toBeVisible({ timeout: 20_000 })
  }

  async assertRecordCountAtLeast(min: number) {
    const count = await this.getRecordCount()
    expect(count).toBeGreaterThanOrEqual(min)
  }

  async assertDatasetUploaded(type: DatasetType) {
    const label = DATASET_LABELS[type]
    const statusBadge = this.page.locator(`text=/uploaded/i`).first()
    await expect(statusBadge).toBeVisible({ timeout: 15_000 })
  }

  async assertNoDataUploaded() {
    const notUploaded = this.page.locator('text=/not uploaded|no data|upload your/i').first()
    await expect(notUploaded).toBeVisible()
  }
}
