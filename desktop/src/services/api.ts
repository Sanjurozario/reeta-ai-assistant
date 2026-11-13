import { getApiBase, getAuthHeaders } from './config';

async function request(endpoint: string, options: RequestInit = {}) {
  const base = getApiBase();
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };
  return fetch(`${base}${endpoint}`, {
    ...options,
    headers,
  });
}

export async function fetchHealth() {
  const res = await request('/system/health');
  return res.json();
}

export async function postEmergencyStop() {
  const res = await request('/system/emergency-stop', { method: 'POST' });
  return res.json();
}

export async function fetchModels() {
  const res = await request('/system/models');
  return res.json();
}

export async function createTask(title: string, objective: string, priority = 5) {
  const res = await request('/tasks', {
    method: 'POST',
    body: JSON.stringify({ title, objective, priority }),
  });
  return res.json();
}

export async function fetchTask(taskId: string) {
  const res = await request(`/tasks/${taskId}`);
  return res.json();
}

export async function cancelTask(taskId: string) {
  const res = await request(`/tasks/${taskId}/cancel`, { method: 'POST' });
  return res.json();
}

export async function fetchTasks(limit = 20) {
  const res = await request(`/tasks?limit=${limit}`);
  return res.json();
}

export async function fetchPendingApprovals() {
  const res = await request('/permissions/pending');
  return res.json();
}

export async function respondToApproval(ticketId: string, decision: 'approve' | 'reject') {
  const res = await request('/permissions/respond', {
    method: 'POST',
    body: JSON.stringify({ ticket_id: ticketId, decision }),
  });
  return res.json();
}

export async function fetchAuditLogs(limit = 50) {
  const res = await request(`/permissions/audit?limit=${limit}`);
  return res.json();
}

export async function fetchMemories(limit = 50, memoryType?: string) {
  const url = memoryType ? `/memory?limit=${limit}&memory_type=${memoryType}` : `/memory?limit=${limit}`;
  const res = await request(url);
  return res.json();
}

export async function searchMemories(query: string, limit = 5) {
  const res = await request('/memory/search', {
    method: 'POST',
    body: JSON.stringify({ query, top_k: limit }),
  });
  return res.json();
}

export async function createMemory(content: string, memoryType = 'preference', category = 'general') {
  const res = await request('/memory', {
    method: 'POST',
    body: JSON.stringify({ content, memory_type: memoryType, category }),
  });
  return res.json();
}

export async function deleteMemory(memoryId: string) {
  const res = await request(`/memory/${memoryId}`, { method: 'DELETE' });
  return res.json();
}

export async function forgetMemory(query: string) {
  const res = await request('/memory/forget', {
    method: 'POST',
    body: JSON.stringify({ query }),
  });
  return res.json();
}
