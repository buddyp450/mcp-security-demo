import { useEffect, useMemo, useState } from 'react'

export interface EventRecord {
  session_id: string
  test_case: string
  timestamp: string
  level: 'info' | 'warning' | 'alert' | 'critical'
  phase: string
  message: string
  metadata?: Record<string, unknown>
  stage_id?: string
  scenario_id?: string
  server_variant_id?: string
}

export function useWebSocket(sessionId?: string) {
  const [events, setEvents] = useState<EventRecord[]>([])
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    if (!sessionId) {
      setEvents([])
      setConnected(false)
      return
    }
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/${sessionId}`)
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as EventRecord
        setEvents((prev) => [...prev, payload])
      } catch (err) {
        console.error('Failed to parse event', err)
      }
    }
    return () => {
      ws.close()
    }
  }, [sessionId])

  return useMemo(() => ({ events, connected }), [events, connected])
}
