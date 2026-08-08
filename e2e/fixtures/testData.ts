import * as path from 'path'

/**
 * Paths to sample CSV/Excel files used in upload tests.
 * Drop real sample files into e2e/fixtures/files/ — they are gitignored.
 */
export const TEST_FILES = {
  POS_CSV:        path.join(__dirname, 'files', 'sample_pos.csv'),
  FINANCIAL_CSV:  path.join(__dirname, 'files', 'sample_financial.csv'),
  CUSTOMER_CSV:   path.join(__dirname, 'files', 'sample_customer.csv'),
  REVIEWS_CSV:    path.join(__dirname, 'files', 'sample_reviews.csv'),
  MENU_CSV:       path.join(__dirname, 'files', 'sample_menu.csv'),
  INVALID_FILE:   path.join(__dirname, 'files', 'invalid.txt'),
}

/** Minimum record counts expected after each sample upload */
export const MIN_RECORD_COUNTS = {
  pos:       10,
  financial:  3,
  customer:   5,
  reviews:    5,
  menu:       3,
}

/** UI labels for each dataset (matches DataCollection page) */
export const DATASET_LABELS = {
  financial: 'Money & Expenses',
  pos:       'Sales & Orders',
  customer:  'Customer Records',
  reviews:   'Customer Reviews',
  menu:      'Menu & Pricing',
}

/** Expected chatbot response keywords for festival queries */
export const FESTIVAL_KEYWORDS = [
  'festival', 'days', 'menu', 'promo', 'ideas',
]

/** Role names that must exist in the system tenant */
export const SYSTEM_ROLES = ['Admin', 'Sub-Admin', 'Viewer']

/** Audit log action types expected after login */
export const AUDIT_ACTIONS = ['LOGIN', 'LOGOUT', 'FILE_UPLOAD']
