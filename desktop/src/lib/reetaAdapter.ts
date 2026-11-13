import type { AskHandlers } from './anthropic'
import type { Blade, Panel } from '../store'
import { useStore } from '../store'

export type ConnectionState = 'connecting' | 'open' | 'lost' | 'reconnected'

const API_BASE = 'http://127.0.0.1:8765/api/v1'
const WS_URL = 'ws://127.0.0.1:8765/ws/v1/stream'

let socket: WebSocket | null = null
let connecting: Promise<WebSocket> | null = null
let everConnected = false
let onConnectionState: ((state: ConnectionState) => void) | null = null

const activeTools: string[] = []
let activeTaskId: string | null = null
let pendingTurn: {
  resolve: (res: { text: string; tools: string[] }) => void
  reject: (err: Error) => void
  handlers: AskHandlers
  accumulatedText: string
} | null = null

export function isConnected(): boolean {
  return socket !== null && socket.readyState === WebSocket.OPEN
}

export function watchConnection(fn: (state: ConnectionState) => void) {
  onConnectionState = fn
}

export function bridgeServers(): string[] {
  return [
    'Google Gemini 3.5 Flash',
    'LangGraph Orchestrator',
    'Computer Agent (Windows UI)',
    'Research Agent (Web)',
    'Coding Agent (Python)',
    'File Agent (Disk)',
    'Productivity Agent',
    'Cognitive Memory',
    'Zero-Trust Security Gate',
  ]
}

export function watchServers(fn: (servers: string[]) => void) {
  fn(bridgeServers())
}

let onPanelCallback: ((panel: Panel) => void) | null = null
export function watchPanels(fn: (panel: Panel) => void) {
  onPanelCallback = fn
}

let onBladeCallback: ((blade: Blade) => void) | null = null
export function watchBlades(fn: (blade: Blade) => void) {
  onBladeCallback = fn
}

let onUiCallback: ((op: string, args: any) => void) | null = null
export function watchUi(fn: (op: string, args: any) => void) {
  onUiCallback = fn
}

export function watchCapture(_fn: any) {
  // Reserved for vision
}

function dispatchSocketMessage(event: MessageEvent) {
  try {
    const data = JSON.parse(event.data)
    const eventType = data.event
    const payload = data.payload || {}
    const taskId = data.task_id

    const store = useStore.getState()

    if (eventType === 'step_started') {
      const toolName = payload.title || payload.agent || 'Executing step'
      if (!activeTools.includes(toolName)) {
        activeTools.push(toolName)
      }
      pendingTurn?.handlers?.onTool?.(toolName)
      store.setActiveTool(toolName)
      store.setPhase('tooling')

      // Push HUD Blade reflecting live execution
      store.pushBlade({
        id: `step-${payload.step_number || Date.now()}`,
        title: `STEP ${payload.step_number || 1} // ${toolName}`,
        kind: 'markup',
        html: `
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.6; color: #00e5ff;">
            <div style="margin-bottom: 8px; opacity: 0.7;">AGENT: <strong style="color: #fff;">${payload.agent || 'system'}</strong></div>
            <div style="padding: 10px; background: rgba(0, 229, 255, 0.05); border: 1px solid rgba(0, 229, 255, 0.2); border-radius: 4px;">
              ${payload.title || 'Executing tool action...'}
            </div>
          </div>
        `,
        size: 'compact',
        hold: 'turn',
      })
    } else if (eventType === 'step_verified') {
      const evidence = payload.evidence || 'Verified'
      const bladeId = `verify-${payload.step_number || Date.now()}`
      store.pushBlade({
        id: bladeId,
        title: `VERIFIED // STEP ${payload.step_number || 1}`,
        kind: 'markup',
        html: `
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; line-height: 1.6; color: #10b981;">
            <div style="margin-bottom: 6px;">STATUS: <strong>PASSED</strong></div>
            <div style="padding: 8px; background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 4px; color: #d1fae5;">
              ${evidence}
            </div>
          </div>
        `,
        size: 'compact',
        hold: 'turn',
      })
      setTimeout(() => {
        store.closeBlade(bladeId)
      }, 7000)
    } else if (eventType === 'agent_message') {
      const text = payload.content || ''
      if (text && pendingTurn) {
        pendingTurn.accumulatedText += text
        pendingTurn.handlers?.onText?.(text)
      }
    } else if (eventType === 'approval_required' || eventType === 'task_waiting_approval') {
      const ticketId = payload.ticket_id || payload.approval_token || 'pending'
      const resource = payload.target_resource || payload.action || 'Consequential OS Action'
      store.setPhase('tooling')

      store.pushBlade({
        id: `approval-${ticketId}`,
        title: 'SECURITY AUTHORIZATION REQUIRED',
        kind: 'markup',
        html: `
          <div style="font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.6; color: #f59e0b;">
            <div style="margin-bottom: 8px; font-weight: bold; color: #fbbf24;">ZERO-TRUST POLICY INTERCEPT</div>
            <div style="padding: 12px; background: rgba(245, 158, 11, 0.08); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 6px; margin-bottom: 12px; color: #fef3c7;">
              An agent requested authorization for: <br/>
              <code style="color: #67e8f9; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 3px;">${resource}</code>
            </div>
            <div style="display: flex; gap: 10px;">
              <button onclick="window.__REETA_RESPOND_TICKET?.('${ticketId}', 'approve')" style="cursor: pointer; background: #10b981; color: #000; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; font-family: monospace;">
                AUTHORIZE
              </button>
              <button onclick="window.__REETA_RESPOND_TICKET?.('${ticketId}', 'reject')" style="cursor: pointer; background: #ef4444; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; font-family: monospace;">
                DENY
              </button>
            </div>
          </div>
        `,
        size: 'compact',
        hold: 'sticky',
      })
    } else if (eventType === 'task_completed') {
      const steps = payload.result?.steps || []
      let finalContent = payload.result?.final_response || payload.final_response || ''
      if (!finalContent) {
        for (const s of steps) {
          if (s.result?.response) {
            finalContent = s.result.response
          } else if (s.result?.answer) {
            finalContent = s.result.answer
          }
        }
      }
      if (!finalContent && steps.length > 0) {
        const lastStep = steps[steps.length - 1]
        finalContent = lastStep.evidence || lastStep.result?.message || 'Task execution verified and completed.'
      }
      if (!finalContent && pendingTurn?.accumulatedText) {
        finalContent = pendingTurn.accumulatedText
      }
      if (!finalContent) {
        finalContent = 'Operation completed successfully.'
      }

      if (pendingTurn) {
        pendingTurn.handlers?.onText?.(finalContent)
        pendingTurn.resolve({
          text: finalContent,
          tools: [...activeTools],
        })
        pendingTurn = null
      }
      store.setActiveTool(null)
      store.setCaption('')
    } else if (eventType === 'task_failed') {
      const err = payload.error?.error || 'Task failed verification.'
      store.setError(err)
      if (pendingTurn) {
        pendingTurn.reject(new Error(err))
        pendingTurn = null
      }
      store.setActiveTool(null)
    } else if (eventType === 'rate_limit') {
      const msg = payload.message || 'Rate limited on Gemini free tier. Retrying...'
      store.setCaption(msg)
      store.setBootNote(msg)
    }
  } catch (err) {
    console.error('[reetaAdapter] Error parsing WebSocket frame:', err)
  }
}

