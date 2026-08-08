import { defineConfig, devices } from '@playwright/test'
import * as path from 'path'

/**
 * Playwright configuration for Cafe Buddy AI E2E tests.
 * Base URL targets production by default; override with BASE_URL env var
 * to test a local/staging environment.
 *
 *   BASE_URL=http://localhost:5173 npx playwright test
 */
export default defineConfig({
  // ── Directory containing .spec.ts files ──────────────────────────────────
  testDir: './tests',

  // ── Parallelism ──────────────────────────────────────────────────────────
  fullyParallel: false,   // keep sequential — workspace state is shared on server
  workers: 1,

  // ── Retries ──────────────────────────────────────────────────────────────
  retries: process.env.CI ? 2 : 0,

  // ── Reporters ────────────────────────────────────────────────────────────
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  // ── Global test settings ─────────────────────────────────────────────────
  use: {
    baseURL: process.env.BASE_URL || 'https://aicafebuddy.com',

    // Record traces on retry for debugging
    trace: 'on-first-retry',

    // Take screenshot on failure
    screenshot: 'only-on-failure',

    // Record video on failure
    video: 'retain-on-failure',

    // Viewport
    viewport: { width: 1280, height: 800 },

    // Max time for each action (click, fill, etc.)
    actionTimeout: 15_000,

    // Max time for each navigation
    navigationTimeout: 30_000,

    // Extra HTTP headers sent with every request
    extraHTTPHeaders: {
      'Accept-Language': 'en-IN',
    },
  },

  // ── Global timeout per test ───────────────────────────────────────────────
  timeout: 60_000,
  expect: { timeout: 10_000 },

  // ── Output directories ────────────────────────────────────────────────────
  outputDir: 'test-results/',

  // ── Projects (browsers) ───────────────────────────────────────────────────
  projects: [
    // Setup project — runs once before all tests to create auth state files
    {
      name: 'setup',
      testMatch: '**/auth.setup.ts',
      use: { ...devices['Desktop Chrome'] },
    },

    // Main Chrome suite — uses saved auth state for fast login
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(__dirname, '.auth', 'admin.json'),
      },
      dependencies: ['setup'],
    },

    // Workspace tenant tests (ImpastoCafe)
    {
      name: 'workspace-tenant',
      testMatch: '**/isolation/**',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(__dirname, '.auth', 'impasto.json'),
      },
      dependencies: ['setup'],
    },

    // Mobile smoke test
    {
      name: 'mobile-safari',
      testMatch: '**/*.smoke.ts',
      use: { ...devices['iPhone 14'] },
    },
  ],
})
