export type ScreenType =
  | 'command'
  | 'operations'
  | 'workspace'
  | 'computer'
  | 'memory'
  | 'permissions'
  | 'history'
  | 'settings';

export interface SystemHealth {
  status: string;
  version: string;
  database: string;
  active_provider: string;
  uptime_seconds: number;
  timestamp: string;
}

export interface TaskStep {
  id?: string;
  step_number: number;
  title: string;
  agent_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  input_payload?: Record<string, any>;
  output_payload?: Record<string, any>;
  error_log?: string;
  created_at?: string;
}

export interface TaskItem {
  id: string;
  title: string;
  objective: string;
  status: 'pending' | 'planning' | 'running' | 'waiting_approval' | 'paused' | 'completed' | 'failed' | 'cancelled';
  priority: number;
  plan?: { steps?: string[]; total_steps?: number };
  result?: { artifacts?: Array<{ type: string; path: string }>; steps?: any[] };
  error_detail?: any;
  verification_status: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  steps: TaskStep[];
}

export interface ApprovalTicket {
  id: string;
  task_id: string;
  task_step_id?: string;
  description: string;
  action_type: string;
  target_resource: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  approval_token: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  requested_at: string;
}

export interface MemoryItem {
  id: string;
  content: string;
  memory_type: 'preference' | 'semantic' | 'episodic' | 'procedural';
  category: string;
  similarity_score?: number;
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  actor: string;
  action_type: string;
  target_resource?: string;
  payload: Record<string, any>;
  status: string;
  timestamp: string;
}
