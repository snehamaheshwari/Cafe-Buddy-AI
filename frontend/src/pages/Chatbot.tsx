import { useEffect, useRef, useState } from 'react'
import {
  Send, Bot, User, Database, Globe, Calendar,
  Trash2, Sparkles, ChevronRight, Coffee, Loader,
  LayoutGrid, X, PlusCircle, AlertCircle, Pencil, MessageCircle,
} from 'lucide-react'
import Header from '../components/Header'

const STORAGE_KEY = 'cafebuddy_chat_v2'

interface Sources { data?: boolean; web?: boolean; festivals?: boolean }
interface Message {
  id: number; role: 'user' | 'assistant'; content: string
  sources?: Sources; animating?: boolean; ts: string
}

const SUGGESTIONS = [
  { icon: '📦', text: 'According to review data, which product should I stock more of?' },
  { icon: '📊', text: 'Which was the highest selling item last week?' },
  { icon: '💰', text: 'What are my lowest margin items?' },
  { icon: '📅', text: 'What festival is coming next and what special dish should I introduce?' },
  { icon: '🎉', text: 'How should I handle Navratri in my café? Give me a full plan.' },
  { icon: '📱', text: 'Which platform generates the most revenue — Zomato, Swiggy, or Dine-in?' },
  { icon: '📈', text: 'Compare my weekend vs weekday sales.' },
  { icon: '⭐', text: 'What do customers say in reviews? Show sentiment breakdown.' },
  { icon: '🍽️', text: 'How is each category performing — Beverages, Mains, Starters?' },
  { icon: '🌟', text: 'Give me Diwali special menu and promotion ideas.' },
  { icon: '👨‍🍳', text: 'How can I increase my food cost efficiency?' },
  { icon: '📍', text: 'Which location has the highest customer satisfaction?' },
]

function now() {
  return new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}

function saveToStorage(messages: Message[], nextId: number) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ messages: messages.map(m => ({ ...m, animating: false })), nextId })) } catch { }
}

