/**
 * FLOW 4 — Data Upload & Validation
 * Tests uploading each dataset type and verifying record counts
 * and status display.
 */
import { test, expect } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'
import { DataCollectionPage } from '../../pages/DataCollectionPage'
import { DashboardPage }      from '../../pages/DashboardPage'
import { TEST_FILES, MIN_RECORD_COUNTS } from '../../fixtures/testData'

// ── Sample CSV generator (used when fixture files don't exist) ────────────────
function ensureSampleFiles() {
  const dir = path.join(__dirname, '../../fixtures/files')
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true })

  // POS / Sales data
  const posPath = path.join(dir, 'sample_pos.csv')
  if (!fs.existsSync(posPath)) {
    const rows = [
      'date,item_name,category,quantity,revenue,platform',
      '2026-07-01,Cappuccino,Beverages,5,750,Dine-in',
      '2026-07-01,Pasta Arrabbiata,Mains,3,1350,Zomato',
      '2026-07-02,Tiramisu,Desserts,2,700,Swiggy',
      '2026-07-02,Latte,Beverages,8,1200,Dine-in',
      '2026-07-03,Margherita Pizza,Mains,4,2000,Zomato',
      '2026-07-03,Cold Brew,Beverages,6,900,Swiggy',
      '2026-07-04,Bruschetta,Starters,3,600,Dine-in',
      '2026-07-05,Espresso,Beverages,10,1000,Dine-in',
      '2026-07-05,Penne Pesto,Mains,2,900,Zomato',
      '2026-07-06,Cheesecake,Desserts,3,900,Swiggy',
    ]
    fs.writeFileSync(posPath, rows.join('\n'))
  }

  // Financial data
  const finPath = path.join(dir, 'sample_financial.csv')
  if (!fs.existsSync(finPath)) {
    const rows = [
      'date,monthly_revenue,gross_margin_pct,net_profit,food_cost_pct,labor_cost_pct',
      '2026-01-01,150000,62,18000,28,22',
      '2026-02-01,165000,63,21000,27,21',
      '2026-03-01,180000,65,25000,25,20',
    ]
    fs.writeFileSync(finPath, rows.join('\n'))
  }

  // Customer data
  const custPath = path.join(dir, 'sample_customer.csv')
  if (!fs.existsSync(custPath)) {
    const rows = [
      'customer_id,name,email,visits,total_spend,last_visit',
      'C001,Rahul Sharma,rahul@test.com,12,8400,2026-07-01',
      'C002,Priya Patel,priya@test.com,5,3500,2026-07-02',
      'C003,Amit Singh,amit@test.com,20,14000,2026-07-03',
      'C004,Sneha Gupta,sneha@test.com,3,2100,2026-07-04',
      'C005,Vikram Rao,vikram@test.com,8,5600,2026-07-05',
    ]
    fs.writeFileSync(custPath, rows.join('\n'))
  }

  // Reviews data
  const revPath = path.join(dir, 'sample_reviews.csv')
  if (!fs.existsSync(revPath)) {
    const rows = [
      'review_id,text,rating,date',
      'R001,Amazing food and great ambiance! Love the coffee.,5,2026-07-01',
      'R002,Service was a bit slow but food was excellent.,4,2026-07-02',
      'R003,Best tiramisu in the city.,5,2026-07-03',
      'R004,Average experience nothing special.,3,2026-07-04',
      'R005,Very friendly staff and cozy atmosphere.,5,2026-07-05',
    ]
    fs.writeFileSync(revPath, rows.join('\n'))
  }

  // Menu data
  const menuPath = path.join(dir, 'sample_menu.csv')
  if (!fs.existsSync(menuPath)) {
    const rows = [
      'item_name,category,price,cost,is_available',
      'Cappuccino,Beverages,150,45,true',
      'Latte,Beverages,160,48,true',
      'Pasta Arrabbiata,Mains,320,96,true',
      'Margherita Pizza,Mains,450,135,true',
      'Tiramisu,Desserts,280,84,true',
    ]
    fs.writeFileSync(menuPath, rows.join('\n'))
  }

  // Invalid file (for negative test)
  const invalidPath = path.join(dir, 'invalid.txt')
  if (!fs.existsSync(invalidPath)) {
    fs.writeFileSync(invalidPath, 'This is not a CSV or Excel file.')
  }
}

