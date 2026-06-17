import { useEffect, useState } from 'react'
import {
  MessageCircle, CheckCircle, AlertCircle, Send, Eye, RefreshCw,
  Phone, Bell, Clock, Info, Zap,
} from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

// ─── Persistence ──────────────────────────────────────────────────────────────
const STORAGE_KEY = 'cafebuddy_whatsapp_infinito_v1'

interface WaSettings {
  phone:        string
  scheduleHour: string
  enabled:      boolean
}

function loadSettings(): Partial<WaSettings> {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') } catch { return {} }
}
function saveSettings(s: WaSettings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
}

// ─── Hour picker options ───────────────────────────────────────────────────────
const HOURS = Array.from({ length: 24 }, (_, i) => {
  const h    = i % 12 || 12
  const ampm = i < 12 ? 'AM' : 'PM'
  return { value: String(i), label: `${h}:00 ${ampm}` }
})

// ─── Main Component ───────────────────────────────────────────────────────────
export default function WhatsAppNotifications() {
  const [settings, setSettings] = useState<WaSettings>(() => {
    const defaults: WaSettings = { phone: '', scheduleHour: '8', enabled: false }
    return { ...defaults, ...loadSettings() }
  })

  const [preview,        setPreview]        = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [sending,        setSending]        = useState(false)
  const [sendResult,     setSendResult]     = useState<{ ok: boolean; msg: string } | null>(null)
  const [saved,          setSaved]          = useState(false)

  useEffect(() => { fetchPreview() }, [])

  const fetchPreview = async () => {
    setPreviewLoading(true)
    try {
      const res = await api.notifications.getSummary()
      setPreview(res.preview)
    } catch {
      setPreview('Could not load preview — make sure your backend is running and you have uploaded some data.')
    } finally {
      setPreviewLoading(false)
    }
  }

  const update = (patch: Partial<WaSettings>) => setSettings(s => ({ ...s, ...patch }))

  const handleSave = () => {
    saveSettings(settings)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const handleSend = async () => {
    const phone = settings.phone.trim()
    if (!phone) {
      setSendResult({ ok: false, msg: 'Enter a recipient WhatsApp number first.' })
      return
    }
    setSending(true)
    setSendResult(null)
    try {
      const res: any = await api.notifications.sendWhatsApp({ phone })
      if (res?.success) {
        setSendResult({ ok: true, msg: 'Message sent! Check your WhatsApp.' })
      } else {
        setSendResult({ ok: false, msg: res?.message || 'Send failed. Check the phone number and try again.' })
      }
    } catch (e: any) {
      setSendResult({ ok: false, msg: e.message || 'Failed to send. Check the phone number format.' })
    } finally {
      setSending(false)
    }
  }

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <div>
      <Header
        title="WhatsApp Alerts"
        subtitle="Get your daily café summary delivered to WhatsApp — powered by Infinito"
      />

      <div className="p-4 md:p-6 space-y-6 max-w-4xl">

        {/* Provider banner */}
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-500 flex items-center justify-center flex-shrink-0">
              <MessageCircle size={20} className="text-white" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-bold text-green-800 flex items-center gap-2">
                Powered by Infinito (ValueFirst)
                <span className="inline-flex items-center gap-1 text-xs font-medium bg-green-200 text-green-800 px-2 py-0.5 rounded-full">
                  <Zap size={10} /> Active
                </span>
              </p>
              <p className="text-xs text-green-700 mt-1 leading-relaxed">
                WhatsApp notifications are sent via the <strong>Infinito unified messaging API</strong>.
                No credentials required — just enter your recipient phone number below and hit
                <strong> Send Test Message</strong>.
              </p>
            </div>
          </div>
        </div>

        {/* How it works */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
          <p className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Info size={14} className="text-blue-500" />
            How It Works
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              {
                step: '1',
                title: 'Enter your phone',
                desc:  'Add the WhatsApp number where you want to receive daily summaries (include country code).',
              },
              {
                step: '2',
                title: 'Send a test',
                desc:  'Click "Send Test Message" — the Infinito gateway delivers it to your WhatsApp instantly.',
              },
              {
                step: '3',
                title: 'Enable daily schedule',
                desc:  'Toggle the daily summary on and pick your preferred delivery time. That\'s it!',
              },
            ].map(({ step, title, desc }) => (
              <div key={step} className="flex gap-3">
                <div className="w-7 h-7 rounded-full bg-green-500 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                  {step}
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-700">{title}</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Settings form */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-5">
          <p className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Bell size={14} className="text-green-500" />
            Notification Settings
          </p>

          {/* Phone number */}
          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1 flex items-center gap-1">
              <Phone size={11} /> Recipient WhatsApp Number <span className="text-red-400">*</span>
            </label>
            <input
              type="tel"
              placeholder="+91 98765 43210"
              value={settings.phone}
              onChange={e => update({ phone: e.target.value })}
              className="w-full md:w-72 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-300 font-mono"
            />
            <p className="text-xs text-slate-400 mt-1">
              Include country code — e.g. <code>+91</code> for India.
              This is the number that will receive the daily summary.
            </p>
          </div>

          {/* API config info (read-only) */}
          <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
            <p className="text-xs font-semibold text-slate-600 mb-2">Infinito Gateway (pre-configured)</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                <span>API: <code className="text-slate-700">api.goinfinito.com</code></span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                <span>Sender: <code className="text-slate-700">+91 7428 309250</code></span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
                <span>Template: <code className="text-slate-700">{'{'}Daily Summary{'}'}</code></span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0" />
                <span className="text-amber-600 font-medium">Token valid until 30 Jul 2026</span>
              </div>
            </div>
          </div>

          {/* Schedule toggle */}
          <div className="flex items-center gap-4 pt-2 border-t border-slate-100 flex-wrap">
            <label className="flex items-center gap-2 cursor-pointer">
              <div
                onClick={() => update({ enabled: !settings.enabled })}
                className={`relative w-9 h-5 rounded-full transition-colors cursor-pointer ${settings.enabled ? 'bg-green-500' : 'bg-slate-300'}`}
              >
                <div className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${settings.enabled ? 'translate-x-4' : 'translate-x-0'}`} />
              </div>
              <span className="text-sm font-medium text-slate-700">Daily summary enabled</span>
            </label>

            {settings.enabled && (
              <div className="flex items-center gap-2 ml-auto">
                <Clock size={12} className="text-slate-400" />
                <label className="text-xs text-slate-600 font-medium">Send at</label>
                <select
                  value={settings.scheduleHour}
                  onChange={e => update({ scheduleHour: e.target.value })}
                  className="px-2 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-300 bg-white"
                >
                  {HOURS.map(h => <option key={h.value} value={h.value}>{h.label}</option>)}
                </select>
                <span className="text-xs text-slate-400">every day</span>
              </div>
            )}
          </div>

          {/* Send result */}
          {sendResult && (
            <div className={`flex items-start gap-2 px-3 py-2.5 rounded-lg text-xs border ${
              sendResult.ok
                ? 'bg-green-50 border-green-200 text-green-700'
                : 'bg-red-50 border-red-200 text-red-700'
            }`}>
              {sendResult.ok
                ? <CheckCircle size={13} className="mt-0.5 flex-shrink-0" />
                : <AlertCircle size={13} className="mt-0.5 flex-shrink-0" />}
              <span>{sendResult.msg}</span>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex items-center gap-2 flex-wrap pt-1">
            <button
              onClick={handleSend}
              disabled={sending}
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg bg-green-500 hover:bg-green-600 text-white transition-colors disabled:opacity-50"
            >
              {sending
                ? <><span className="w-3 h-3 border-2 border-green-300 border-t-white rounded-full animate-spin" /> Sending…</>
                : <><Send size={12} /> Send Test Message</>}
            </button>
            <button
              onClick={handleSave}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-lg border transition-colors ${
                saved
                  ? 'bg-emerald-500 text-white border-emerald-500'
                  : 'border-slate-300 text-slate-700 hover:bg-slate-50'
              }`}
            >
              {saved ? <><CheckCircle size={12} /> Saved!</> : 'Save Settings'}
            </button>
          </div>
        </div>

        {/* Message preview */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <Eye size={14} className="text-slate-500" />
              Preview of Your Daily Message
            </p>
            <button
              onClick={fetchPreview}
              disabled={previewLoading}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50"
            >
              <RefreshCw size={11} className={previewLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>

          {/* WhatsApp-style chat bubble */}
          <div className="bg-[#075e54] rounded-xl p-4">
            <div className="bg-[#dcf8c6] rounded-xl p-3 max-w-sm ml-auto">
              {previewLoading ? (
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <div className="w-3 h-3 border-2 border-slate-300 border-t-slate-500 rounded-full animate-spin" />
                  Loading preview…
                </div>
              ) : (
                <pre className="text-xs text-slate-800 whitespace-pre-wrap font-sans leading-relaxed">
                  {preview || 'Upload your data first to see a preview of your daily summary.'}
                </pre>
              )}
              <p className="text-right text-xs text-slate-400 mt-2">
                {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} ✓✓
              </p>
            </div>
          </div>

          <p className="text-xs text-slate-400">
            This preview is generated from your actual café data. The message is delivered
            through Infinito's WhatsApp Business gateway to any registered WhatsApp number.
          </p>
        </div>

      </div>
    </div>
  )
}
