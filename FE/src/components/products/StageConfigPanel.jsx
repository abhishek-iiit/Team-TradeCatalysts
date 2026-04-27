import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getStageConfigs, saveStageConfig } from '../../api/stageConfigs'

const STAGE_LABELS = {
  intro:        'Intro',
  documents:    'Documents',
  requirements: 'Ask Requirements',
  pricing:      'Pricing',
  followup:     'Follow-Up on Pricing',
  meeting:      'Meeting',
  deal:         'Deal',
}

const STAGE_HINTS = {
  intro:        'First contact — introduce your company and product',
  documents:    'Share product brochure / technical datasheet',
  requirements: 'Ask about quantity, packing, quality certs, delivery port',
  pricing:      'Provide competitive pricing based on their requirements',
  followup:     'Include payment terms and lead time in this follow-up',
  meeting:      'Invite the prospect for a call or meeting',
  deal:         'Best offer — competitive margin + sample request',
}

function StageRow({ productId, config }) {
  const qc = useQueryClient()
  const stage = config.stage
  const [open, setOpen] = useState(false)
  const [subject, setSubject] = useState(config.subject_line || '')
  const [content, setContent] = useState(config.email_content || '')
  const [triggerDays, setTriggerDays] = useState(config.trigger_days ?? 4)
  const [file, setFile] = useState(null)
  const [saved, setSaved] = useState(false)

  const mutation = useMutation({
    mutationFn: () => {
      const form = new FormData()
      form.append('subject_line', subject)
      form.append('email_content', content)
      form.append('trigger_days', triggerDays)
      if (file) form.append('document', file)
      return saveStageConfig(config.id, productId, stage, form)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['stage-configs', productId] })
      setFile(null)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    },
  })

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 text-sm font-medium text-gray-700 transition-colors"
      >
        <span className="flex flex-col items-start text-left">
          <span>{STAGE_LABELS[stage]}</span>
          <span className="text-xs font-normal text-gray-400">{STAGE_HINTS[stage]}</span>
        </span>
        <span className="flex items-center gap-2">
          {config.has_document && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">Doc attached</span>
          )}
          {config.subject_line && (
            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">Configured</span>
          )}
          <span className="text-gray-400">{open ? '▲' : '▼'}</span>
        </span>
      </button>

      {open && (
        <div className="p-4 space-y-3 bg-white">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Subject Line</label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
              placeholder={`e.g. Introduction | Acetone`}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Email Content</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={5}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm font-mono"
              placeholder="Dear {contact_name}, ..."
            />
          </div>

          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">Trigger After (days)</label>
              <input
                type="number"
                min={1}
                max={365}
                value={triggerDays}
                onChange={(e) => setTriggerDays(Number(e.target.value))}
                className="w-24 border border-gray-300 rounded-md px-3 py-2 text-sm"
              />
            </div>

            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Attachment {config.has_document && '(replace)'}
              </label>
              <label className="inline-flex items-center gap-2 cursor-pointer border border-gray-300 rounded-md px-3 py-1.5 text-sm text-gray-600 bg-white hover:bg-gray-50 transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                {file ? file.name : config.has_document ? 'Replace file' : 'Choose file'}
                <input
                  type="file"
                  accept=".pdf,.doc,.docx,.png,.jpg"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files[0] || null)}
                />
              </label>
              {file && <p className="text-xs text-indigo-600 mt-1">{file.name}</p>}
              {!file && config.has_document && (
                <p className="text-xs text-green-600 mt-1">Document already attached</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors"
            >
              {mutation.isPending ? 'Saving…' : 'Save Stage Config'}
            </button>
            {saved && <span className="text-xs text-green-600 font-medium">Saved!</span>}
            {mutation.isError && (
              <span className="text-xs text-red-600">
                {mutation.error?.response?.data?.detail || 'Save failed'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function StageConfigPanel({ productId }) {
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['stage-configs', productId],
    queryFn: () => getStageConfigs(productId),
  })

  if (isLoading) return <p className="text-xs text-gray-400 py-2">Loading stage configs…</p>

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Email Stage Configuration</p>
      {configs.map((config) => (
        <StageRow key={config.stage} productId={productId} config={config} />
      ))}
    </div>
  )
}
