import { useEffect, useMemo, useState } from 'react'

import { statusFromOutcome } from '../constants/outcomeMap'
import type { ScenarioLookingGlass, StageScenario, StoryboardStage } from '../data/storyboard'
import type { ClientId, ServerVariantId } from '../types/testCases'
import { useWebSocket } from '../hooks/useWebSocket'
import type { EventRecord } from '../hooks/useWebSocket'

type RunStatus = 'idle' | 'running' | 'passed' | 'blocked' | 'breached' | 'error'

const statusCopy: Record<RunStatus, string> = {
  idle: 'Idle',
  running: 'Running…',
  passed: 'Outcome: passed',
  blocked: 'Outcome: blocked',
  breached: 'Outcome: breached',
  error: 'Error'
}

const statusStyle: Record<RunStatus, string> = {
  idle: 'bg-slate-800 text-slate-200',
  running: 'bg-blue-900 text-blue-200',
  passed: 'bg-emerald-900 text-emerald-200',
  blocked: 'bg-amber-900 text-amber-200',
  breached: 'bg-rose-900 text-rose-200',
  error: 'bg-red-900 text-red-200'
}

const scenarioOutcomeMeta: Partial<Record<RunStatus, { label: string; className: string }>> = {
  passed: { label: 'PASSED', className: 'text-emerald-300' },
  blocked: { label: 'BLOCKED', className: 'text-amber-300' },
  breached: { label: 'BREACHED', className: 'text-rose-400' }
}

const ARTICLE_LABEL: Record<string, string> = {
  factset: 'FactSet — Enterprise MCP',
  cyberark: 'CyberArk — MCP Threat Analysis',
  windows: 'Microsoft — Securing MCP on Windows'
}

interface TailTab {
  sessionId: string
  scenarioId: string
  clientId: ClientId
  serverVariantId: ServerVariantId
  label: string
  createdAt: string
  events: EventRecord[]
  status: RunStatus
  live: boolean
  stale: boolean
}

interface CodeDiffPayload {
  file: string
  baseline: string
  variant: string
  diff: string
  annotations: { symbol: string; summary: string; start_line: number; end_line: number }[]
}

interface Props {
  stage: StoryboardStage
}

function formatEvents(events: EventRecord[]) {
  return events
    .map((evt) => {
      const time = new Date(evt.timestamp).toLocaleTimeString()
      const level = evt.level.toUpperCase().padEnd(5, ' ')
      const meta = evt.metadata ? JSON.stringify(evt.metadata) : ''
      return `[${time}] [${level}] ${evt.message}${meta ? ` ${meta}` : ''}`
    })
    .join('\n')
}

