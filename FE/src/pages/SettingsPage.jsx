import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getEmailSettings, saveEmailSettings } from '../api/auth'

export default function SettingsPage() {
  const qc = useQueryClient()
  const [password, setPassword] = useState('')
  const [saved, setSaved] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [ccEmails, setCcEmails] = useState([])
  const [ccInput, setCcInput] = useState('')
  const [ccError, setCcError] = useState('')

  const { data: settings, isLoading } = useQuery({
    queryKey: ['email-settings'],
    queryFn: getEmailSettings,
  })

  useEffect(() => {
    if (settings?.cc_emails) setCcEmails(settings.cc_emails)
  }, [settings])

  function addCcEmail() {
    const email = ccInput.trim().toLowerCase()
    if (!email) return
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setCcError('Invalid email address')
      return
    }
    if (ccEmails.includes(email)) {
      setCcError('Already added')
      return
    }
    setCcEmails((prev) => [...prev, email])
    setCcInput('')
    setCcError('')
  }

  function removeCcEmail(email) {
    setCcEmails((prev) => prev.filter((e) => e !== email))
  }

  function handleCcKeyDown(e) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      addCcEmail()
    }
  }

  const mutation = useMutation({
    mutationFn: () => saveEmailSettings({
      ...(password.trim() && { smtp_password: password }),
      cc_emails: ccEmails,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['email-settings'] })
      setPassword('')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Settings</h1>
      <p className="text-sm text-gray-500 mb-8">Configure your account to send emails from your own Gmail address.</p>

      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-6">
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-1">Email Configuration</h2>
          <p className="text-sm text-gray-500">
            All outbound emails (intro, pricing, follow-ups, etc.) will be sent from your Gmail account.
            Leave the app password blank to use the system default sender.
          </p>
        </div>

        {/* Sender email (read-only) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Sender Email</label>
          <input
            disabled
            value={isLoading ? '…' : settings?.email || ''}
            className="w-full border border-gray-200 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-600 cursor-not-allowed"
          />
          <p className="text-xs text-gray-400 mt-1">This is your login email — it cannot be changed here.</p>
        </div>

        {/* CC Emails */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">CC Emails</label>
          <p className="text-xs text-gray-400 mb-2">These addresses will be CC'd on every outbound email sent from your account.</p>
          <div className="flex gap-2">
            <input
              type="email"
              value={ccInput}
              onChange={(e) => { setCcInput(e.target.value); setCcError('') }}
              onKeyDown={handleCcKeyDown}
              placeholder="colleague@company.com"
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="button"
              onClick={addCcEmail}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Add
            </button>
          </div>
          {ccError && <p className="text-xs text-red-500 mt-1">{ccError}</p>}
          {ccEmails.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {ccEmails.map((email) => (
                <span key={email} className="flex items-center gap-1.5 text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-1 rounded-full">
                  {email}
                  <button type="button" onClick={() => removeCcEmail(email)} className="text-indigo-400 hover:text-indigo-700 leading-none">×</button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Status badge */}
        {!isLoading && (
          <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg border ${
            settings?.has_smtp_password
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-yellow-50 border-yellow-200 text-yellow-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${settings?.has_smtp_password ? 'bg-green-500' : 'bg-yellow-500'}`} />
            {settings?.has_smtp_password
              ? 'App password configured — emails sent from your Gmail account.'
              : 'No app password set — using system default sender.'}
          </div>
        )}

        {/* Gmail app password input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Gmail App Password {settings?.has_smtp_password && <span className="text-green-600 text-xs ml-1">(already set — enter new to replace)</span>}
          </label>
          <div className="relative">
            <input
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm pr-20"
              placeholder="xxxx xxxx xxxx xxxx"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-600"
            >
              {showPassword ? 'Hide' : 'Show'}
            </button>
          </div>
          {/* Step-by-step guide */}
          <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-amber-900 space-y-3">
            <p className="font-semibold text-amber-800">How to generate a Gmail App Password</p>
            <ol className="space-y-2 list-none">
              <li className="flex gap-2">
                <span className="shrink-0 w-5 h-5 rounded-full bg-amber-200 text-amber-800 text-xs font-bold flex items-center justify-center">1</span>
                <span>Make sure <strong>2-Step Verification</strong> is enabled on your Google account. Go to{' '}
                  <a href="https://myaccount.google.com/security" target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline font-medium">
                    myaccount.google.com/security
                  </a>{' '}→ scroll to "2-Step Verification" and turn it on if it isn't already.</span>
              </li>
              <li className="flex gap-2">
                <span className="shrink-0 w-5 h-5 rounded-full bg-amber-200 text-amber-800 text-xs font-bold flex items-center justify-center">2</span>
                <span>Open{' '}
                  <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer" className="text-indigo-600 hover:underline font-medium">
                    myaccount.google.com/apppasswords
                  </a>
                  {' '}(you may need to sign in again).</span>
              </li>
              <li className="flex gap-2">
                <span className="shrink-0 w-5 h-5 rounded-full bg-amber-200 text-amber-800 text-xs font-bold flex items-center justify-center">3</span>
                <span>In the <strong>"App name"</strong> field type <code className="bg-amber-100 px-1 rounded text-xs">SalesCatalyst</code> (or any name you prefer) and click <strong>Create</strong>.</span>
              </li>
              <li className="flex gap-2">
                <span className="shrink-0 w-5 h-5 rounded-full bg-amber-200 text-amber-800 text-xs font-bold flex items-center justify-center">4</span>
                <span>Google will show a <strong>16-character password</strong> (e.g. <code className="bg-amber-100 px-1 rounded text-xs">abcd efgh ijkl mnop</code>). Copy it — you won't see it again.</span>
              </li>
              <li className="flex gap-2">
                <span className="shrink-0 w-5 h-5 rounded-full bg-amber-200 text-amber-800 text-xs font-bold flex items-center justify-center">5</span>
                <span>Paste it into the field above (spaces are fine) and click <strong>Save App Password</strong>.</span>
              </li>
            </ol>
            <p className="text-xs text-amber-700 pt-1 border-t border-amber-200">
              Your regular Gmail password will <strong>not</strong> work here — you must use the App Password generated above.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-semibold px-5 py-2 rounded-lg transition-colors"
          >
            {mutation.isPending ? 'Saving…' : 'Save Settings'}
          </button>
          {saved && <span className="text-sm text-green-600 font-medium">Saved! Emails will now be sent from {settings?.email}.</span>}
          {mutation.isError && <span className="text-sm text-red-600">Save failed. Try again.</span>}
        </div>

        {/* Help box */}
        <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 text-sm text-blue-800 space-y-1">
          <p className="font-semibold">How it works</p>
          <p>Once configured, every campaign you create will send emails directly from <strong>{settings?.email}</strong> using Gmail SMTP (smtp.gmail.com:587 with TLS).</p>
          <p>Replies from leads will land in your Gmail inbox and be picked up by the system poller automatically.</p>
        </div>
      </div>
    </div>
  )
}
