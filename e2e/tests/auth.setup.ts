/**
 * Auth Setup — runs ONCE before all test suites.
 * Logs in as each test user and saves browser storage state to .auth/*.json
 * so subsequent tests skip the login flow and run faster.
 */
import { test as setup, expect } from '@playwright/test'
import * as path from 'path'
import * as fs from 'fs'
import { USERS } from '../fixtures/users'

// Ensure .auth directory exists
const AUTH_DIR = path.join(__dirname, '..', '.auth')
if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true })

setup('authenticate: system admin', async ({ page }) => {
  const user = USERS.SYSTEM_ADMIN

  await page.goto(user.loginUrl)
  await page.getByPlaceholder('admin').fill(user.username)
  await page.getByPlaceholder('••••••••').fill(user.password)

  await Promise.all([
    page.waitForURL('**/'),
    page.getByRole('button', { name: /sign in/i }).click(),
  ])

  // Confirm we landed on dashboard
  await expect(page).toHaveURL(/(?!.*\/login)/)

  // Save storage state (cookies + localStorage) for all admin tests
  await page.context().storageState({
    path: path.join(AUTH_DIR, 'admin.json'),
  })
  console.log('✅ Admin auth state saved')
})

setup('authenticate: ImpastoCafe workspace', async ({ page }) => {
  const user = USERS.IMPASTO_ADMIN

  await page.goto(user.loginUrl)
  await page.getByPlaceholder('admin').fill(user.username)
  await page.getByPlaceholder('••••••••').fill(user.password)

  await Promise.all([
    page.waitForURL(/\?workspace=impasto-cafe/),
    page.getByRole('button', { name: /sign in/i }).click(),
  ])

  await expect(page).toHaveURL(/workspace=impasto-cafe/)

  await page.context().storageState({
    path: path.join(AUTH_DIR, 'impasto.json'),
  })
  console.log('✅ ImpastoCafe auth state saved')
})
