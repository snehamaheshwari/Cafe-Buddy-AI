# Cafe Buddy AI — Playwright E2E Test Suite

> **Automated end-to-end tests for the ImpastoCafe / Cafe Buddy AI platform.**
> Covers 10 core user flows, enforces tenant data isolation, and gates deployments via a Jenkins CI pipeline.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Test Flows](#test-flows)
- [Running Tests](#running-tests)
- [Environment Variables](#environment-variables)
- [Jenkins CI Setup](#jenkins-ci-setup)
- [Adding New Tests](#adding-new-tests)

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Node.js | 18+ | https://nodejs.org |
| npm | 9+ | bundled with Node |
| Java | 11+ | Already installed ✅ |

Verify:
```bash
node -v    # v18+ required
npm -v
java -version
```

---

## Quick Start

```bash
# 1. From the repo root, navigate to e2e directory
cd e2e

# 2. Install dependencies
npm install

# 3. Install Playwright browser binaries
npx playwright install chromium --with-deps

# 4. Create auth directory and run auth setup (saves login state)
npx playwright test tests/auth.setup.ts --project=setup

# 5. Run smoke tests (fast, ~2-3 min)
npm run test:smoke

# 6. Run full regression suite
npm run test:regression

# 7. View HTML report
npx playwright show-report
```

---

## Project Structure

```
e2e/
├── fixtures/
│   ├── users.ts          # Test user accounts (system admin, ImpastoCafe, etc.)
│   └── testData.ts       # Dataset labels, file paths, min record counts
│
├── pages/                # Page Object Model (POM)
│   ├── BasePage.ts       # Shared helpers (wait, navigate, assert)
│   ├── LoginPage.ts      # Login form interactions
│   ├── DashboardPage.ts  # Dashboard assertions (stat cards, sidebar)
│   ├── DataCollectionPage.ts  # Upload datasets, verify record counts
│   ├── ChatbotPage.ts    # Send chat messages, validate responses
│   ├── RoleManagementPage.ts  # Role/user table assertions
│   └── AuditLogPage.ts   # Audit log filtering and verification
│
├── tests/
│   ├── auth.setup.ts     # Saves auth state to .auth/ (runs once before suite)
│   ├── auth/
│   │   └── login.spec.ts          # Flows 1, 2, 3
│   ├── upload/
│   │   └── data-upload.spec.ts    # Flow 4
│   ├── dashboard/
│   │   └── dashboard.spec.ts      # Flow 5
│   ├── isolation/
│   │   └── data-isolation.spec.ts # Flows 6, 10
│   ├── chatbot/
│   │   └── chatbot.spec.ts        # Flow 7
│   ├── roles/
│   │   └── role-management.spec.ts # Flow 8
│   └── audit/
│       └── audit-logs.spec.ts     # Flow 9
│
├── utils/
│   └── helpers.ts        # API helpers, date utilities, auth utilities
│
├── .auth/                # Saved browser storage states (git-ignored)
│   ├── admin.json        # System admin auth state
│   └── impasto.json      # ImpastoCafe admin auth state
│
├── playwright.config.ts  # Playwright configuration
├── package.json
├── Jenkinsfile           # CI/CD pipeline definition
├── setup-jenkins.bat     # Windows Jenkins install script
└── .gitignore
```

---

## Test Flows

| # | Flow | Tag | File |
|---|------|-----|------|
| 1 | System Admin Login | `@smoke` | `tests/auth/login.spec.ts` |
| 2 | ImpastoCafe Workspace Login | `@smoke` | `tests/auth/login.spec.ts` |
| 3 | Invalid Credentials Rejection | `@regression` | `tests/auth/login.spec.ts` |
| 4 | Data Upload Validation | `@regression` | `tests/upload/data-upload.spec.ts` |
| 5 | Dashboard Stats Visible | `@smoke` | `tests/dashboard/dashboard.spec.ts` |
| 6 | Tenant Data Isolation (no cross-tenant leakage) | `@regression` | `tests/isolation/data-isolation.spec.ts` |
| 7 | Chatbot Responses & Festival Dates | `@regression` | `tests/chatbot/chatbot.spec.ts` |
| 8 | Role Management (RBAC) | `@regression` | `tests/roles/role-management.spec.ts` |
| 9 | Audit Logs (tenant-scoped only) | `@regression` | `tests/audit/audit-logs.spec.ts` |
| 10 | Session Management & Logout | `@smoke` | `tests/isolation/data-isolation.spec.ts` |

**Tags:**
- `@smoke` — Fast subset run before every deploy (~2 min, ~8 tests)
- `@regression` — Full suite, runs on main/master branch only (~10 min)

---

## Running Tests

```bash
# All tests (Chromium)
npm test

# Smoke tests only (CI gate)
npm run test:smoke

# Full regression
npm run test:regression

# With browser visible (debugging)
npm run test:headed

# Playwright UI mode (interactive)
npm run test:ui

# CI mode (parallel + retries)
npm run test:ci

# Specific test file
npx playwright test tests/auth/login.spec.ts

# Specific test by name
npx playwright test --grep "ImpastoCafe"

# View last HTML report
npx playwright show-report
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `https://aicafebuddy.com` | Target application URL |
| `IMPASTO_CAFE_PASSWORD` | — | Overrides ImpastoCafe password from `users.ts` |
| `SYSTEM_ADMIN_PASSWORD` | — | Overrides system admin password from `users.ts` |

```bash
# Run against local dev server
BASE_URL=http://localhost:5173 npm test
```

---

## Jenkins CI Setup

> **Full automated setup**: run `setup-jenkins.bat` to download and start Jenkins with step-by-step instructions.
>
> Or follow the manual steps below.

### Step 1 — Install Jenkins (Windows)

Jenkins runs as a Java application (no separate installer needed):

```batch
# Create Jenkins home directory
mkdir %USERPROFILE%\jenkins

# Download Jenkins LTS WAR file
powershell -Command "Invoke-WebRequest -Uri 'https://get.jenkins.io/war-stable/latest/jenkins.war' -OutFile '%USERPROFILE%\jenkins\jenkins.war'"

# Start Jenkins on port 8090 (8080 often used by other apps)
java -jar %USERPROFILE%\jenkins\jenkins.war --httpPort=8090 --JENKINS_HOME=%USERPROFILE%\jenkins\home
```

Then open: http://localhost:8090

### Step 2 — Unlock Jenkins

```batch
# Get the initial admin password
type %USERPROFILE%\jenkins\home\secrets\initialAdminPassword
```

Paste it into the browser → click **Install suggested plugins** → create admin account.

### Step 3 — Install Required Plugins

Go to **Manage Jenkins → Plugins → Available** and install:

| Plugin | Purpose |
|--------|---------|
| **NodeJS** | Run `npm ci`, `npx playwright` |
| **HTML Publisher** | Publish Playwright HTML report |
| **GitHub Integration** | Webhook trigger on push |
| **AnsiColor** | Colored console output |
| **Blue Ocean** | Modern pipeline UI (optional) |

### Step 4 — Configure NodeJS Tool

**Manage Jenkins → Tools → NodeJS → Add NodeJS:**
- Name: `NodeJS-22`
- Version: `22.x`
- ✅ Install automatically

### Step 5 — Add Credentials

**Manage Jenkins → Credentials → System → Global → Add Credentials:**

| Kind | ID | Secret |
|------|----|----|
| Secret text | `impasto-cafe-password` | `ImpastoCafe@123` |
| Secret text | `system-admin-password` | `cafe123` |

### Step 6 — Create the Pipeline Job

1. **New Item** → Enter `cafe-buddy-e2e` → Select **Pipeline** → OK
2. Under **Pipeline** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/snehamaheshwari/Cafe-Buddy-AI`
   - Branch: `*/main` or `*/master`
   - Script Path: `e2e/Jenkinsfile`
3. Save → **Build Now** to run the first time

### Step 7 — Configure GitHub Webhook (optional)

In your GitHub repo → **Settings → Webhooks → Add webhook:**
- Payload URL: `http://YOUR_IP:8090/github-webhook/`
- Content type: `application/json`
- Trigger: **Just the push event**

> **Note:** For local Jenkins, use [ngrok](https://ngrok.com) to expose port 8090:
> ```bash
> ngrok http 8090
> # Use the generated URL (e.g., https://abc123.ngrok.io/github-webhook/)
> ```

### Pipeline Flow

```
Push to GitHub
    │
    ▼
[Checkout]
    │
    ▼
[Install Dependencies]   npm ci
    │
    ▼
[Install Browsers]       npx playwright install chromium
    │
    ▼
[Auth Setup]             Save login state to .auth/
    │
    ▼
[Smoke Tests @smoke]     ← BLOCKS deployment on failure
    │
    ▼ (main/master only)
[Full Regression]        All tests
    │
    ▼
[Publish HTML Report]    playwright-report/index.html
    │
    ▼ (main/master only)
[Deploy Gate]            git push → Railway auto-deploy
```

---

## Adding New Tests

1. **Add a new page object** in `pages/` extending `BasePage`
2. **Create a spec file** in `tests/<feature>/`
3. **Tag critical tests** with `@smoke` (they gate deployment)
4. **Update `fixtures/testData.ts`** with any new test data constants
5. The `Jenkinsfile` picks up new tests automatically

### Example test skeleton

```typescript
import { test, expect } from '@playwright/test'
import { LoginPage }    from '../../pages/LoginPage'
import { USERS }        from '../../fixtures/users'

test.describe('Flow N — My New Feature @regression', () => {
  test('should do something', async ({ page }) => {
    const login = new LoginPage(page)
    await login.loginAs(USERS.IMPASTO_ADMIN)
    await page.waitForURL(/workspace=impasto-cafe/)

    // Your assertions here
    await expect(page.getByText('Expected Text')).toBeVisible()
  })
})
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Auth files missing (`.auth/`) | Run `npx playwright test tests/auth.setup.ts --project=setup` |
| Wrong workspace data showing | Check `?workspace=impasto-cafe` is in URL; re-login |
| Festival dates wrong | Confirm IST timezone fix is deployed; check `chatbot.py` |
| Jenkins can't find Node | Install NodeJS plugin + configure `NodeJS-22` in Tools |
| Tests slow / timing out | Increase `timeout` in `playwright.config.ts` or `test.setTimeout()` |
| Port 8090 already in use | Change `--httpPort=8090` to another port (e.g. 8091) |

---

## Contact

For issues or questions, contact the QA team or file a GitHub issue.
