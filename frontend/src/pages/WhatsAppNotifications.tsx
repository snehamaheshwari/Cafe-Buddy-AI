import { useEffect, useState } from 'react'
import {
  MessageCircle, CheckCircle, AlertCircle, Send, Eye, RefreshCw,
  Phone, Key, Bell, ExternalLink, Info, Clock, Smartphone,
} from 'lucide-react'
import Header from '../components/Header'
import { api } from '../lib/api'

const STORAGE_KEY = 'cafebuddy_whatsapp_v2'

interface WaSettings {
  idInstance: string
  apiTokenInstance: string
  phone: string
  scheduleHour: string
  enabled: boolean
}

function loadSettings(): Partial<WaSettings> {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') } catch { return {} }
}

function saveSettings(s: WaSettings) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
}

const HOURS = Array.from({ length: 24 }, (_, i) => {
  const h = i % 12 || 12
  const ampm = i < 12 ? 'AM' : 'PM'
  return { value: String(i), label: `${h}:00 ${ampm}` }
})

export default function WhatsAppNotifications() {
  const [settings, setSettings] = useState<WaSettings>(() => {
    const defaults: WaSettings = { idInstance: '', apiTokenInstance: '', phone: '', scheduleHour: '8', enabled: false }
    return { ...defaults, ...loadSettings() }
  })
  const [preview, setPreview] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [sendResult, setSendResult] = useState<{ ok: boolean; msg: string } | null>(null)
  const [saved, setSaved] = useState(false)

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

  const update = (patch: Partial<WaSettings>) => setSettings((s) => ({ ...s, ...patch }))

  const handleSave = () => {
    saveSettings(settings)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  const handleSend = async () => {
    if (!settings.idInstance || !settings.apiTokenInstance || !settings.phone) {
      setSendResult({ ok: false, msg: 'Fill in your Instance ID, API Token, and phone number first.' })
      return
    }
    setSending(true)
    setSendResult(null)
    try {
      const res: any = await api.notifications.sendWhatsApp({
        idInstance: settings.idInstance,
        apiTokenInstance: settings.apiTokenInstance,
        phone: settings.phone,
      })
      if (res?.success) {
        setSendResult({ ok: true, msg: 'Message sent! Check your WhatsApp.' })
      } else {
        setSendResult({ ok: false, msg: res?.message || 'Send failed. Check your credentials.' })
      }
    } catch (e: any) {
      setSendResult({ ok: false, msg: e.message || 'Failed to send. Check Instance ID, API token and phone.' })
    } finally {
      setSending(false)
    }
  }

  return (
    <div>
      <Header
        title="WhatsApp Alerts"
        subtitle="Get your daily café summary and action items sent to your WhatsApp — completely free via Green API"
      />

      <div className="p-4 md:p-6 space-y-6 max-w-4xl">

        {/* Banner */}
        <div className="bg-green-50 border border-green-200 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-green-500 flex items-center justify-center flex-shrink-0">
              <MessageCircle size={20} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-bold text-green-800">100% Free — Powered by Green API</p>
              <p className="text-xs text-green-700 mt-1 leading-relaxed">
                Green API connects your personal WhatsApp to Cafe Buddy via a QR code scan.
                The free developer plan includes <strong>500 messages/month</strong> — more than enough for daily summaries.
                No credit card. No WhatsApp Business account needed.
              </p>
            </div>
          </div>
        </div>

        {/* 3-Step Setup */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-5">
          <p className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Info size={14} className="text-blue-500" />
            One-time Setup (3 steps — takes 2 minutes)
          </p>

          <div className="space-y-5">
            {/* Step 1 */}
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-green-500 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">1</div>
              <div>
                <p className="text-sm font-semibold text-slate-700">Create a free Green API account</p>
                <p className="text-xs text-slate-500 mt-1">
                  Go to <strong>green-api.com</strong> and register. Select the <strong>Developer</strong> plan (free, 500 msg/month).
                </p>
                <a
                  href="https://green-api.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-500 hover:text-blue-700 mt-1.5 font-medium"
                >
                  Open green-api.com <ExternalLink size={10} />
                </a>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-green-500 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">2</div>
              <div>
                <p className="text-sm font-semibold text-slate-700">Create an instance and scan the QR code</p>
                <p className="text-xs text-slate-500 mt-1">
                  In your Green API dashboard, click <strong>"Create Instance"</strong>. Open the instance settings and scan the QR code with your WhatsApp (the same way you use WhatsApp Web).
                </p>
                <div className="mt-2 flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg">
                  <Smartphone size={12} className="text-slate-400" />
                  <span className="text-xs text-slate-600">WhatsApp → Menu → Linked Devices → Link a Device → scan QR</span>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex gap-3">
              <div className="w-7 h-7 rounded-full bg-green-500 text-white text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">3</div>
              <div>
                <p className="text-sm font-semibold text-slate-700">Copy your Instance ID and API Token below</p>
                <p className="text-xs text-slate-500 mt-1">
                  From your Green API dashboard, copy the <strong>idInstance</strong> (a number like 1101234567) and the <strong>apiTokenInstance</strong> (a long string). Paste them below and hit "Send Test Message".
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Settings form */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
          <p className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Bell size={14} className="text-green-500" />
            Your Green API Settings
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1 flex items-center gap-1">
                <Key size={11} /> Instance ID
              </label>
              <input
                type="text"
                placeholder="1101234567"
                value={settings.idInstance}
                onChange={(e) => update({ idInstance: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-300 font-mono"
              />
              <p className="text-xs text-slate-400 mt-1">Found in your Green API dashboard</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1 flex items-center gap-1">
                <Key size={11} /> API Token Instance
              </label>
              <input
                type="password"
                placeholder="paste your apiTokenInstance here"
                value={settings.apiTokenInstance}
                onChange={(e) => update({ apiTokenInstance: e.target.value })}
                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-300 font-mono"
              />
              <p className="text-xs text-slate-400 mt-1">Long token string from the dashboard</p>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1 flex items-center gap-1">
              <Phone size={11} /> Recipient WhatsApp Number
            </label>
            <input
              type="tel"
              placeholder="+919876543210"
              value={settings.phone}
              onChange={(e) => update({ phone: e.target.value })}
              className="w-full md:w-64 px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-300 font-mono"
            />
            <p className="text-xs text-slate-400 mt-1">Include country code — e.g. +91 for India. This is the number that will receive the message (usually your own number).</p>
          </div>

          {/* Schedule */}
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
                  onChange={(e) => update({ scheduleHour: e.target.value })}
                  className="px-2 py-1 text-xs border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-300 bg-white"
                >
                  {HOURS.map((h) => <option key={h.value} value={h.value}>{h.label}</option>)}
                </select>
                <span className="text-xs text-slate-400">every day</span>
              </div>
            )}
          </div>

          {/* Result */}
          {sendResult && (
            <div className={`flex items-start gap-2 px-3 py-2.5 rounded-lg text-xs border ${
              sendResult.ok ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
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
                saved ? 'bg-emerald-500 text-white border-emerald-500' : 'border-slate-300 text-slate-700 hover:bg-slate-50'
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

          {/* WhatsApp-style bubble */}
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
            This message is generated from your actual café data. With Green API your WhatsApp stays connected as a linked device — the same as WhatsApp Web.
          </p>
        </div>

      </div>
    </div>
  )
}
