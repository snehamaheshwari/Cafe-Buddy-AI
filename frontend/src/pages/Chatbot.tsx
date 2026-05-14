import { useEffect, useRef, useState } from 'react'
import {
  Send, Bot, User, Database, Globe, Calendar,
  Trash2, Sparkles, ChevronRight, Coffee, Loader,
} from 'lucide-react'
import Header from '../components/Header'

// ─── Types ───────────────────────────────────────────────────────────────────

interface Sources { data?: boolean; web?: boolean; festivals?: boolean }

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: Sources
  streaming?: boolean
  ts: string
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  { icon: '📊', text: 'Which was the highest selling item last week?' },
  { icon: '💰', text: 'What are my lowest margin items?' },
  { icon: '📅', text: 'What festival is coming next and what special dish should I introduce?' },
  { icon: '🎉', text: 'How should I handle Navratri in my café? Give me a full plan.' },
  { icon: '📱', text: 'Which platform generates the most revenue — Zomato, Swiggy, or Dine-in?' },
  { icon: '📈', text: 'Compare my weekend vs weekday sales.' },
  { icon: '🌟', text: 'Give me Diwali special menu and promotion ideas.' },
  { icon: '👨‍🍳', text: 'How can I increase my food cost efficiency?' },
]

function SourceBadge({ sources }: { sources?: Sources }) {
  if (!sources) return null
  const badges = []
  if (sources.data)      badges.push({ icon: <Database size={10} />, label: 'Your Data',       cls: 'bg-indigo-50 text-indigo-600 border-indigo-200' })
  if (sources.festivals) badges.push({ icon: <Calendar  size={10} />, label: 'Festival Calendar', cls: 'bg-brand-50 text-brand-600 border-brand-200' })
  if (sources.web)       badges.push({ icon: <Globe     size={10} />, label: 'Web Search',      cls: 'bg-emerald-50 text-emerald-600 border-emerald-200' })
  if (!badges.length)    return null
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {badges.map((b) => (
        <span key={b.label} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${b.cls}`}>
          {b.icon}{b.label}
        </span>
      ))}
    </div>
  )
}

function Markdown({ text }: { text: string }) {
  // Very lightweight markdown: **bold**, bullet lists, numbered lists, line breaks
  const html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code class="bg-slate-100 px-1 rounded text-xs font-mono">$1</code>')
    .replace(/^(\d+)\. (.+)$/gm, '<div class="flex gap-2 my-0.5"><span class="font-bold text-slate-500 flex-shrink-0">$1.</span><span>$2</span></div>')
    .replace(/^[-•] (.+)$/gm, '<div class="flex gap-2 my-0.5"><span class="text-brand-500 flex-shrink-0">•</span><span>$1</span></div>')
    .replace(/^─+.*─+$/gm, '<hr class="border-slate-200 my-2" />')
    .replace(/\n\n/g, '</p><p class="mt-2">')
    .replace(/\n/g, '<br />')
  return (
    <div
      className="text-sm text-slate-700 leading-relaxed"
      dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }}
    />
  )
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function Chatbot() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [aiMode, setAiMode]     = useState<boolean | null>(null)
  const [ddgMode, setDdgMode]   = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)
  const msgId     = useRef(0)

  const newId = () => ++msgId.current

  useEffect(() => {
    fetch('/api/chatbot/status').then((r) => r.json()).then((d) => {
      setAiMode(d.ai_mode)
      setDdgMode(d.web_search)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return
    setInput('')
    setLoading(true)

    const userMsg: Message = { id: newId(), role: 'user', content: text, ts: now() }
    const history = messages.map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, userMsg])

    // Placeholder AI message for streaming
    const aiId = newId()
    setMessages((prev) => [...prev, { id: aiId, role: 'assistant', content: '', streaming: true, ts: now() }])

    try {
      const res = await fetch('/api/chatbot/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      })

      if (!res.ok) throw new Error(`Server error ${res.status}`)
      if (!res.body)  throw new Error('No response body')

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let sources: Sources = {}
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const raw = line.slice(6).trim()
          if (!raw) continue
          try {
            const parsed = JSON.parse(raw)
            if (parsed.done) {
              sources = parsed.sources || {}
            } else if (parsed.text) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === aiId ? { ...m, content: m.content + parsed.text } : m
                )
              )
            }
          } catch { /* ignore malformed SSE lines */ }
        }
      }

      // Finalise: remove streaming flag, attach sources
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId ? { ...m, streaming: false, sources } : m
        )
      )
    } catch (err: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === aiId
            ? { ...m, content: `Sorry, something went wrong: ${err.message}`, streaming: false }
            : m
        )
      )
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const clearChat = () => setMessages([])

  return (
    <div className="flex flex-col h-screen">
      <Header title="Cafe Buddy AI" subtitle="Ask about your data, menu ideas, festivals, and more" />

      {/* Mode banner */}
      <div className={`px-6 py-2 text-xs font-medium flex items-center gap-6 border-b ${aiMode ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-amber-50 border-amber-200 text-amber-700'}`}>
        <span className="flex items-center gap-1.5">
          {aiMode ? <Sparkles size={12} /> : <Bot size={12} />}
          {aiMode ? 'Claude AI (claude-opus-4-7)' : 'Smart Analytics Engine'}
        </span>
        <span className="flex items-center gap-1.5">
          <Globe size={12} className={ddgMode ? 'text-emerald-500' : 'text-slate-400'} />
          {ddgMode ? 'Web search enabled' : 'Web search unavailable'}
        </span>
        <span className="flex items-center gap-1.5">
          <Calendar size={12} />
          Indian festival calendar active
        </span>
        {!aiMode && (
          <span className="ml-auto text-amber-600 italic">
            Set ANTHROPIC_API_KEY in backend .env for full AI mode
          </span>
        )}
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto bg-slate-50">
        {messages.length === 0 ? (
          /* Welcome / suggestions */
          <div className="max-w-3xl mx-auto px-4 py-10">
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-2xl bg-brand-500 flex items-center justify-center mx-auto mb-4 shadow-lg">
                <Coffee size={28} className="text-white" />
              </div>
              <h2 className="text-2xl font-bold text-slate-900">Cafe Buddy AI</h2>
              <p className="text-slate-500 mt-2 text-sm max-w-md mx-auto">
                Ask me anything about your café — sales data, festival menus, pricing strategies, or operational advice.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s.text}
                  onClick={() => sendMessage(s.text)}
                  className="flex items-start gap-3 p-4 bg-white border border-slate-200 rounded-lg text-left hover:border-brand-400 hover:shadow-sm transition-all group"
                >
                  <span className="text-xl flex-shrink-0">{s.icon}</span>
                  <span className="text-sm text-slate-700 group-hover:text-slate-900 leading-snug">{s.text}</span>
                  <ChevronRight size={14} className="text-slate-300 group-hover:text-brand-400 ml-auto flex-shrink-0 mt-0.5" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message list */
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  msg.role === 'user' ? 'bg-slate-700' : 'bg-brand-500'
                }`}>
                  {msg.role === 'user'
                    ? <User size={15} className="text-white" />
                    : <Bot  size={15} className="text-white" />}
                </div>

                {/* Bubble */}
                <div className={`max-w-[78%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
                  <div className={`rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-slate-800 text-white rounded-tr-sm'
                      : 'bg-white border border-slate-200 shadow-sm rounded-tl-sm'
                  }`}>
                    {msg.role === 'user' ? (
                      <p className="text-sm text-white leading-relaxed">{msg.content}</p>
                    ) : msg.streaming && !msg.content ? (
                      <TypingDots />
                    ) : (
                      <Markdown text={msg.content} />
                    )}
                    {msg.streaming && msg.content && (
                      <span className="inline-block w-1 h-4 bg-brand-400 animate-pulse ml-0.5 align-text-bottom" />
                    )}
                  </div>

                  {/* Sources + timestamp */}
                  {msg.role === 'assistant' && !msg.streaming && (
                    <SourceBadge sources={msg.sources} />
                  )}
                  <span className="text-xs text-slate-400 mt-1 px-1">{msg.ts}</span>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="bg-white border-t border-slate-200 px-4 py-3">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-3 bg-slate-50 border border-slate-300 rounded-xl px-4 py-2 focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100 transition-all">
            <textarea
              ref={inputRef}
              rows={1}
              className="flex-1 bg-transparent resize-none text-sm text-slate-800 placeholder-slate-400 focus:outline-none max-h-32 py-1.5 leading-snug"
              placeholder="Ask about your data, festivals, menu ideas…  (Enter to send, Shift+Enter for new line)"
              value={input}
              onChange={(e) => {
                setInput(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px'
              }}
              onKeyDown={handleKey}
            />
            <div className="flex items-center gap-2 pb-1 flex-shrink-0">
              {messages.length > 0 && (
                <button
                  onClick={clearChat}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors"
                  title="Clear chat"
                >
                  <Trash2 size={15} />
                </button>
              )}
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || loading}
                className={`p-2 rounded-lg transition-all ${
                  input.trim() && !loading
                    ? 'bg-brand-500 text-white hover:bg-brand-600 shadow-sm'
                    : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }`}
              >
                {loading ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-1.5 text-center">
            Cafe Buddy AI uses your uploaded data + festival calendar{ddgMode ? ' + live web search' : ''} to answer questions.
          </p>
        </div>
      </div>
    </div>
  )
}

function now() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}
