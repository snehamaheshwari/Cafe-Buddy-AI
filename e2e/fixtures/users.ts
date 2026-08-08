/**
 * Test user credentials and workspace definitions.
 * Never put real production secrets here — use environment variables
 * for sensitive values in CI (see README).
 */

export interface TestUser {
  username:      string
  password:      string
  role:          string
  workspace?:    string   // undefined → system tenant (demo login)
  loginUrl:      string
  expectedHome:  string
}

export const USERS = {
  /** System / demo admin — no workspace slug, full access */
  SYSTEM_ADMIN: {
    username:     'admin',
    password:     process.env.SYSTEM_ADMIN_PASSWORD || 'cafe123',
    role:         'Admin',
    workspace:    undefined,
    loginUrl:     '/login',
    expectedHome: '/',
  } satisfies TestUser,

  /** Second system demo account */
  SYSTEM_OWNER: {
    username:     'owner',
    password:     process.env.SYSTEM_OWNER_PASSWORD || 'buddy@2024',
    role:         'Admin',
    workspace:    undefined,
    loginUrl:     '/login',
    expectedHome: '/',
  } satisfies TestUser,

  /** ImpastoCafe workspace tenant admin */
  IMPASTO_ADMIN: {
    username:     'ImpastoCafe',
    password:     process.env.IMPASTO_PASSWORD || 'ImpastoCafe@123',
    role:         'Admin',
    workspace:    'impasto-cafe',
    loginUrl:     '/login?workspace=impasto-cafe',
    expectedHome: '/?workspace=impasto-cafe',
  } satisfies TestUser,

  /** Invalid / negative-test credentials */
  INVALID_USER: {
    username:     'nonexistent_user',
    password:     'wrongpassword123',
    role:         'none',
    workspace:    'impasto-cafe',
    loginUrl:     '/login?workspace=impasto-cafe',
    expectedHome: '/login?workspace=impasto-cafe',   // stays on login
  } satisfies TestUser,
} as const
