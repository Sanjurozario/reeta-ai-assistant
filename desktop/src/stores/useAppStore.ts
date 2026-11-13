import { create } from 'zustand';
import { ScreenType, SystemHealth, TaskItem, ApprovalTicket, MemoryItem } from '../types';
import * as api from '../services/api';
import { getApiBase, getWsUrl, initBackendConfig } from '../services/config';

interface AppState {
  activeScreen: ScreenType;
  setActiveScreen: (screen: ScreenType) => void;

  health: SystemHealth | null;
  isMockMode: boolean;
  wsConnected: boolean;
  isListening: boolean;
  isSpeaking: boolean;
  audioLevel: number;
  partialTranscript: string;
  activeTask: TaskItem | null;
  tasks: TaskItem[];
  pendingApprovals: ApprovalTicket[];
  memories: MemoryItem[];
  logs: string[];
  ws: WebSocket | null;

  init: () => Promise<void>;
  connectWebSocket: () => void;
  sendUserMessage: (text: string) => void;
  triggerEmergencyStop: () => Promise<void>;
  createTaskAndExecute: (title: string, objective: string) => Promise<void>;
  refreshTasks: () => Promise<void>;
  refreshApprovals: () => Promise<void>;
  refreshMemories: () => Promise<void>;
  createMemory: (content: string, type?: string, category?: string) => Promise<void>;
  deleteMemory: (id: string) => Promise<void>;
  forgetMemory: (query: string) => Promise<void>;
  approveTicket: (ticketId: string) => Promise<void>;
  rejectTicket: (ticketId: string) => Promise<void>;
  toggleVoiceListening: () => void;
  speak: (text: string) => void;
  stopSpeaking: () => void;
}

let speechRecInstance: any = null;