function loadFromStorage(): { messages: Message[]; nextId: number } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function SourceBadge({ sources }: { sources?: Sources }) {
  if (!sources) return null
  const badges = []
  if (sources.data)      badges.push({ icon: <Database size={10} />, label: 'Your Data',        cls: 'bg-indigo-50 text-indigo-600 border-indigo-200' })
  if (sources.festivals) badges.push({ icon: <Calendar  size={10} />, label: 'Festival Calendar', cls: 'bg-orange-50 text-orange-600 border-orange-200' })
  if (sources.web)       badges.push({ icon: <Globe     size={10} />, label: 'Web Search',        cls: 'bg-emerald-50 text-emerald-600 border-emerald-200' })
  if (!badges.length) return null
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {badges.map(b => (
        <span key={b.label} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${b.cls}`}>
          {b.icon}{b.label}
        </span>
      ))}
    </div>
  )
}

function Markdown({ text }: { text: string }) {
  const html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code class="bg-slate-100 px-1 rounded text-xs font-mono">$1</code>')
    .replace(/^(\d+)\. (.+)$/gm, '<div class="flex gap-2 my-0.5"><span class="font-bold text-slate-500 flex-shrink-0">$1.</span><span>$2</span></div>')
    .replace(/^─+.*─+$/gm, '<hr class="border-slate-200 my-2" />')
    .replace(/\n\n/g, '</p><p class="mt-2">')
    .replace(/\n/g, '<br />')
  return (
    <div className="text-sm text-slate-700 leading-relaxed"
      dangerouslySetInnerHTML={{ __html: `<p>${html}</p>` }} />
  )
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map(i => (
        <div key={i} className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </div>
  )
}

function SuggestionCard({ s, onClick, compact = false }: { s: typeof SUGGESTIONS[0]; onClick: () => void; compact?: boolean }) {
  return (
    <button onClick={onClick}
      className={`flex items-start gap-3 bg-white border border-slate-200 rounded-xl text-left hover:border-brand-400 hover:shadow-sm transition-all group ${compact ? 'p-3' : 'p-4'}`}>
      <span className={`flex-shrink-0 ${compact ? 'text-lg' : 'text-xl'}`}>{s.icon}</span>
      <span className={`text-slate-700 group-hover:text-slate-900 leading-snug ${compact ? 'text-xs' : 'text-sm'}`}>{s.text}</span>
      <ChevronRight size={12} className="text-slate-300 group-hover:text-brand-400 ml-auto flex-shrink-0 mt-0.5" />
    </button>
  )
}

export default function Chatbot() {
  const [messages, setMessages]       = useState<Message[]>([])
  const [input, setInput]             = useState('')
  const [loading, setLoading]         = useState(false)
  const [aiMode, setAiMode]           = useState<boolean | null>(null)
  const [ddgMode, setDdgMode]         = useState(false)
  const [showMenu, setShowMenu]       = useState(false)
  const [clearConfirm, setClearConfirm] = useState(false)
  const [hasData, setHasData]         = useState<boolean | null>(null)
  const [editingId, setEditingId]     = useState<number | null>(null)

  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)
  const msgId     = useRef(0)
  const animRef   = useRef<ReturnType<typeof setTimeout> | null>(null)

  const newId = () => ++msgId.current

  useEffect(() => {
    const saved = loadFromStorage()
    if (saved?.messages.length) {
      setMessages(saved.messages)
      msgId.current = saved.nextId
    }
    fetch('/api/chatbot/status').then(r => r.json()).then(d => {
      setAiMode(d.ai_mode); setDdgMode(d.web_search)
    }).catch(() => {})
    fetch('/api/upload/status/all').then(r => r.json()).then((all: any) => {
      setHasData(Object.values(all).some((v: any) => v?.uploaded))
    }).catch(() => setHasData(false))
  }, [])

  useEffect(() => {
    if (messages.length > 0 && !messages.some(m => m.animating))
      saveToStorage(messages, msgId.current)
  }, [messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!showMenu) return
    const handle = (e: MouseEvent) => {
      const panel = document.getElementById('chat-menu-panel')
      if (panel && !panel.contains(e.target as Node)) setShowMenu(false)
    }
    document.addEventListener('mousedown', handle)
    return () => document.removeEventListener('mousedown', handle)
  }, [showMenu])

  // Animate text word-by-word client-side (works through any proxy/tunnel)
  const animateText = (aiId: number, fullText: string, sources: Sources) => {
    const words = fullText.split(' ')
    let i = 0
    const tick = () => {
      if (i >= words.length) {
        setMessages(prev => prev.map(m => m.id === aiId ? { ...m, animating: false, sources } : m))
        setLoading(false)
        inputRef.current?.focus()
        return
      }
      const chunk = words.slice(0, i + 1).join(' ')
      setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: chunk } : m))
      i++
      animRef.current = setTimeout(tick, 22)
    }
    tick()
  }

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return
    setInput('')
    setShowMenu(false)
    setEditingId(null)
    setLoading(true)

    const userMsg: Message = { id: newId(), role: 'user', content: text, ts: now() }
    const history = messages.map(m => ({ role: m.role, content: m.content }))
    setMessages(prev => [...prev, userMsg])

    const aiId = newId()
    setMessages(prev => [...prev, { id: aiId, role: 'assistant', content: '', animating: true, ts: now() }])

    try {
      const res = await fetch('/api/chatbot/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      animateText(aiId, data.text || 'No response received.', data.sources || {})
    } catch (err: any) {
      const raw: string = err?.message ?? ''
      let friendly = 'Something went wrong. Please try again.'
      if (raw.includes('502') || raw.includes('503') || raw.includes('504')) {
        friendly = 'Server is temporarily busy — please try again in a moment.'
      } else if (raw.includes('Failed to fetch') || raw.includes('NetworkError') || raw.includes('ERR_')) {
        friendly = 'Could not reach the server. Check that the backend is running.'
      }
      setMessages(prev => prev.map(m => m.id === aiId ? { ...m, content: friendly, animating: false } : m))
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input) }
  }

  const clearChat = () => {
    if (animRef.current) clearTimeout(animRef.current)
    setMessages([]); setClearConfirm(false); setShowMenu(false); setEditingId(null)
    localStorage.removeItem(STORAGE_KEY); msgId.current = 0
  }

  const startEdit = (msg: Message) => {
    if (loading) return
    setMessages(prev => prev.slice(0, prev.findIndex(m => m.id === msg.id)))
    setInput(msg.content); setEditingId(msg.id)
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus()
        inputRef.current.style.height = 'auto'
        inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 128) + 'px'
      }
    }, 50)
  }

  const inChat = messages.length > 0

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <Header title="Ask Cafe Buddy" subtitle="Your AI café assistant — ask anything about your business" />

      {/* Mode banner */}
      <div className={`px-4 py-2 text-xs font-medium flex flex-wrap items-center gap-x-5 gap-y-1 border-b ${
        aiMode ? 'bg-emerald-50 border-emerald-200 text-emerald-700' : 'bg-amber-50 border-amber-200 text-amber-700'
      }`}>
        <span className="flex items-center gap-1.5">
          {aiMode ? <Sparkles size={12} /> : <Bot size={12} />}
          {aiMode ? 'Claude AI (Full Power)' : 'Smart Analytics Engine'}
        </span>
        <span className="flex items-center gap-1.5">
          <Globe size={12} className={ddgMode ? 'text-emerald-500' : 'text-slate-400'} />
          {ddgMode ? 'Web search on' : 'Web search off'}
        </span>
        <span className="flex items-center gap-1.5">
          <Calendar size={12} />Festival calendar active
        </span>
        {inChat && (
          <span className="ml-auto text-slate-500">{messages.filter(m => m.role === 'user').length} questions this session</span>
        )}
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto relative">
        {!inChat ? (
          <div className="max-w-3xl mx-auto px-4 py-8 md:py-10">
            <div className="text-center mb-8">
              <div className="w-16 h-16 rounded-2xl bg-brand-500 flex items-center justify-center mx-auto mb-4 shadow-lg">
                <MessageCircle size={28} className="text-white" />
              </div>
              <h2 className="text-xl md:text-2xl font-bold text-slate-900">Ask Cafe Buddy Anything</h2>
              <p className="text-slate-500 mt-2 text-sm max-w-md mx-auto">
                Sales analysis, menu ideas, festival planning, cost reduction — just ask.
              </p>
            </div>

            {hasData === false && (
              <div className="mb-5 flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
                <AlertCircle size={16} className="flex-shrink-0 mt-0.5 text-amber-500" />
                <div>
                  <p className="font-semibold mb-0.5">No data uploaded yet</p>
                  <p className="text-xs text-amber-700">
                    Sales analysis needs your data first.{' '}
                    <a href="/data-collection" className="underline font-medium hover:text-amber-900">Upload your data →</a>{' '}
                    Festival ideas and general advice work without data.
                  </p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {SUGGESTIONS.map(s => (
                <SuggestionCard key={s.text} s={s} onClick={() => sendMessage(s.text)} />
              ))}
            </div>
          </div>
        ) : (
          <div>
            {/* Toolbar */}
            <div className="sticky top-0 z-10 bg-white/95 backdrop-blur border-b border-slate-100 px-4 py-2 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {messages.filter(m => m.role === 'user').length} questions this session
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => { setShowMenu(v => !v); setClearConfirm(false) }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    showMenu ? 'bg-brand-500 text-white border-brand-500' : 'bg-white text-slate-600 border-slate-200 hover:border-brand-400'
                  }`}
                >
                  <LayoutGrid size={13} />
                  <span className="hidden sm:inline">More Questions</span>
                </button>
                {clearConfirm ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-red-500 font-medium">Clear all?</span>
                    <button onClick={clearChat} className="px-2.5 py-1 rounded text-xs font-semibold bg-red-500 text-white hover:bg-red-600">Yes</button>
                    <button onClick={() => setClearConfirm(false)} className="px-2.5 py-1 rounded text-xs border border-slate-200 text-slate-600">No</button>
                  </div>
                ) : (
                  <button onClick={() => { setClearConfirm(true); setShowMenu(false) }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-slate-200 bg-white text-slate-500 hover:border-red-300 hover:text-red-500 transition-colors">
                    <PlusCircle size={13} />
                    <span className="hidden sm:inline">New Chat</span>
                  </button>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="max-w-3xl mx-auto px-3 md:px-4 py-6 space-y-6">
              {messages.map(msg => (
                <div key={msg.id} className={`flex gap-2 md:gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'user' ? 'bg-slate-700' : 'bg-brand-500'}`}>
                    {msg.role === 'user' ? <User size={14} className="text-white" /> : <Bot size={14} className="text-white" />}
                  </div>
                  <div className={`max-w-[85%] md:max-w-[78%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                    <div className={`rounded-2xl px-4 py-3 ${
                      msg.role === 'user' ? 'bg-slate-800 text-white rounded-tr-sm' : 'bg-white border border-slate-200 shadow-sm rounded-tl-sm'
                    }`}>
                      {msg.role === 'user' ? (
                        <div className="group relative">
                          <p className="text-sm text-white leading-relaxed pr-5">{msg.content}</p>
                          <button onClick={() => startEdit(msg)} disabled={loading} title="Edit"
                            className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity p-0.5 rounded text-slate-300 hover:text-white disabled:cursor-not-allowed">
                            <Pencil size={11} />
                          </button>
                        </div>
                      ) : msg.animating && !msg.content ? (
                        <TypingDots />
                      ) : (
                        <>
                          <Markdown text={msg.content} />
                          {msg.animating && msg.content && (
                            <span className="inline-block w-1 h-4 bg-brand-400 animate-pulse ml-0.5 align-text-bottom" />
                          )}
                        </>
                      )}
                    </div>
                    {msg.role === 'assistant' && !msg.animating && <SourceBadge sources={msg.sources} />}
                    <span className="text-xs text-slate-400 mt-1 px-1">{msg.ts}</span>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          </div>
        )}
      </div>

      {/* Slide-up question menu */}
      {showMenu && inChat && (
        <div id="chat-menu-panel" className="border-t border-slate-200 bg-white shadow-2xl" style={{ maxHeight: '45vh', overflowY: 'auto' }}>
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 sticky top-0 bg-white z-10">
            <div>
              <p className="text-sm font-semibold text-slate-800">More Questions</p>
              <p className="text-xs text-slate-400">Pick one to add to the chat</p>
            </div>
            <button onClick={() => setShowMenu(false)} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100">
              <X size={16} />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-4">
            {SUGGESTIONS.map(s => <SuggestionCard key={s.text} s={s} compact onClick={() => sendMessage(s.text)} />)}
          </div>
        </div>
      )}

      {/* Input bar */}
      <div className={`bg-white border-t px-3 md:px-4 py-3 ${editingId ? 'border-amber-300 bg-amber-50' : 'border-slate-200'}`}>
        <div className="max-w-3xl mx-auto">
          <div className="flex items-end gap-2 md:gap-3 bg-slate-50 border border-slate-300 rounded-xl px-3 md:px-4 py-2 focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-100 transition-all">
            <textarea
              ref={inputRef}
              rows={1}
              className="flex-1 bg-transparent resize-none text-sm text-slate-800 placeholder-slate-400 focus:outline-none max-h-32 py-1.5 leading-snug"
              placeholder="Ask about your sales, reviews, festivals, strategy…"
              value={input}
              onChange={e => {
                setInput(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px'
              }}
              onKeyDown={handleKey}
            />
            <div className="flex items-center gap-1 pb-1 flex-shrink-0">
              {inChat && (
                <button onClick={() => { setShowMenu(v => !v); setClearConfirm(false) }} title="More questions"
                  className={`p-1.5 rounded-lg transition-colors ${showMenu ? 'text-brand-500 bg-brand-50' : 'text-slate-400 hover:text-brand-500 hover:bg-brand-50'}`}>
                  <LayoutGrid size={15} />
                </button>
              )}
              {inChat && (
                <button onClick={() => { setClearConfirm(true); setShowMenu(false) }} title="New Chat"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 transition-colors">
                  <Trash2 size={15} />
                </button>
              )}
              <button
                onClick={() => sendMessage(input)}
                disabled={!input.trim() || loading}
                className={`p-2 rounded-lg transition-all ${
                  input.trim() && !loading ? 'bg-brand-500 text-white hover:bg-brand-600 shadow-sm' : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }`}
              >
                {loading ? <Loader size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </div>
          </div>
          {editingId ? (
            <p className="text-xs text-amber-600 mt-1.5 text-center flex items-center justify-center gap-1">
              <Pencil size={11} /> Editing — modify and press Enter to resend
              <button onClick={() => { setInput(''); setEditingId(null) }} className="ml-2 underline">Cancel</button>
            </p>
          ) : (
            <p className="text-xs text-slate-400 mt-1.5 text-center">
              Analyses your data · festival calendar{ddgMode ? ' · live web search' : ''}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
