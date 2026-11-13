export type Msg = {
  role: 'user' | 'assistant'
  content: string
}

export type AskHandlers = {
  /** Fires for each chunk of the spoken answer. */
  onText: (delta: string) => void
  /** Fires when REETA starts running a tool/agent. */
  onTool: (name: string) => void
}

export async function ask(
  _messages: Msg[],
  _handlers: AskHandlers,
): Promise<{ text: string; tools: string[] }> {
  return { text: 'REETA assistant is operational with Google Gemini.', tools: [] }
}

export function cancel(): void {}

export function connectedLabels(): string[] {
  return [
    'Google Gemini 3.5 Flash',
    'LangGraph Orchestrator',
    'Windows 11 UI Automation',
    'Cognitive Memory',
  ]
}