export function StoryboardStageCard({ stage }: Props) {
  const defaultVariant = stage.serverVariants[0]?.id as ServerVariantId | undefined
  const [selectedVariantId, setSelectedVariantId] = useState<ServerVariantId>(defaultVariant ?? 'covert-slice')
  const selectedVariant = stage.serverVariants.find((variant) => variant.id === selectedVariantId) ?? stage.serverVariants[0]

  const [sessionId, setSessionId] = useState<string>()
  const [activeScenarioId, setActiveScenarioId] = useState<string>()
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const { events, connected } = useWebSocket(sessionId)
  const [tailTabs, setTailTabs] = useState<TailTab[]>([])
  const [activeTailId, setActiveTailId] = useState<string>()

  const [diffCache, setDiffCache] = useState<Record<string, CodeDiffPayload>>({})
  const [activeDiffKey, setActiveDiffKey] = useState<string>()
  const [diffLoading, setDiffLoading] = useState(false)
  const [diffError, setDiffError] = useState<string>()

  const activeTail = tailTabs.find((tab) => tab.sessionId === activeTailId)
  const tailText = useMemo(() => (activeTail ? formatEvents(activeTail.events) : ''), [activeTail])

  useEffect(() => {
    if (!sessionId) return
    setTailTabs((tabs) =>
      tabs.map((tab) =>
        tab.sessionId === sessionId
          ? {
              ...tab,
              events,
              live: true
            }
          : tab
      )
    )
  }, [events, sessionId])

  useEffect(() => {
    if (!sessionId || events.length === 0) return
    const last = events[events.length - 1]
    if (last.phase === 'case_end') {
      const outcome = statusFromOutcome(last.metadata?.['outcome'])
      if (outcome) {
        setRunStatus(outcome)
        setTailTabs((tabs) =>
          tabs.map((tab) =>
            tab.sessionId === sessionId
              ? {
                  ...tab,
                  status: outcome,
                  live: false,
                  events: [...events]
                }
              : tab
          )
        )
      }
      setIsStarting(false)
    }
  }, [events, sessionId])

  useEffect(() => {
    if (!activeTailId && tailTabs.length > 0) {
      setActiveTailId(tailTabs[0].sessionId)
    }
  }, [tailTabs, activeTailId])

  function markTabsForVariant(variantId: ServerVariantId) {
    setTailTabs((tabs) =>
      tabs.map((tab) => ({
        ...tab,
        stale: tab.serverVariantId !== variantId
      }))
    )
  }

  async function resetBackendState(reason: string, context: { scenarioId?: string; clientId?: ClientId; serverVariantId?: ServerVariantId }) {
    try {
      await fetch('/api/reset-state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stage_id: stage.id,
          scenario_id: context.scenarioId,
          client_id: context.clientId,
          server_variant_id: context.serverVariantId,
          reason
        })
      })
    } catch (err) {
      console.warn('Failed to reset backend state', err)
    }
  }

  async function handleRun(scenario: StageScenario) {
    if (!selectedVariant) return
    if (activeScenarioId && activeScenarioId !== scenario.id) {
      await resetBackendState('scenario-switch', {
        scenarioId: scenario.id,
        clientId: scenario.clientId,
        serverVariantId: selectedVariant.id
      })
    }
    setIsStarting(true)
    setError(undefined)
    setRunStatus('running')
    setActiveScenarioId(scenario.id)
    setSessionId(undefined)
    try {
      const response = await fetch('/api/run-case', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stage_id: stage.id,
          scenario_id: scenario.id,
          scenario_label: scenario.label,
          client_id: scenario.clientId,
          server_variant_id: selectedVariant.id
        })
      })
      if (!response.ok) {
        throw new Error(`Failed to start scenario: ${response.status}`)
      }
      const data = (await response.json()) as { session_id: string }
      const newTab: TailTab = {
        sessionId: data.session_id,
        scenarioId: scenario.id,
        clientId: scenario.clientId,
        serverVariantId: selectedVariant.id,
        label: `${scenario.label} • ${selectedVariant.label}`,
        createdAt: new Date().toISOString(),
        events: [],
        status: 'running',
        live: true,
        stale: false
      }
      setTailTabs((tabs) => [newTab, ...tabs])
      setActiveTailId(newTab.sessionId)
      setSessionId(data.session_id)
    } catch (err) {
      console.error(err)
      setRunStatus('error')
      setError('Unable to start scenario. Is the backend running?')
      setIsStarting(false)
    }
  }

  async function handleVariantChange(variantId: ServerVariantId) {
    await resetBackendState('variant-switch', { serverVariantId: variantId })
    setSelectedVariantId(variantId)
    setRunStatus('idle')
    setActiveScenarioId(undefined)
    setSessionId(undefined)
    setIsStarting(false)
    setError(undefined)
    markTabsForVariant(variantId)
  }

  function handleCopyTail() {
    if (!activeTail) return
    navigator.clipboard?.writeText(tailText).catch(() => {
      // eslint-disable-next-line no-alert
      alert('Unable to copy to clipboard in this browser.')
    })
  }

  function handleCloseTab(session: string) {
    setTailTabs((tabs) => tabs.filter((tab) => tab.sessionId !== session))
    if (activeTailId === session) {
      setActiveTailId(undefined)
    }
  }

  function openLookingGlass(target: ScenarioLookingGlass) {
    const key = `${target.file}:${target.baseline}->${target.variant}`
    setActiveDiffKey(key)
    setDiffError(undefined)
    const cached = diffCache[key]
    if (cached) {
      return
    }
    setDiffLoading(true)
    fetch(
      `/api/code-diff?file=${encodeURIComponent(target.file)}&baseline=${encodeURIComponent(target.baseline)}&variant=${encodeURIComponent(target.variant)}`
    )
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Unable to load diff (${res.status})`)
        }
        return (await res.json()) as CodeDiffPayload
      })
      .then((payload) => {
        setDiffCache((prev) => ({ ...prev, [key]: payload }))
      })
      .catch((err) => {
        setDiffError(err instanceof Error ? err.message : 'Unable to load diff')
      })
      .finally(() => setDiffLoading(false))
  }

  const activeDiff = activeDiffKey ? diffCache[activeDiffKey] : undefined

  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-950/60 p-6 shadow-lg shadow-black/40">
      <div className="space-y-5">
        <header className="space-y-2">
          <div className="text-sm uppercase tracking-widest text-slate-500">Stage</div>
          <h2 className="text-2xl font-semibold text-slate-50">{stage.title}</h2>
          <p className="text-slate-300">{stage.blurb}</p>
          <div className="flex flex-wrap gap-2 text-xs text-slate-400">
            {stage.articles.map((article) => (
              <span key={article} className="rounded-full border border-slate-700 px-3 py-1">
                {ARTICLE_LABEL[article] ?? article}
              </span>
            ))}
          </div>
        </header>

        <ul className="list-disc space-y-1 pl-5 text-slate-200">
          {stage.examples.map((example) => (
            <li key={example}>{example}</li>
          ))}
        </ul>

        <section className="space-y-3">
          <div className="flex items-center justify-between text-sm font-semibold uppercase tracking-wide text-slate-400">
            <span>Server mutations</span>
            <span className="text-xs text-slate-500">Feeds apply per stage</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {stage.serverVariants.map((variant) => (
              <button
                key={variant.id}
                onClick={() => handleVariantChange(variant.id)}
                className={`rounded-full border px-4 py-2 text-sm transition ${
                  variant.id === selectedVariantId
                    ? 'border-emerald-400 bg-emerald-400/10 text-emerald-200'
                    : 'border-slate-700 text-slate-300 hover:border-emerald-400 hover:text-emerald-200'
                }`}
              >
                <div className="font-semibold">{variant.label}</div>
                <div className="text-xs text-slate-400">{variant.description}</div>
              </button>
            ))}
          </div>
        </section>

        <section className="space-y-2">
          <div className="text-sm font-semibold uppercase tracking-wide text-slate-400">Scenarios</div>
          <div className="grid gap-3 md:grid-cols-2">
            {stage.scenarios.map((scenario) => (
              <button
                key={scenario.id}
                onClick={() => handleRun(scenario)}
                className="rounded-xl border border-slate-700 bg-gradient-to-br from-slate-900 to-slate-800 px-4 py-3 text-left text-sm transition hover:border-emerald-500 hover:text-emerald-200"
                disabled={isStarting && activeScenarioId === scenario.id}
              >
                <div className="font-semibold text-slate-100">{scenario.label}</div>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-slate-400">
                  <span className="flex-1">{scenario.description}</span>
                  {activeScenarioId === scenario.id && scenarioOutcomeMeta[runStatus] && (
                    <span className={`text-xs font-semibold uppercase tracking-wide ${scenarioOutcomeMeta[runStatus]?.className}`}>
                      {scenarioOutcomeMeta[runStatus]?.label}
                    </span>
                  )}
                </div>
                {activeScenarioId === scenario.id && <div className="mt-2 text-xs text-emerald-300">Active</div>}
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-slate-800 bg-black/30 p-4 text-sm text-slate-200">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs uppercase tracking-wide text-slate-400">
            <span>Pinned tails</span>
            <span>
              Status:{' '}
              <span className={`rounded-full px-2 py-1 font-semibold ${statusStyle[runStatus]}`}>{statusCopy[runStatus]}</span>
              <span className="ml-2 text-slate-500">{connected ? 'Live' : 'Idle'}</span>
            </span>
          </div>
          {tailTabs.length === 0 ? (
            <p className="mt-3 text-slate-400">Run a scenario to capture and pin its log tail.</p>
          ) : (
            <>
              <div className="mt-3 flex flex-wrap gap-2">
                {tailTabs.map((tab) => (
                  <div
                    key={tab.sessionId}
                    className={`flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${
                      tab.sessionId === activeTailId ? 'border-emerald-400 text-emerald-200' : 'border-slate-700 text-slate-400'
                    } ${tab.stale ? 'opacity-60' : ''}`}
                  >
                    <button
                      className="flex flex-col text-left"
                      onClick={() => setActiveTailId(tab.sessionId)}
                      type="button"
                    >
                      <span className="font-semibold">{tab.label}</span>
                      <span className="text-[10px] uppercase tracking-widest">
                        {tab.status} {tab.stale && '• stale'}
                      </span>
                    </button>
                    <button
                      className="text-slate-500 hover:text-red-300"
                      onClick={() => handleCloseTab(tab.sessionId)}
                      type="button"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
              {activeTail && (
                <div className="mt-4 space-y-2">
                  <textarea
                    readOnly
                    value={tailText}
                    className="h-64 w-full resize-none rounded-xl border border-slate-800 bg-slate-950/80 p-3 font-mono text-xs text-slate-200"
                  />
                  <div className="flex flex-wrap items-center justify-between text-xs text-slate-400">
                    <div>
                      Session {activeTail.sessionId.slice(0, 8)} • Variant {activeTail.serverVariantId}{' '}
                      {activeTail.stale && '• pinned before variant change'}
                    </div>
                    <div className="flex gap-2">
                      <button className="rounded border border-emerald-400/60 px-3 py-1 text-emerald-200" onClick={handleCopyTail} type="button">
                        Copy feed
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          {error && <div className="mt-3 rounded-xl border border-red-500/30 bg-red-900/20 p-3 text-sm text-red-200">{error}</div>}
        </section>

        {stage.lookingGlassRefs.length > 0 && (
          <section className="space-y-3">
            <div className="text-sm font-semibold uppercase tracking-wide text-slate-400">Looking glass</div>
            {stage.lookingGlassRefs.map((ref) => (
              <div key={ref.id} className="rounded-xl border border-slate-800 bg-black/30 p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold text-slate-100">{ref.label}</div>
                    <div className="text-xs text-slate-400">{ref.summary}</div>
                    <div className="mt-1 font-mono text-[11px] text-emerald-300">{ref.file}</div>
                  </div>
                  <button
                    className="rounded border border-emerald-400/60 px-3 py-1 text-xs uppercase tracking-widest text-emerald-200"
                    type="button"
                    onClick={() => openLookingGlass(ref)}
                  >
                    View diff
                  </button>
                </div>
              </div>
            ))}
            {(diffLoading || activeDiff || diffError) && (
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-200">
                {diffLoading && <p>Loading diff…</p>}
                {diffError && <p className="text-rose-300">{diffError}</p>}
                {activeDiff && !diffLoading && !diffError && (
                  <div className="space-y-3">
                    <div className="text-xs uppercase tracking-widest text-slate-400">
                      {activeDiff.baseline} → {activeDiff.variant}
                    </div>
                    <pre className="max-h-80 overflow-auto rounded-xl border border-slate-800 bg-black/60 p-3 text-xs text-emerald-200">
                      {activeDiff.diff}
                    </pre>
                    <div>
                      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Annotated nodes</div>
                      <ul className="mt-2 space-y-1 text-xs text-slate-300">
                        {activeDiff.annotations.slice(0, 5).map((ann) => (
                          <li key={`${ann.symbol}-${ann.start_line}`} className="rounded border border-slate-800/60 px-2 py-1">
                            <div className="font-mono text-emerald-200">{ann.symbol}</div>
                            <div className="text-slate-400">
                              Lines {ann.start_line}–{ann.end_line}
                            </div>
                            {ann.summary && <div className="text-slate-500">{ann.summary}</div>}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </div>
    </article>
  )
}

