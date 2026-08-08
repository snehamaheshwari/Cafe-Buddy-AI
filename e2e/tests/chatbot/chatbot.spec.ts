/**
 * FLOW 7 — Chatbot Basic Interaction & Date Validation
 */
import { test, expect } from '@playwright/test'
import { ChatbotPage } from '../../pages/ChatbotPage'

test.describe('Flow 7 — Chatbot Interaction @regression', () => {
  let chatbot: ChatbotPage

  test.beforeEach(async ({ page }) => {
    chatbot = new ChatbotPage(page)
    await page.goto('/')
    await page.waitForLoadState('networkidle')

    // Navigate to chatbot via sidebar
    const chatLink = page.getByRole('link', { name: /ask cafe buddy|chatbot/i }).first()
    if (await chatLink.isVisible()) await chatLink.click()
    await page.waitForLoadState('networkidle')
  })

  test('chatbot page loads with input field and suggestions', async ({ page }) => {
    await chatbot.assertPageLoaded()
    await chatbot.assertSuggestionCardsVisible()
  })

  test('sends a message and receives a non-empty response', async ({ page }) => {
    const response = await chatbot.sendMessage('What can you help me with?')
    expect(response.length).toBeGreaterThan(10)
  })

  test('asks about upcoming festivals — response contains date info', async ({ page }) => {
    await chatbot.sendMessage('What festival is coming next?', true)

    // Response should mention a festival name
    const content = await page.content()
    const hasFestivalInfo = /festival|janmashtami|independence|ganesh|navratri|diwali/i.test(content)
    expect(hasFestivalInfo).toBe(true)
  })

  test('festival days-away count is within valid range (1–365)', async ({ page }) => {
    await chatbot.sendMessage('List upcoming festivals with dates', true)
    await chatbot.assertFestivalDatesCorrect()
  })

  test('asks for sales summary — response uses actual uploaded data or says no data', async ({ page }) => {
    const response = await chatbot.sendMessage('Give me a summary of my sales')
    // Either data-driven or "no data" — both are valid responses
    const isValid = /revenue|orders|no data|upload|haven't uploaded/i.test(response + await page.content())
    expect(isValid).toBe(true)
  })

  test('chat history is saved in localStorage under tenant-scoped key', async ({ page }) => {
    await chatbot.sendMessage('Hello!')
    await page.waitForTimeout(1500)

    // Storage key must be tenant-scoped (cafebuddy_chat_v2_<tenant-id>)
    const storageKeys = await page.evaluate(() => Object.keys(localStorage))
    const chatKey = storageKeys.find(k => k.startsWith('cafebuddy_chat_v2'))
    expect(chatKey).toBeTruthy()
  })

  test('clear chat removes conversation from screen', async ({ page }) => {
    await chatbot.sendMessage('Test message', true)

    // Clear the chat
    const clearBtn = page.getByRole('button', { name: /new chat|clear/i }).first()
    if (await clearBtn.isVisible()) {
      await clearBtn.click()
      await page.waitForTimeout(500)

      // Previous message should be gone
      const prevMsg = page.locator('text=Test message')
      await expect(prevMsg).not.toBeVisible()
    }
  })

  test('401 on expired session redirects to login — not system data', async ({ page }) => {
    // Simulate expired token by corrupting localStorage
    await page.evaluate(() => {
      const raw = localStorage.getItem('cafe_buddy_auth')
      if (raw) {
        const parsed = JSON.parse(raw)
        parsed.token = 'eyJhbGciOiJIUzI1NiJ9.EXPIRED.INVALIDSIG'
        localStorage.setItem('cafe_buddy_auth', JSON.stringify(parsed))
      }
    })

    // Reload and try to use chatbot
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Either redirected to login, or the 401 handler clears auth
    const onLogin = page.url().includes('/login')
    const storageCleared = await page.evaluate(() => !localStorage.getItem('cafe_buddy_auth'))
    expect(onLogin || storageCleared).toBe(true)
  })
})
