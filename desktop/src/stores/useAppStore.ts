import { create } from 'zustand';
import { ScreenType, SystemHealth, TaskItem, ApprovalTicket, AuditLogItem } from '../types';
import * as api from '../services/api';

interface AppState {
  activeScreen: ScreenType;
  setActiveScreen: (screen: ScreenType) => void;

  health: SystemHealth | null;
  wsConnected: boolean;
  isListening: boolean;
  activeTask: TaskItem | null;
  tasks: TaskItem[];
  pendingApprovals: ApprovalTicket[];
  logs: string[];
  ws: WebSocket | null;

  init: () => Promise<void>;
  connectWebSocket: () => void;
  sendUserMessage: (text: string) => void;
  triggerEmergencyStop: () => Promise<void>;
  createTaskAndExecute: (title: string, objective: string) => Promise<void>;
  refreshTasks: () => Promise<void>;
  refreshApprovals: () => Promise<void>;
  approveTicket: (ticketId: string) => Promise<void>;
  rejectTicket: (ticketId: string) => Promise<void>;
  toggleVoiceListening: () => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  activeScreen: 'command',
  setActiveScreen: (screen) => set({ activeScreen: screen }),

  health: null,
  wsConnected: false,
  isListening: false,
  activeTask: null,
  tasks: [],
  pendingApprovals: [],
  logs: ['[System] REETA Desktop Interface initialized.'],
  ws: null,

  init: async () => {
    try {
      const health = await api.fetchHealth();
      set({ health });
    } catch (e) {
      console.warn('Backend not responding yet:', e);
    }
    get().connectWebSocket();
    await get().refreshTasks();
    await get().refreshApprovals();
  },

  connectWebSocket: () => {
    try {
      const socket = new WebSocket('ws://127.0.0.1:8765/ws/v1/stream');

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
          } else if (eventType === 'step_verified') {
            set((s) => ({
              logs: [...s.logs, `[Verification] Step ${payload.step_number} passed: ${payload.passed} | Evidence: ${payload.evidence}`],
            }));
            get().refreshTasks();
          } else if (eventType === 'approval_required') {
            set((s) => ({
              logs: [...s.logs, `[Security] Approval demanded for ticket: ${payload.ticket_id}`],
            }));
            get().refreshApprovals();
          } else if (eventType === 'task_completed') {
            set((s) => ({
              logs: [...s.logs, `[Task] Task completed successfully!`],
            }));
            get().refreshTasks();
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
    set({ logs: [...logs, `[User] ${text}`] });
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ event: 'user_message', payload: { text } }));
    }
  },

  triggerEmergencyStop: async () => {
    try {
      await api.postEmergencyStop();
      set((s) => ({ logs: [...s.logs, '[Security] EMERGENCY STOP invoked. Terminated all active workers.'] }));
      await get().refreshTasks();
    } catch (e) {
      console.error('Emergency stop error:', e);
    }
  },

  createTaskAndExecute: async (title: string, objective: string) => {
    try {
      const task = await api.createTask(title, objective);
      set({ activeTask: task, activeScreen: 'operations' });
      set((s) => ({
        tasks: [task, ...s.tasks],
        logs: [...s.logs, `[Task Created] ID: ${task.id.slice(0, 8)} | "${title}"`],
      }));
    } catch (e) {
      console.error('Task creation failed:', e);
    }
  },

  refreshTasks: async () => {
    try {
      const tasks = await api.fetchTasks(20);
      set({ tasks });
      if (tasks.length > 0 && !get().activeTask) {
        set({ activeTask: tasks[0] });
      }
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

  toggleVoiceListening: () => {
    const now = !get().isListening;
    set({ isListening: now });
    set((s) => ({
      logs: [...s.logs, now ? '[Voice] Listening activated ("Hey Reeta")...' : '[Voice] Microphone muted.'],
    }));
  },
}));