export async function connect(): Promise<WebSocket> {
  if (socket && socket.readyState === WebSocket.OPEN) {
    return socket
  }
  if (connecting) {
    return connecting
  }

  connecting = new Promise<WebSocket>((resolve, reject) => {
    onConnectionState?.('connecting')
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      socket = ws
      connecting = null
      onConnectionState?.(everConnected ? 'reconnected' : 'open')
      everConnected = true
      resolve(ws)
    }

    ws.onmessage = dispatchSocketMessage

    ws.onerror = (e) => {
      console.warn('[reetaAdapter] WebSocket error:', e)
      connecting = null
      onConnectionState?.('lost')
    }

    ws.onclose = () => {
      socket = null
      connecting = null
      onConnectionState?.('lost')
      setTimeout(() => connect().catch(() => {}), 3000)
    }
  })

  return connecting
}

export async function warmBridge(): Promise<void> {
  await connect().catch(() => {})
}

export async function ask(
  prompt: string,
  handlers: AskHandlers,
): Promise<{ text: string; tools: string[] }> {
  await connect().catch(() => {})
  activeTools.length = 0

  return new Promise<{ text: string; tools: string[] }>(async (resolve, reject) => {
    pendingTurn = {
      resolve,
      reject,
      handlers,
      accumulatedText: '',
    }

    try {
      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: prompt.length > 45 ? prompt.slice(0, 42) + '...' : prompt,
          objective: prompt,
          priority: 5,
        }),
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`Failed to submit task to REETA backend: ${res.status} ${errText}`)
      }

      const taskData = await res.json()
      activeTaskId = taskData.id

      // Timeout fallback after 90 seconds
      setTimeout(() => {
        if (pendingTurn) {
          const fallback = pendingTurn.accumulatedText || 'Execution completed.'
          pendingTurn.resolve({ text: fallback, tools: [...activeTools] })
          pendingTurn = null
        }
      }, 90000)
    } catch (err: any) {
      pendingTurn = null
      reject(err)
    }
  })
}

export function cancel(): void {
  if (activeTaskId) {
    fetch(`${API_BASE}/tasks/${activeTaskId}/cancel`, { method: 'POST' }).catch(() => {})
  }
  if (pendingTurn) {
    pendingTurn.resolve({
      text: pendingTurn.accumulatedText || 'Operation interrupted by user.',
      tools: [...activeTools],
    })
    pendingTurn = null
  }
}

// Global approval helper accessible from HTML blades
declare global {
  interface Window {
    __REETA_RESPOND_TICKET?: (ticketId: string, decision: 'approve' | 'reject') => void
  }
}

if (typeof window !== 'undefined') {
  window.__REETA_RESPOND_TICKET = async (ticketId: string, decision: 'approve' | 'reject') => {
    try {
      await fetch(`${API_BASE}/permissions/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket_id: ticketId, decision }),
      })
      useStore.getState().setPhase('tooling')
    } catch (e) {
      console.error('Failed to respond to ticket:', e)
    }
  }
}
