import { Page, Locator, expect } from '@playwright/test'
import { BasePage } from './BasePage'

/**
 * ChatbotPage — Ask Cafe Buddy chatbot interface.
 */
export class ChatbotPage extends BasePage {
  // ── Locators ──────────────────────────────────────────────────────────────
  readonly chatInput:        Locator
  readonly sendButton:       Locator
  readonly messageList:      Locator
  readonly typingIndicator:  Locator
  readonly clearChatButton:  Locator
  readonly suggestionCards:  Locator

  constructor(page: Page) {
    super(page)
    this.chatInput       = page.getByRole('textbox', { name: /message|ask/i }).first()
    this.sendButton      = page.getByRole('button', { name: /send/i }).first()
    this.messageList     = page.locator('[class*="message"], [class*="chat"]').first()
    this.typingIndicator = page.locator('[class*="typing"], [class*="animate-bounce"]').first()
    this.clearChatButton = page.getByRole('button', { name: /clear|new chat/i }).first()
    this.suggestionCards = page.locator('[class*="suggestion"], [class*="SuggestionCard"]')
  }

  // ── Actions ───────────────────────────────────────────────────────────────

  async navigate(workspace?: string) {
    const base = workspace ? `/?workspace=${workspace}` : '/'
    await this.goto(base)
    await this.page.getByRole('link', { name: /ask cafe buddy|chatbot/i }).first().click()
    await this.waitForNetworkIdle()
  }

  /** Send a message and wait for the AI response */
  async sendMessage(text: string, waitForResponse = true): Promise<string> {
    await this.chatInput.fill(text)

    // Wait for the API response
    const responsePromise = waitForResponse
      ? this.page.waitForResponse(r => r.url().includes('/api/chatbot/ask') && r.request().method() === 'POST')
      : null

    await this.sendButton.click()

    if (responsePromise) {
      await responsePromise
      // Wait for animation to complete (text word-by-word render)
      await this.page.waitForTimeout(2000)
    }

    // Return the last assistant message content
    const assistantMessages = this.page.locator('[class*="assistant"], [role="status"]')
    const lastMsg = assistantMessages.last()
    return (await lastMsg.textContent()) || ''
  }

  /** Click a suggestion card */
  async clickSuggestion(index = 0) {
    await this.suggestionCards.nth(index).click()
    await this.page.waitForResponse(r => r.url().includes('/api/chatbot/ask'))
    await this.page.waitForTimeout(2000)
  }

  async clearChat() {
    await this.clearChatButton.click()
    const confirmBtn = this.page.getByRole('button', { name: /confirm|yes|clear/i }).first()
    if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmBtn.click()
    }
  }

  // ── Assertions ────────────────────────────────────────────────────────────

  async assertPageLoaded() {
    // Chat input must be visible
    await expect(this.chatInput).toBeVisible()
  }

  async assertResponseReceived(minLength = 20) {
    // Wait until typing indicator disappears (animation done)
    await expect(this.typingIndicator).not.toBeVisible({ timeout: 30_000 })

    const assistantMessages = this.page.locator('text=/Cafe Buddy AI|🤖/').first()
    // At least one assistant message with real content
    const allMessages = await this.page.locator('[class*="content"]').allTextContents()
    const hasSubstantialResponse = allMessages.some(t => t.length >= minLength)
    expect(hasSubstantialResponse).toBe(true)
  }

  async assertResponseContains(keywords: string[]) {
    const content = await this.page.content()
    for (const kw of keywords) {
      expect(content.toLowerCase()).toContain(kw.toLowerCase())
    }
  }

  async assertNoSystemTenantData() {
    // ImpastoCafe chatbot should not show admin data in its responses
    const content = await this.page.content()
    // Admin-specific system data markers should not appear
    expect(content).not.toContain('admin data')
  }

  async assertSuggestionCardsVisible() {
    await expect(this.suggestionCards.first()).toBeVisible()
    const count = await this.suggestionCards.count()
    expect(count).toBeGreaterThan(0)
  }

  async assertFestivalDatesCorrect() {
    // Verify "days away" is a reasonable number (< 365, > 0)
    const festivalText = await this.page.locator('text=/days away/').first().textContent()
    if (festivalText) {
      const match = festivalText.match(/(\d+) days away/)
      if (match) {
        const daysAway = parseInt(match[1])
        expect(daysAway).toBeGreaterThan(0)
        expect(daysAway).toBeLessThan(366)
      }
    }
  }
}