export const useAppStore = create<AppState>((set, get) => ({
  activeScreen: 'command',
  setActiveScreen: (screen) => set({ activeScreen: screen }),

  health: null,
  isMockMode: true,
  wsConnected: false,
  isListening: false,
  isSpeaking: false,
  audioLevel: 0,
  partialTranscript: '',
  activeTask: null,
  tasks: [],
  pendingApprovals: [],
  memories: [],
  logs: ['[System] REETA Holographic Interface initialized.'],
  ws: null,

  init: async () => {
    await initBackendConfig();
    try {
      const health = await api.fetchHealth();
      const isMock = health?.active_provider === 'mock' || !health?.active_provider;
      set({ health, isMockMode: isMock });
    } catch (e) {
      console.warn('Backend not responding yet:', e);
    }
    get().connectWebSocket();
    await get().refreshTasks();
    await get().refreshApprovals();
    await get().refreshMemories();
  },

  connectWebSocket: () => {
    try {
      const socket = new WebSocket(getWsUrl());

      socket.onopen = () => {
        set({ wsConnected: true, ws: socket });
        set((s) => ({ logs: [...s.logs, '[WebSocket] Real-time event bus connected.'] }));
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const eventType = data.event;
          const payload = data.payload || {};

          if (eventType === 'step_started') {
            set((s) => ({
              logs: [...s.logs, `[Agent:${payload.agent}] Step ${payload.step_number}: ${payload.title}`],
            }));
            get().refreshTasks();
          } else if (eventType === 'step_verified') {
            set((s) => ({
              logs: [...s.logs, `[Verification] Step ${payload.step_number} passed: ${payload.passed} | Evidence: ${payload.evidence}`],
            }));
            get().refreshTasks();
          } else if (eventType === 'step_updated' || eventType === 'plan_generated') {
            get().refreshTasks();
          } else if (eventType === 'approval_required' || eventType === 'task_waiting_approval') {
            set((s) => ({
              logs: [...s.logs, `[Security] Approval demanded for ticket: ${payload.ticket_id || 'Action Escalated'}`],
            }));
            get().speak('Security check required. A consequential action demands your explicit authorization.');
            get().refreshApprovals();
            get().refreshTasks();
          } else if (eventType === 'task_completed') {
            set((s) => ({
              logs: [...s.logs, `[Task] Task completed successfully!`],
            }));
            get().speak('Task successfully verified and completed.');
            get().refreshTasks();
          } else if (eventType === 'task_failed') {
            const errStr = payload?.error?.error || payload?.error?.unhandled_exception || 'Execution interrupted';
            set((s) => ({
              logs: [...s.logs, `[Task] Task failed: ${errStr}`],
            }));
            get().speak('Task execution failed verification.');
            get().refreshTasks();
          } else if (eventType === 'agent_message') {
            const content = payload.content || '';
            if (content) {
              get().speak(content);
            }
          } else if (eventType === 'audio_level') {
            if (payload.level !== undefined) {
              set({ audioLevel: payload.level });
            }
          } else if (eventType === 'wake_word_detected') {
            set((s) => ({
              logs: [...s.logs, `[Wake-Word] "Hey REETA" detected: "${payload.command || payload.raw_text}"`],
            }));
            try {
              import('@tauri-apps/api/window').then(({ getCurrentWindow }) => {
                const win = getCurrentWindow();
                win.show();
                win.setFocus();
              });
            } catch (_) {}
            const cmd = payload.command;
            if (cmd && cmd.trim().length > 3) {
              get().createTaskAndExecute(cmd.slice(0, 30), cmd);
            }
          } else if (eventType === 'speech_transcribed') {
            if (payload.text) {
              set((s) => ({
                logs: [...s.logs, `[Voice] Transcribed: "${payload.text}"`],
              }));
            }
          }
        } catch (err) {
          console.error('Error parsing WS message:', err);
        }
      };

      socket.onclose = () => {
        set({ wsConnected: false, ws: null });
        setTimeout(() => get().connectWebSocket(), 3000);
      };
    } catch (e) {
      console.error('WebSocket connection error:', e);
    }
  },

  sendUserMessage: (text: string) => {
    const { ws, logs } = get();
    get().stopSpeaking();
    set({ logs: [...logs, `[User] ${text}`] });
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ event: 'user_message', payload: { text } }));
    }
  },

  triggerEmergencyStop: async () => {
    get().stopSpeaking();
    try {
      await api.postEmergencyStop();
      set((s) => ({ logs: [...s.logs, '[Security] EMERGENCY STOP invoked. Terminated all active workers.'] }));
      get().speak('Emergency stop triggered. All active operations terminated.');
      await get().refreshTasks();
    } catch (e) {
      console.error('Emergency stop error:', e);
    }
  },

  createTaskAndExecute: async (title: string, objective: string) => {
    get().stopSpeaking();
    try {
      const task = await api.createTask(title, objective);
      set({ activeTask: task, activeScreen: 'operations' });
      set((s) => ({
        tasks: [task, ...s.tasks],
        logs: [...s.logs, `[Task Created] ID: ${task.id.slice(0, 8)} | "${title}"`],
      }));
      setTimeout(() => {
        get().refreshTasks();
      }, 350);
    } catch (e) {
      console.error('Task creation failed:', e);
    }
  },

  refreshTasks: async () => {
    try {
      const tasks: TaskItem[] = await api.fetchTasks(20);
      const currentActive = get().activeTask;
      let nextActive = currentActive;
      if (currentActive) {
        const found = tasks.find((t: TaskItem) => t.id === currentActive.id);
        if (found) {
          nextActive = found;
        }
      } else if (tasks.length > 0) {
        nextActive = tasks[0];
      }
      set({ tasks, activeTask: nextActive });
    } catch (e) {
      console.warn('Failed to refresh tasks:', e);
    }
  },

  refreshApprovals: async () => {
    try {
      const pendingApprovals = await api.fetchPendingApprovals();
      set({ pendingApprovals });
    } catch (e) {
      console.warn('Failed to refresh approvals:', e);
    }
  },

  refreshMemories: async () => {
    try {
      const memories = await api.fetchMemories(50);
      set({ memories });
    } catch (e) {
      console.warn('Failed to refresh memories:', e);
    }
  },

  createMemory: async (content: string, type = 'preference', category = 'general') => {
    try {
      await api.createMemory(content, type, category);
      await get().refreshMemories();
      set((s) => ({ logs: [...s.logs, `[Memory Stored] "${content.slice(0, 35)}..."`] }));
    } catch (e) {
      console.error('Create memory failed:', e);
    }
  },

  deleteMemory: async (id: string) => {
    try {
      await api.deleteMemory(id);
      await get().refreshMemories();
      set((s) => ({ logs: [...s.logs, `[Memory Deleted] ID ${id.slice(0, 8)} removed.`] }));
    } catch (e) {
      console.error('Delete memory failed:', e);
    }
  },

  forgetMemory: async (query: string) => {
    try {
      const res = await api.forgetMemory(query);
      await get().refreshMemories();
      set((s) => ({ logs: [...s.logs, `[Cognitive Forget] Removed ${res.deleted_count} memories matching '${query}'.`] }));
    } catch (e) {
      console.error('Forget memory failed:', e);
    }
  },

  approveTicket: async (ticketId: string) => {
    try {
      await api.respondToApproval(ticketId, 'approve');
      set((s) => ({ logs: [...s.logs, `[Approval] Approved ticket ${ticketId}`] }));
      await get().refreshApprovals();
    } catch (e) {
      console.error('Approval failed:', e);
    }
  },

  rejectTicket: async (ticketId: string) => {
    try {
      await api.respondToApproval(ticketId, 'reject');
      set((s) => ({ logs: [...s.logs, `[Approval] Rejected ticket ${ticketId}`] }));
      await get().refreshApprovals();
    } catch (e) {
      console.error('Rejection failed:', e);
    }
  },

  speak: (text: string) => {
    const cleanText = text
      .replace(/\[REETA[^\]]*\]/g, '')
      .replace(/https?:\/\/[^\s]+/g, 'link')
      .replace(/[*_#`]/g, '')
      .slice(0, 250);
    if (!cleanText.trim()) return;

    if (typeof window !== 'undefined' && 'speechSynthesis' in window && window.speechSynthesis.speak) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.onstart = () => set({ isSpeaking: true });
      utterance.onend = () => set({ isSpeaking: false });
      utterance.onerror = () => {
        set({ isSpeaking: false });
        fetch(`${getApiBase()}/voice/speak`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: cleanText }),
        }).catch(() => {});
      };
      window.speechSynthesis.speak(utterance);
    } else {
      fetch(`${getApiBase()}/voice/speak`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cleanText }),
      }).catch(() => {});
    }
  },

  stopSpeaking: () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    fetch(`${getApiBase()}/voice/interrupt`, { method: 'POST' }).catch(() => {});
    set({ isSpeaking: false });
  },

  toggleVoiceListening: () => {
    const isCurrentlyListening = get().isListening;

    if (isCurrentlyListening) {
      if (speechRecInstance) {
        try { speechRecInstance.stop(); } catch (_) {}
      }
      set({ isListening: false, partialTranscript: '' });
      set((s) => ({ logs: [...s.logs, '[Voice] Microphone standby.'] }));
      return;
    }

    // Activate Web Speech API
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) {
      // Browser SpeechRecognition not available in environment
      set({ isListening: true });
      set((s) => ({ logs: [...s.logs, '[Voice] Listening simulation mode active. Speak or type instructions.'] }));
      return;
    }

    try {
      speechRecInstance = new SpeechRec();
      speechRecInstance.continuous = true;
      speechRecInstance.interimResults = true;
      speechRecInstance.lang = 'en-US';

      speechRecInstance.onspeechstart = () => {
        // Voice Barge-in interruption
        get().stopSpeaking();
      };

      speechRecInstance.onresult = (event: any) => {
        let interim = '';
        let final = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }

        const currentText = (final || interim).trim();
        set({ partialTranscript: currentText });

        if (final && final.trim().length > 3) {
          const prompt = final.trim();
          set((s) => ({ logs: [...s.logs, `[Voice Input] "${prompt}"`] }));
          set({ partialTranscript: '' });

          // Auto-trigger command if wake word or direct instruction given
          const cleanPrompt = prompt.replace(/^hey\s+reeta,?\s*/i, '').trim();
          get().createTaskAndExecute(cleanPrompt.slice(0, 30), prompt);
        }
      };

      speechRecInstance.onerror = (e: any) => {
        console.warn('SpeechRecognition error:', e);
        set({ isListening: false, partialTranscript: '' });
      };

      speechRecInstance.onend = () => {
        set({ isListening: false, partialTranscript: '' });
      };

      speechRecInstance.start();
      set({ isListening: true });
      get().stopSpeaking();
      set((s) => ({ logs: [...s.logs, '[Voice] Neural audio listener active ("Hey REETA")...'] }));
    } catch (err) {
      console.warn('Could not start SpeechRecognition:', err);
      set({ isListening: true });
    }
  },
}));
