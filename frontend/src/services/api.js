const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

function getAuthHeaders() {
  const token = sessionStorage.getItem('auth_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginUser(username, password) {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Invalid username or password' }));
    throw new Error(errorData.detail || 'Invalid username or password');
  }
  
  const data = await res.json();
  if (data.access_token) {
    sessionStorage.setItem('auth_token', data.access_token);
    sessionStorage.setItem('auth_username', data.username);
  }
  return data;
}

export function logoutUser() {
  sessionStorage.removeItem('auth_token');
  sessionStorage.removeItem('auth_username');
}

export function getStoredUser() {
  const token = sessionStorage.getItem('auth_token');
  const username = sessionStorage.getItem('auth_username');
  if (token && username) {
    return { token, username };
  }
  return null;
}

export async function fetchHealth() {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchDbStatus() {
  const res = await fetch(`${API_BASE_URL}/db/status`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`DB status check failed: ${res.statusText}`);
  return res.json();
}

export async function fetchScenarios() {
  const res = await fetch(`${API_BASE_URL}/scenarios`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Fetch scenarios failed: ${res.statusText}`);
  return res.json();
}

export async function fetchMlMetrics() {
  const res = await fetch(`${API_BASE_URL}/ml/metrics`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Fetch ML metrics failed: ${res.statusText}`);
  return res.json();
}

export async function analyzeDisruption(disruptionPayload) {
  const res = await fetch(`${API_BASE_URL}/disruption/analyze`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(disruptionPayload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Disruption analysis failed');
  }
  return res.json();
}

export async function acceptRecoveryPlan(disruptionId, selectedPlanId, operatorNotes = '', operatorId = 'OPERATOR_01') {
  const res = await fetch(`${API_BASE_URL}/recovery/accept`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      disruption_id: disruptionId,
      selected_plan_id: selectedPlanId,
      operator_id: operatorId,
      operator_notes: operatorNotes,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Accepting plan failed');
  }
  return res.json();
}

export async function modifyRecoveryPlan(disruptionId, selectedPlanId, customOverrides = {}, operatorNotes = '', operatorId = 'OPERATOR_01') {
  const res = await fetch(`${API_BASE_URL}/recovery/modify`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      disruption_id: disruptionId,
      selected_plan_id: selectedPlanId,
      operator_id: operatorId,
      operator_notes: operatorNotes,
      custom_overrides: customOverrides,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Modifying plan failed');
  }
  return res.json();
}
