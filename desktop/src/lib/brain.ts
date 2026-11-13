import * as reeta from './reetaAdapter'
import type { AskHandlers, Msg } from './anthropic'
import type { Blade, Panel } from '../store'

export type { AskHandlers, Msg }
export type { ConnectionState } from './reetaAdapter'

export const usingBridge = true

/**
 * REETA Assistant Brain.
 * Routes questions, tasks, and voice instructions directly to REETA's FastAPI
 * backend, LangGraph orchestrator, Google Gemini reasoning, and 32 autonomous tools.
 */
export async function ask(
  prompt: string,
  _history: Msg[],
  handlers: AskHandlers,
): Promise<{ text: string; tools: string[] }> {
  return reeta.ask(prompt, handlers)
}

export async function warm(): Promise<void> {
  await reeta.warmBridge()
}

export function watchServers(fn: (servers: string[]) => void): void {
  reeta.watchServers(fn)
}

export function watchPanels(fn: (panel: Panel) => void): void {
  reeta.watchPanels(fn)
}

export function watchBlades(fn: (blade: Blade) => void): void {
  reeta.watchBlades(fn)
}

export function watchUi(fn: (op: string, args: any) => void): void {
  reeta.watchUi(fn)
}

export function watchCapture(fn: any): void {
  reeta.watchCapture(fn)
}

export function cancel(): void {
  reeta.cancel()
}

export function interrupt(): void {
  cancel()
}

export function isConnected(): boolean {
  return reeta.isConnected()
}

export function watchConnection(fn: (state: reeta.ConnectionState) => void): void {
  reeta.watchConnection(fn)
}

export function connectedLabels(): string[] {
  return reeta.bridgeServers()
}