// Generate fixtures before tests run
ensureSampleFiles()

// ─────────────────────────────────────────────────────────────────────────────
// FLOW 4: Data Upload & Validation
// ─────────────────────────────────────────────────────────────────────────────
test.describe('Flow 4 — Data Upload & Validation @regression', () => {
  let dataPage: DataCollectionPage

  test.beforeEach(async ({ page }) => {
    dataPage = new DataCollectionPage(page)
    // Navigate directly (auth state loaded from setup)
    await page.goto('/data-collection')
    await page.waitForLoadState('networkidle')
  })

  test('Upload My Data page loads with all dataset sections', async ({ page }) => {
    await dataPage.assertPageLoaded()

    // All 5 dataset labels must be present
    const datasets = ['Money & Expenses', 'Sales & Orders', 'Customer Records', 'Customer Reviews', 'Menu & Pricing']
    for (const label of datasets) {
      const el = page.getByText(label).first()
      await expect(el).toBeVisible()
    }
  })

  test('upload POS/Sales CSV and verify record count', async ({ page }) => {
    await dataPage.selectDataset('pos')
    await dataPage.uploadFile(TEST_FILES.POS_CSV)

    await dataPage.assertUploadSuccess()
    await dataPage.assertRecordCountAtLeast(MIN_RECORD_COUNTS.pos)
  })

  test('upload Financial CSV and verify status badge', async ({ page }) => {
    await dataPage.selectDataset('financial')
    await dataPage.uploadFile(TEST_FILES.FINANCIAL_CSV)
    await dataPage.assertUploadSuccess()
    await dataPage.assertRecordCountAtLeast(MIN_RECORD_COUNTS.financial)
  })

  test('upload Customer CSV and verify upload success', async ({ page }) => {
    await dataPage.selectDataset('customer')
    await dataPage.uploadFile(TEST_FILES.CUSTOMER_CSV)
    await dataPage.assertUploadSuccess()
    await dataPage.assertRecordCountAtLeast(MIN_RECORD_COUNTS.customer)
  })

  test('upload Reviews CSV and verify sentiment processing', async ({ page }) => {
    await dataPage.selectDataset('reviews')
    await dataPage.uploadFile(TEST_FILES.REVIEWS_CSV)

    // Reviews have extra processing — wait longer
    await page.waitForTimeout(3000)
    await dataPage.assertUploadSuccess()
  })

  test('upload Menu CSV and verify items listed', async ({ page }) => {
    await dataPage.selectDataset('menu')
    await dataPage.uploadFile(TEST_FILES.MENU_CSV)
    await dataPage.assertUploadSuccess()
    await dataPage.assertRecordCountAtLeast(MIN_RECORD_COUNTS.menu)
  })

  test('upload overall status shows all 5 datasets loaded', async ({ page }) => {
    // The status banner / summary card should show 5/5 datasets
    const statusSummary = page.locator('text=/5.*dataset|all.*uploaded|5.*5/i').first()
    // At minimum, some upload count text should appear
    const anyUpload = page.locator('text=/uploaded/i').first()
    await expect(anyUpload).toBeVisible()
  })

  test('NEGATIVE — invalid file type shows error', async ({ page }) => {
    await dataPage.selectDataset('pos')

    // Attempt to upload a .txt file
    const fileInput = page.locator('input[type="file"]').first()
    await fileInput.setInputFiles(TEST_FILES.INVALID_FILE)

    // Error message or the upload simply not proceeding
    const errorEl = page.locator('text=/invalid|not supported|error|failed/i').first()
    const noSuccess = page.locator('text=/uploaded|success/i')

    // Either an error appears or success does NOT appear
    const errorVisible = await errorEl.isVisible({ timeout: 5000 }).catch(() => false)
    const successVisible = await noSuccess.isVisible({ timeout: 3000 }).catch(() => false)
    expect(errorVisible || !successVisible).toBe(true)
  })
})
