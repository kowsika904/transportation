const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

function getAuthHeaders() {
  const token = sessionStorage.getItem('auth_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginUser(username, password, role = 'logistics_operator') {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password, role }),
  });
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Invalid User ID or Password.' }));
    throw new Error(errorData.detail || 'Invalid User ID or Password.');
  }
  
  const data = await res.json();
  if (data.access_token) {
    sessionStorage.setItem('auth_token', data.access_token);
    sessionStorage.setItem('auth_username', data.username);
    if (data.role) {
      sessionStorage.setItem('auth_role', data.role);
    }
  }
  return data;
}

export function logoutUser() {
  sessionStorage.removeItem('auth_token');
  sessionStorage.removeItem('auth_username');
  sessionStorage.removeItem('auth_role');
}

export function getStoredUser() {
  const token = sessionStorage.getItem('auth_token');
  const username = sessionStorage.getItem('auth_username');
  const role = sessionStorage.getItem('auth_role') || 'logistics_operator';
  if (token && username) {
    return { token, username, role };
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

export async function fetchActiveIncident() {
  const res = await fetch(`${API_BASE_URL}/incidents/active`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Fetch active incident failed');
  }
  return res.json();
}

export async function reportDisruption(disruptionPayload) {
  const res = await fetch(`${API_BASE_URL}/disruption/report`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(disruptionPayload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Reporting disruption failed');
  }
  return res.json();
}

export async function fetchAffectedDeliveries() {
  const res = await fetch(`${API_BASE_URL}/deliveries/affected`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Fetch affected deliveries failed');
  }
  return res.json();
}

export async function acknowledgeDelivery(deliveryId, acknowledgedBy = 'delivery') {
  const res = await fetch(`${API_BASE_URL}/deliveries/acknowledge`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      delivery_id: deliveryId,
      acknowledged_by: acknowledgedBy
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Acknowledging delivery failed');
  }
  return res.json();
}

export async function updateDisruptionStatus(disruptionId, status) {
  const res = await fetch(`${API_BASE_URL}/disruption/${disruptionId}/status`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ status }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || 'Updating status failed');
  }
  return res.json();
}

export async function fetchNotifications(role = null) {
  const url = role ? `${API_BASE_URL}/notifications?role=${encodeURIComponent(role)}` : `${API_BASE_URL}/notifications`;
  const res = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Fetch notifications failed: ${res.statusText}`);
  return res.json();
}

export async function markNotificationRead(notificationId) {
  const res = await fetch(`${API_BASE_URL}/notifications/${notificationId}/read`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Mark notification read failed: ${res.statusText}`);
  return res.json();
}

export async function fetchAuditLogs(limit = 50) {
  const res = await fetch(`${API_BASE_URL}/audit-logs?limit=${limit}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`Fetch audit logs failed: ${res.statusText}`);
  return res.json();
}

export function subscribeNotificationsStream(onNotification, onError) {
  const token = sessionStorage.getItem('auth_token');
  const url = `${API_BASE_URL}/notifications/stream?token=${encodeURIComponent(token || '')}`;
  const eventSource = new EventSource(url);

  eventSource.addEventListener('notification', (event) => {
    try {
      const notifs = JSON.parse(event.data);
      if (onNotification) onNotification(notifs);
    } catch (e) {
      console.error('SSE notification parse error', e);
    }
  });

  eventSource.onerror = (err) => {
    if (onError) onError(err);
  };

  return () => {
    eventSource.close();
  };
}



