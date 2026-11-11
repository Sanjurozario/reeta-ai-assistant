const API_BASE = 'http://127.0.0.1:8765/api/v1';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/system/health`);
  return res.json();
}

export async function postEmergencyStop() {
  const res = await fetch(`${API_BASE}/system/emergency-stop`, { method: 'POST' });
  return res.json();
}

export async function fetchModels() {
  const res = await fetch(`${API_BASE}/system/models`);
  return res.json();
}

export async function createTask(title: string, objective: string, priority = 5) {
  const res = await fetch(`${API_BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, objective, priority }),
  });
  return res.json();
}

export async function fetchTask(taskId: string) {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`);
  return res.json();
}

export async function cancelTask(taskId: string) {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, { method: 'POST' });
  return res.json();
}

export async function fetchTasks(limit = 20) {
  const res = await fetch(`${API_BASE}/tasks?limit=${limit}`);
  return res.json();
}

export async function fetchPendingApprovals() {
  const res = await fetch(`${API_BASE}/permissions/pending`);
  return res.json();
}

export async function respondToApproval(ticketId: string, decision: 'approve' | 'reject') {
  const res = await fetch(`${API_BASE}/permissions/respond`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticket_id: ticketId, decision }),
  });
  return res.json();
}

export async function fetchAuditLogs(limit = 50) {
  const res = await fetch(`${API_BASE}/permissions/audit?limit=${limit}`);
  return res.json();
}
