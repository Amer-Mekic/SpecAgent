const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

function getToken() {
  return localStorage.getItem('access_token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return null;
  return res.json();
}

// Auth
export const auth = {
  register: (email, password, name) =>
    request('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name }),
    }),
  login: async (email, password) => {
    const data = await request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('access_token', data.access_token);
    return data;
  },
  logout: () => localStorage.removeItem('access_token'),
};

// Upload
export const upload = {
  document: async (file) => {
    const token = getToken();
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE_URL}/api/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },
};

// Requirements
export const requirements = {
  list: (sessionId) => request(`/api/requirements/${sessionId}`),
  create: (sessionId, data) =>
    request(`/api/requirements`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, ...data }),
    }),
  update: (reqId, data) =>
    request(`/api/requirements/${reqId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  approve: (reqId) =>
    request(`/api/requirements/${reqId}`, {
      method: 'PUT',
      body: JSON.stringify({ finalization_status: 'final' }),
    }),
  reject: (reqId) =>
    request(`/api/requirements/${reqId}`, {
      method: 'PUT',
      body: JSON.stringify({ finalization_status: 'rejected' }),
    }),
};

// Chat
export const chat = {
  send: (sessionId, message, requirementId = null) =>
    request(`/api/chat/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({ message, requirement_id: requirementId }),
    }),
  history: (sessionId) => request(`/api/chat/${sessionId}`),
};

// RTM & Export
export const exportApi = {
  rtm: (sessionId) => request(`/api/rtm/${sessionId}`),

  srs: async (sessionId, format = 'pdf') => {
    const token = getToken();
    const res = await fetch(`${BASE_URL}/api/export/${sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ format }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Export failed' }));
      throw new Error(err.detail || 'Export failed');
    }
    return res.blob();
  },

  rtmPdf: async (sessionId) => {
    const token = getToken();
    const res = await fetch(`${BASE_URL}/api/rtm/${sessionId}/export`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'RTM export failed' }));
      throw new Error(err.detail || 'RTM export failed');
    }
    return res.blob();
  },
};